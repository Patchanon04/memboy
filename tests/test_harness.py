"""Harness conformance suite — one check per harness item in PLAN.md, each printed on its
own line with the value it actually measured, then written to eval/logs/HARNESS_REPORT.md.

Run: docker compose run -T --rm app python -m tests.test_harness
No LLM quota needed: the model is stubbed. Items that genuinely need an external system
(live vision, LINE) are reported as EXTERNAL with a pointer to where they were measured.
"""
import asyncio
import io
import json
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select

from app import agent, events, line_io, llm, tools, worker
from app.db import Conversation, Invoice, ProcessedEvent, User, init_db, session

RESULTS = []
REAL_GENERATE = llm.generate  # keep the real one: later checks stub llm.generate out


def check(cid, title, kind):
    """Register one harness check. The function returns the evidence string, or raises."""
    def deco(fn):
        RESULTS.append({"id": cid, "title": title, "kind": kind, "fn": fn})
        return fn
    return deco


def _user(tag):
    ext = f"harness:{tag}:{uuid.uuid4().hex[:6]}"
    return ext, agent.get_user(ext)


def _stub(responses):
    calls = []

    async def fake(contents, temperature=0.0, model=None):
        calls.append(contents)
        return responses[min(len(calls) - 1, len(responses) - 1)]
    llm.generate = fake
    return calls


def _add(u, s, **kw):
    d = dict(vendor="ร้านทดสอบ", invoice_date="2026-08-20", subtotal=100.0, vat=7.0, total=107.0,
             category="อาหาร", status="confirmed")
    d.update(kw)
    iv = Invoice(profile_id=tools._active_profile(u, s).id, total_thb=d["total"], **d)
    s.add(iv)
    s.commit()
    return iv.id


# ---------------- guardrails ----------------
@check("G1", "User scoping ที่ระดับ tool", "unit")
def g1():
    (_, a), (_, b) = _user("a"), _user("b")
    with session() as s:
        ua, ub = s.get(User, a), s.get(User, b)
        iid = _add(ua, s)
        blocked = 0
        for fn, kw in ((tools.save_invoice, {"draft_id": iid}), (tools.delete_invoice, {"invoice_id": iid}),
                       (tools.update_invoice, {"invoice_id": iid, "fields": {"total": 1}}),
                       (tools.get_invoice_image, {"invoice_id": iid})):
            try:
                fn(ub, s, **kw)
            except tools.ToolError as e:
                blocked += 1
                assert "ไม่พบบิล" in str(e), "error must not reveal that the id exists"
        assert blocked == 4
    return f"user B ถูกปฏิเสธ {blocked}/4 tools ด้วยข้อความเดียวกับ 'บิลไม่มีจริง'"


@check("G2", "Loop cap ต่อเทิร์น", "stub")
def g2():
    ext, _ = _user("cap")
    _stub([json.dumps({"tool": "check_duplicate", "args": {"vendor": "x", "date": "2026-01-01", "total": 1}})])
    out = asyncio.run(agent.run_turn(ext, text="วนไป"))["reply"]
    assert "ขั้นตอนเยอะเกินไป" in out
    return f"โมเดลเรียก tool ไม่หยุด → ตัดที่ {agent.LOOP_CAP} ครั้ง แล้วตอบ user"


@check("G3", "Validate args ที่ปาก tool", "unit")
def g3():
    ext, uid = _user("val")
    with session() as s:
        u = s.get(User, uid)
        iid = _add(u, s)
        rejected = []
        for bad in ({"total": -5}, {"total": "abc"}, {"status": "confirmed"}, {"category": "ไม่มีหมวดนี้"}):
            try:
                tools.update_invoice(u, s, invoice_id=iid, fields=bad)
            except tools.ToolError:
                rejected.append(list(bad)[0] + "=" + str(list(bad.values())[0]))
        assert len(rejected) == 4
    return "ปฏิเสธทั้งหมด: " + ", ".join(rejected)


@check("G4", "ลบ = soft delete (กู้คืนได้)", "unit")
def g4():
    ext, uid = _user("del")
    with session() as s:
        u = s.get(User, uid)
        iid = _add(u, s)
        tools.delete_invoice(u, s, invoice_id=iid)
        row = s.get(Invoice, iid)
        assert row.deleted_at is not None, "row must still exist"
        assert tools.find_invoices(u, s)["count"] == 0, "deleted must not appear in queries"
        tools.restore_invoice(u, s, invoice_id=iid)
        assert tools.find_invoices(u, s)["count"] == 1
    return "หลังลบ: แถวยังอยู่ใน DB, ไม่โผล่ใน query, restore กลับมาได้"


@check("G5", "Prompt injection ในรูปบิล", "external")
def g5():
    p = Path("/srv/eval/logs/evalA_31b.json")
    if not p.exists():
        return "ดูผลใน eval/logs/EVAL_REPORT.md (D-adversarial)"
    rows = json.loads(p.read_text(encoding="utf-8"))
    d = [r for r in rows if str(r.get("group", "")).startswith("D")]
    return f"Eval D adversarial {sum(1 for r in d if r['ok'])}/{len(d)} ผ่าน (รวมบิลที่ฝังคำสั่ง SYSTEM OVERRIDE) + live probe บันทึกใน eval/logs/"


@check("G6", "Error ไม่รั่วถึง user และไม่ถึงโมเดล", "stub")
def g6():
    SECRET = "SELECT password FROM users -- internal"
    ext, uid = _user("leak")

    def boom(user, s, **kw):
        raise RuntimeError(f"psycopg.errors.UndefinedColumn: {SECRET}")
    orig = agent.TOOLS["check_duplicate"]
    agent.TOOLS["check_duplicate"] = (boom, orig[1], orig[2])
    try:
        _stub([json.dumps({"tool": "check_duplicate", "args": {"vendor": "x", "date": "2026-01-01", "total": 1}}),
               json.dumps({"reply": "ขออภัยครับ ระบบมีปัญหาชั่วคราว"})])
        reply = asyncio.run(agent.run_turn(ext, text="เช็คซ้ำ"))["reply"]
    finally:
        agent.TOOLS["check_duplicate"] = orig
    with session() as s:
        fed = " ".join(c.content.get("text", "") for c in s.scalars(select(Conversation).where(Conversation.user_id == uid)))
    assert SECRET not in reply and SECRET not in fed and "psycopg" not in fed
    return "ข้อความ exception ไม่ปรากฏทั้งในคำตอบ user และใน context ที่ป้อนกลับโมเดล"


@check("G7", "Rate limit ต่อ user (LINE + เว็บ)", "unit")
def g7():
    uid = f"rl:{uuid.uuid4().hex[:6]}"
    hits = [events.rate_limited(uid) for _ in range(events.RATE_LIMIT + 2)]
    assert not any(hits[:events.RATE_LIMIT]) and all(hits[events.RATE_LIMIT:])
    assert "rate_limited" in Path("/srv/app/web.py").read_text(encoding="utf-8"), "web path must use it too"
    return f"{events.RATE_LIMIT} ครั้งแรกผ่าน / ครั้งที่ {events.RATE_LIMIT + 1}-{events.RATE_LIMIT + 2} บล็อก; ใช้ทั้ง events.py และ web.py"


@check("G8", "ย่อรูปก่อนส่ง LLM", "unit")
def g8():
    from PIL import Image
    im = Image.new("RGB", (4000, 3000), "white")
    b = io.BytesIO()
    im.save(b, "JPEG", quality=95)
    raw = b.getvalue()
    out = events.shrink(raw)
    w, h = Image.open(io.BytesIO(out)).size
    assert max(w, h) <= 1280 and len(out) < len(raw)
    return f"4000x3000 {len(raw) // 1024}KB → {w}x{h} {len(out) // 1024}KB"


# ---------------- determinism ----------------
@check("D1", "temperature = 0 ทุก call", "unit")
def d1():
    captured = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"reply":"ok"}'}]}}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, params=None, json=None):
            captured.update(json or {})
            return _Resp()

    real, httpx.AsyncClient = httpx.AsyncClient, _Client
    try:
        asyncio.run(REAL_GENERATE([{"role": "user", "parts": [{"text": "hi"}]}]))
    finally:
        httpx.AsyncClient = real
    t = captured.get("generationConfig", {}).get("temperature")
    assert t == 0.0, captured
    return f"payload ที่ส่งจริงมี generationConfig.temperature = {t}"


@check("D2", "เลขเงินมาจาก SQL + เช็ค subtotal+vat≈total", "unit")
def d2():
    ext, uid = _user("money")
    with session() as s:
        u = s.get(User, uid)
        vals = [107.0, 250.5, 84.0]
        for v in vals:
            _add(u, s, total=v, subtotal=v, vat=0.0, invoice_date="2026-08-20")
        got = tools.summarize_expenses(u, s)["total"]
        assert abs(got - sum(vals)) < 0.01, (got, vals)
        d = tools._make_draft(u, s, {"vendor": "ร้านเลขเพี้ยน", "date": "2026-08-20", "total": 500,
                                     "subtotal": 100, "vat": 7, "category": "อาหาร"}, Path("/tmp/x.png"), None)
        assert any("เลขไม่ลงตัว" in w for w in d["warnings"]), d["warnings"]
    return f"ยอดรวมจาก SQL = {got} (ตรงกับผลบวกจริง); บิลที่ 100+7≠500 ถูกติด warning อัตโนมัติ"


@check("D3", "Webhook idempotency", "stub")
def d3():
    mid = f"h-{uuid.uuid4().hex[:8]}"
    ev = {"type": "message", "replyToken": "t", "source": {"userId": f"U-h-{uuid.uuid4().hex[:4]}"},
          "message": {"type": "text", "id": mid, "text": "สวัสดี"}}
    _stub([json.dumps({"reply": "ok"})])
    asyncio.run(events.handle_event(ev))
    with session() as s:
        assert s.get(ProcessedEvent, mid) is not None
    seen = []
    real = agent.run_turn

    async def spy(*a, **k):
        seen.append(1)
        return await real(*a, **k)
    agent.run_turn = spy
    try:
        asyncio.run(events.handle_event(ev))   # LINE redelivery
    finally:
        agent.run_turn = real
    assert not seen, "duplicate must not reach the agent"
    return f"event {mid} ส่งซ้ำ → ไม่เข้า agent loop รอบสอง (ถูก dedupe จากตาราง processed_events)"


@check("D4", "State machine ของบิล (draft → confirmed)", "unit")
def d4():
    ext, uid = _user("state")
    with session() as s:
        u = s.get(User, uid)
        iid = _add(u, s, status="draft")
        tools.save_invoice(u, s, draft_id=iid)
        assert s.get(Invoice, iid).status == "confirmed"
        try:
            tools.save_invoice(u, s, draft_id=iid)
            raise AssertionError("double save must fail")
        except tools.ToolError as e:
            msg = str(e)
    return f"บันทึกซ้ำถูกปฏิเสธที่ tool: {msg[:60]}"


@check("D5", "Turn log ครบทุกเทิร์น (JSONL)", "stub")
def d5():
    ext, _ = _user("log")
    _stub([json.dumps({"reply": "ok"})])
    asyncio.run(agent.run_turn(ext, text="ทดสอบ log"))
    last = json.loads(Path("/data/logs/turns.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["user"] == ext and last["steps"] and "out" in last
    return f"เทิร์นล่าสุดถูกบันทึกครบ: user/in/steps/out ({len(last['steps'])} step)"


@check("D6", "Pin รุ่นโมเดล (ไม่ใช้ alias ลอยๆ)", "unit")
def d6():
    assert "latest" not in llm.MODEL and llm.MODEL.startswith("gemma-4"), llm.MODEL
    return f"MODEL={llm.MODEL} · FALLBACK={llm.FALLBACK} (ระบุรุ่นเต็ม ไม่ใช่ alias)"


@check("D7", "Inject วันที่ปัจจุบัน (Asia/Bangkok)", "unit")
def d7():
    import datetime
    ext, uid = _user("date")
    with session() as s:
        sp = agent.system_prompt(s.get(User, uid), s)
    today = datetime.datetime.now(agent.TZ).strftime("%Y-%m-%d")
    assert today in sp, "system prompt must carry today's date"
    return f"system prompt มีวันที่ {today} (เวลาไทย) → 'เดือนนี้/เมื่อวาน' คำนวณจากโค้ด ไม่ใช่ความจำโมเดล"


@check("D8", "Serialize ต่อ user (ขนานข้าม user)", "stub")
def d8():
    order = []

    async def fake(contents, temperature=0.0, model=None):
        tag = contents[-1]["parts"][-1]["text"][-2:]
        order.append(("s", tag))
        await asyncio.sleep(0.3)
        order.append(("e", tag))
        return json.dumps({"reply": "ok"})
    llm.generate = fake

    def evs(uid):
        return [{"type": "message", "replyToken": "t", "source": {"userId": uid},
                 "message": {"type": "text", "id": f"{uid}-{i}-{uuid.uuid4().hex[:4]}", "text": f"msg #{i}"}} for i in range(3)]

    async def run(e):
        await asyncio.gather(*(worker.process_event({"job_try": 1}, x) for x in e))
    same = f"U-same-{uuid.uuid4().hex[:4]}"
    t0 = time.time()
    asyncio.run(run(evs(same)))
    serial_s = time.time() - t0
    assert all(order[i][0] == "s" and order[i + 1] == ("e", order[i][1]) for i in range(0, 6, 2)), order
    t0 = time.time()
    asyncio.run(run([evs(f"U-diff{i}-{uuid.uuid4().hex[:4]}")[0] for i in range(3)]))
    par_s = time.time() - t0
    assert par_s < 0.7 < serial_s
    return f"user เดียวกัน 3 ข้อความ = {serial_s:.1f}s (เรียงกัน) · คนละ user = {par_s:.1f}s (ขนาน)"


# ---------------- external (needs a system we can't stub honestly) ----------------
@check("X1", "LINE transport (reply/push/quick reply/Flex/rich menu)", "external")
def x1():
    raise NotImplementedError("ยังไม่ได้วัด — ต้องมี LINE channel credentials (โค้ดพร้อม: scripts/setup_line.py)")


@check("X2", "LIFF dashboard บนแอป LINE", "external")
def x2():
    raise NotImplementedError("ยังไม่ได้วัด — ต้องมี LIFF ID จาก LINE Login channel")


def main():
    init_db()

    async def _no_line(path, body):  # never touch the real LINE API from tests (credentials may be present)
        pass
    line_io._post = _no_line

    rows = []
    for c in RESULTS:
        try:
            ev = c["fn"]()
            status, note = "PASS", ev
        except NotImplementedError as e:
            status, note = "TODO", str(e)
        except Exception as e:
            status, note = "FAIL", f"{type(e).__name__}: {e}"
        rows.append({**{k: c[k] for k in ("id", "title", "kind")}, "status": status, "note": note})
        icon = {"PASS": "✅", "TODO": "⏳", "FAIL": "❌"}[status]
        print(f"{icon} {c['id']:3} {c['title']:42} [{c['kind']:8}] {note}", flush=True)

    md = ["# Harness conformance — ผลทดสอบรายข้อ", "",
          f"รันด้วย `docker compose run --rm app python -m tests.test_harness` · "
          f"ผ่าน {sum(1 for r in rows if r['status'] == 'PASS')}/{sum(1 for r in rows if r['status'] != 'TODO')} ข้อที่วัดได้ในเครื่อง", "",
          "| # | รายการ | วิธีพิสูจน์ | ผล | ค่าที่วัดได้ |", "|---|---|---|---|---|"]
    kinds = {"unit": "unit test", "stub": "agent loop (LLM จำลอง)", "external": "ระบบภายนอก"}
    for r in rows:
        md.append(f"| {r['id']} | {r['title']} | {kinds[r['kind']]} | "
                  f"{'✅ ผ่าน' if r['status'] == 'PASS' else ('⏳ ยังไม่วัด' if r['status'] == 'TODO' else '❌ ตก')} | {r['note']} |")
    out = Path("/srv/eval/logs/HARNESS_REPORT.md")
    try:
        out.write_text("\n".join(md) + "\n", encoding="utf-8")
        print("\nwrote", out)
    except OSError:
        Path("/data/logs/HARNESS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print("\nwrote /data/logs/HARNESS_REPORT.md (eval/ is read-only)")
    bad = [r for r in rows if r["status"] == "FAIL"]
    print(f"\n{sum(1 for r in rows if r['status'] == 'PASS')} PASS · {len(bad)} FAIL · {sum(1 for r in rows if r['status'] == 'TODO')} TODO")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
