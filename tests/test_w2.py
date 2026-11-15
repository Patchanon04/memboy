"""W2 tests that need no LLM: tools against real Postgres + agent loop with a stubbed LLM.
Run: docker compose run -T --rm app python -m tests.test_w2
"""
import asyncio
import json
import uuid
from pathlib import Path

from app import agent, llm, tools
from sqlalchemy import select

from app.db import Conversation, Invoice, User, init_db, session


def fresh_user(tag):
    ext = f"test:{tag}:{uuid.uuid4().hex[:6]}"
    return ext, agent.get_user(ext)


def make_draft(user, s, **kw):
    d = dict(vendor="ร้านทดสอบ", invoice_date="2026-08-20", subtotal=100.0, vat=7.0, total=107.0,
             category="อาหาร", status="draft")
    d.update(kw)
    iv = Invoice(profile_id=tools._active_profile(user, s).id, total_thb=d["total"], **d)
    s.add(iv)
    s.commit()
    return iv


def test_tools():
    from app.db import User
    (_, uid_a), (_, uid_b) = fresh_user("a"), fresh_user("b")
    with session() as s:
        ua, ub = s.get(User, uid_a), s.get(User, uid_b)
        iv = make_draft(ua, s)

        # save: draft -> confirmed; saving twice must fail
        assert tools.save_invoice(ua, s, draft_id=iv.id)["saved"] == iv.id
        try:
            tools.save_invoice(ua, s, draft_id=iv.id)
            raise AssertionError("double-save must raise")
        except tools.ToolError:
            pass

        # user scoping: B must not see/touch A's invoice, same error as nonexistent
        for fn, kw in ((tools.save_invoice, {"draft_id": iv.id}), (tools.update_invoice, {"invoice_id": iv.id, "fields": {"total": 1}}),
                       (tools.delete_invoice, {"invoice_id": iv.id})):
            try:
                fn(ub, s, **kw)
                raise AssertionError("cross-user access must raise")
            except tools.ToolError as e:
                assert "ไม่พบบิล" in str(e)

        # update: valid, invalid field, negative amount
        assert tools.update_invoice(ua, s, invoice_id=iv.id, fields={"total": 450, "date": "2026-08-21"})["total"] == 450
        for bad in ({"status": "confirmed"}, {"total": -5}, {"total": "abc"}):
            try:
                tools.update_invoice(ua, s, invoice_id=iv.id, fields=bad)
                raise AssertionError(f"must reject {bad}")
            except tools.ToolError:
                pass

        # duplicate: same date+total hits, then soft-deleted invoices don't count
        assert tools.check_duplicate(ua, s, vendor="x", date="2026-08-21", total=450)["duplicate"] is True
        assert tools.delete_invoice(ua, s, invoice_id=iv.id)["deleted"] == iv.id
        assert tools.check_duplicate(ua, s, vendor="x", date="2026-08-21", total=450)["duplicate"] is False
        try:
            tools.update_invoice(ua, s, invoice_id=iv.id, fields={"total": 1})
            raise AssertionError("deleted invoice must be gone")
        except tools.ToolError:
            pass
    print("test_tools OK")


def stub_llm(responses):
    """Replace llm.generate with a canned sequence; records what the agent sent."""
    calls = []

    async def fake(contents, temperature=0.0, model=None):
        calls.append(contents)
        return responses[min(len(calls) - 1, len(responses) - 1)]
    llm.generate = fake
    return calls


def test_loop_happy_and_parse_retry():
    ext, uid = fresh_user("loop")
    from app.db import User
    with session() as s:
        u = s.get(User, uid)
        iv_id = make_draft(u, s, vendor="ครัวลุงหนวด", total=250.0, subtotal=250.0, vat=0.0).id
    stub_llm([
        "เอ่อ ขอโทษครับ ผมจะบันทึกให้",                                # not JSON -> parse retry
        json.dumps({"tool": "save_invoice", "args": {"draft_id": iv_id}}),
        json.dumps({"reply": "บันทึกบิลครัวลุงหนวด 250 บาทแล้วครับ"}),
    ])
    out = asyncio.run(agent.run_turn(ext, text="บันทึกเลย"))["reply"]
    assert "ครัวลุงหนวด" in out, out
    with session() as s:
        assert s.get(Invoice, iv_id).status == "confirmed"
    print("test_loop_happy_and_parse_retry OK")


def test_loop_tool_error_feedback():
    ext, uid = fresh_user("err")
    stub_llm([
        json.dumps({"tool": "save_invoice", "args": {"draft_id": 999999}}),   # bad id -> ToolError fed back
        json.dumps({"reply": "ไม่พบบิลที่ว่าครับ"}),
    ])
    out = asyncio.run(agent.run_turn(ext, text="เซฟ 999999"))["reply"]
    assert "ไม่พบ" in out
    print("test_loop_tool_error_feedback OK")


def test_loop_cap():
    ext, uid = fresh_user("cap")
    stub_llm([json.dumps({"tool": "check_duplicate", "args": {"vendor": "x", "date": "2026-01-01", "total": 1}})])
    out = asyncio.run(agent.run_turn(ext, text="วนไปเรื่อยๆ"))["reply"]
    assert "ขั้นตอนเยอะเกินไป" in out, out
    print("test_loop_cap OK")


def test_unknown_tool_then_recover():
    ext, uid = fresh_user("unk")
    stub_llm([
        json.dumps({"tool": "transfer_money", "args": {}}),   # not a real tool -> parse error path
        json.dumps({"reply": "ผมโอนเงินไม่ได้ครับ ทำได้แค่จัดการบิล"}),
    ])
    out = asyncio.run(agent.run_turn(ext, text="โอนเงินให้แม่ค้าหน่อย"))["reply"]
    assert "โอนเงินไม่ได้" in out
    print("test_unknown_tool_then_recover OK")


def test_llm_down_and_turn_budget():
    ext, uid = fresh_user("down")

    async def boom(contents, temperature=0.0, model=None):
        raise llm.LLMError("LLM http 503")
    llm.generate = boom
    out = asyncio.run(agent.run_turn(ext, text="สวัสดี"))["reply"]
    assert "ขัดข้อง" in out, out

    async def slow(contents, temperature=0.0, model=None):
        await asyncio.sleep(0.3)
        return json.dumps({"tool": "check_duplicate", "args": {"vendor": "x", "date": "2026-01-01", "total": 1}})
    llm.generate = slow
    agent.TURN_BUDGET_S = 0.2
    out = asyncio.run(agent.run_turn(ext, text="วนไป"))["reply"]
    agent.TURN_BUDGET_S = 90
    assert "ตอบช้าผิดปกติ" in out, out
    print("test_llm_down_and_turn_budget OK")


SECRET = "SELECT password FROM users WHERE id=42 -- internal-detail"


def test_tool_crash_does_not_leak():
    """guardrail #6: a tool blowing up must reach the user as a polite line, and the crash text
    must not even reach the model (it lands in the log only)."""
    ext, uid = fresh_user("leak")

    def boom(user, s, vendor=None, date=None, total=None, **kw):  # named params: check_args must let the call through
        raise RuntimeError(f"psycopg.errors.UndefinedColumn: {SECRET}")
    orig = agent.TOOLS["check_duplicate"]
    agent.TOOLS["check_duplicate"] = (boom, orig[1], orig[2])
    try:
        stub_llm([
            json.dumps({"tool": "check_duplicate", "args": {"vendor": "x", "date": "2026-01-01", "total": 1}}),
            json.dumps({"reply": "ขออภัยครับ ระบบมีปัญหาชั่วคราว"}),
        ])
        out = asyncio.run(agent.run_turn(ext, text="เช็คบิลซ้ำให้หน่อย"))["reply"]
    finally:
        agent.TOOLS["check_duplicate"] = orig
    assert SECRET not in out and "Traceback" not in out and "psycopg" not in out, out
    assert out.strip(), "user must still get a reply"
    # what was fed back to the model must be the generic message, not the exception text
    with session() as s:
        fed = " ".join(c.content.get("text", "") for c in
                       s.scalars(select(Conversation).where(Conversation.user_id == uid)))
    assert SECRET not in fed and "psycopg" not in fed, fed[-300:]
    assert "เครื่องมือขัดข้องภายใน" in fed
    print("test_tool_crash_does_not_leak OK")

def test_image_routed_then_prose_reply():
    """speed path: a photo goes straight to analyze_receipt (no LLM 'decide' call), and a plain-text reply
    after a tool result is accepted instead of burning a retry. Expect exactly 2 LLM calls."""
    from PIL import Image
    ext, uid = fresh_user("route")
    png_path = f"/data/uploads/route{uuid.uuid4().hex[:8]}.png"
    Image.new("RGB", (8, 8), "white").save(png_path)
    calls = stub_llm([
        json.dumps({"vendor": "ร้านเส้นทาง", "date": "2026-08-25", "total": 90, "vat": 0, "subtotal": 120, "discount": 30, "category": "อาหาร", "items": []}),  # analyze_receipt's own call
        "สรุปใบเสร็จร้านเส้นทาง 90 บาท ถูกต้องไหมครับ",                                                                    # agent answers in prose
    ])
    out = asyncio.run(agent.run_turn(ext, image_path=png_path))
    assert len(calls) == 2, len(calls)
    assert out["reply"].startswith("สรุปใบเสร็จร้านเส้นทาง"), out["reply"]
    assert out["draft"] is True
    steps = [json.loads(l) for l in open("/data/logs/turns.jsonl", encoding="utf-8")][-1]["steps"]
    assert steps[0].get("tool") == "analyze_receipt" and steps[0].get("routed") is True, steps[0]
    assert steps[-1].get("prose") is True, steps[-1]
    assert not any("เลขไม่ลงตัว" in w for w in steps[0]["result"]["warnings"]), steps[0]["result"]["warnings"]  # 120 - 30 + 0 == 90
    with session() as s:
        assert s.get(Invoice, steps[0]["result"]["draft_id"]).discount == 30
    print("test_image_routed_then_prose_reply OK")

def test_confirmation_gate():
    """guardrail #9 (program-enforced, professor's requirement): save/edit-confirmed/delete never run on the turn the
    model asks for them; they run only after the user's own 'ยืนยัน', and 'ยกเลิก' drops them."""
    from app import gate
    ext, uid = fresh_user("gate")
    with session() as s:
        u = s.get(User, uid)
        iv = make_draft(u, s, vendor="ร้านเกต", total=77.0, subtotal=77.0, vat=0.0, status="confirmed"); iv_id = iv.id
        draft_id = make_draft(u, s, vendor="ร้านดราฟต์", total=10.0, subtotal=10.0, vat=0.0).id

    # (a) model tries to delete a confirmed invoice without the user confirming -> parked, previewed, NOT deleted
    stub_llm([json.dumps({"tool": "delete_invoice", "args": {"invoice_id": iv_id}}),
              json.dumps({"reply": "จะลบบิลร้านเกต 77 บาท พิมพ์ ยืนยัน"})])
    out = asyncio.run(agent.run_turn(ext, text="ลบบิลร้านเกตทิ้ง"))
    assert out["draft"] is True and "ยืนยัน" in out["reply"], out
    with session() as s:
        assert s.get(Invoice, iv_id).deleted_at is None, "must not delete before confirmation"
        assert s.get(User, uid).pending_action["tool"] == "delete_invoice"
    steps = [json.loads(l) for l in open("/data/logs/turns.jsonl", encoding="utf-8")][-1]["steps"]
    assert steps[0].get("gated") is True, steps[0]

    # (b) an unrelated question keeps the pending action; (c) 'ยืนยัน' executes it with no model decision
    stub_llm([json.dumps({"reply": "ยอด 77 บาทครับ"})])
    asyncio.run(agent.run_turn(ext, text="ยอดเท่าไหร่นะ"))
    with session() as s:
        assert s.get(User, uid).pending_action["tool"] == "delete_invoice"
    calls = stub_llm([json.dumps({"reply": "ลบแล้วครับ"})])
    out = asyncio.run(agent.run_turn(ext, text="ยืนยัน"))
    with session() as s:
        assert s.get(Invoice, iv_id).deleted_at is not None, "confirmed action must run"
        assert s.get(User, uid).pending_action is None
    steps = [json.loads(l) for l in open("/data/logs/turns.jsonl", encoding="utf-8")][-1]["steps"]
    assert steps[0].get("tool") == "delete_invoice" and steps[0].get("confirmed") is True, steps[0]
    assert len(calls) == 1, "the deletion itself must not need an LLM call"

    # (d) 'ยกเลิก' drops a pending save; the draft stays a draft
    stub_llm([json.dumps({"tool": "save_invoice", "args": {"draft_id": draft_id}}), json.dumps({"reply": "รอยืนยัน"})])
    asyncio.run(agent.run_turn(ext, text="บันทึกบิลดราฟต์"))
    stub_llm([json.dumps({"reply": "ยกเลิกแล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยกเลิก"))
    with session() as s:
        assert s.get(Invoice, draft_id).status == "draft" and s.get(User, uid).pending_action is None

    # (e) the normal flow stays one round trip: user says 'ยืนยัน' after a preview, model calls save -> allowed
    stub_llm([json.dumps({"tool": "save_invoice", "args": {"draft_id": draft_id}}), json.dumps({"reply": "บันทึกแล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยืนยัน บันทึกเลย"))
    with session() as s:
        assert s.get(Invoice, draft_id).status == "confirmed"

    # (f) editing a draft is not gated (preview loop), editing a confirmed invoice is
    d2 = None
    with session() as s:
        d2 = make_draft(s.get(User, uid), s, vendor="ร้านแก้", total=5.0, subtotal=5.0, vat=0.0).id
    stub_llm([json.dumps({"tool": "update_invoice", "args": {"invoice_id": d2, "fields": {"total": 6}}}), json.dumps({"reply": "แก้แล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยอดจริง 6"))
    with session() as s:
        assert s.get(Invoice, d2).total == 6
    stub_llm([json.dumps({"tool": "update_invoice", "args": {"invoice_id": draft_id, "fields": {"total": 11}}}), json.dumps({"reply": "รอยืนยัน"})])
    asyncio.run(agent.run_turn(ext, text="บิลดราฟต์ยอดจริง 11"))
    with session() as s:
        assert s.get(Invoice, draft_id).total == 10, "confirmed invoice must not change before ยืนยัน"
    stub_llm([json.dumps({"reply": "ยกเลิกแล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยกเลิก"))

    # (g) mark_reimbursed waits for ยืนยัน, then runs
    stub_llm([json.dumps({"tool": "mark_reimbursed", "args": {"invoice_ids": [draft_id]}}), json.dumps({"reply": "รอยืนยัน"})])
    asyncio.run(agent.run_turn(ext, text="ติ๊กว่าเบิกบิลดราฟต์แล้ว"))
    with session() as s:
        assert s.get(Invoice, draft_id).reimbursed_at is None, "must not mark before ยืนยัน"
    stub_llm([json.dumps({"reply": "ติ๊กแล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยืนยัน"))
    with session() as s:
        assert s.get(Invoice, draft_id).reimbursed_at is not None

    # (h) manage_category: list runs at once, add/remove/rename wait
    with session() as s:
        u = s.get(User, uid)
        assert not gate.needs_gate(u, s, "manage_category", {"action": "list"})
        assert gate.needs_gate(u, s, "manage_category", {"action": "rename", "name": "a", "new_name": "b"})
    stub_llm([json.dumps({"tool": "manage_category", "args": {"action": "add", "name": "ค่าเกต"}}), json.dumps({"reply": "รอยืนยัน"})])
    asyncio.run(agent.run_turn(ext, text="เพิ่มหมวดค่าเกต"))
    with session() as s:
        assert "ค่าเกต" not in tools.user_categories(s.get(User, uid), s), "must not add before ยืนยัน"
    stub_llm([json.dumps({"reply": "เพิ่มแล้ว"})])
    asyncio.run(agent.run_turn(ext, text="ยืนยัน"))
    with session() as s:
        assert "ค่าเกต" in tools.user_categories(s.get(User, uid), s)
    print("test_confirmation_gate OK")

def test_long_prose_is_a_reply():
    """'วิธีใช้'-style answers came back as prose, got a format nag, and the user saw "ผมจะตอบเป็น JSON..." —
    a long prose answer with no tool call is accepted as the reply in one call; a short intent still retries."""
    ext, uid = fresh_user("prose")
    howto = "ใช้งานได้ดังนี้ครับ: 1) ส่งรูปใบเสร็จมา 2) ตรวจข้อมูลแล้วพิมพ์ยืนยัน 3) ถามยอดได้ เช่น เดือนนี้ใช้ไปเท่าไหร่ 4) ขอรายงาน PDF ได้ทุกเมื่อ 5) สร้างโปรไฟล์แยกทริปได้"
    calls = stub_llm([howto, json.dumps({"reply": "ไม่ควรถูกเรียก"})])
    out = asyncio.run(agent.run_turn(ext, text="ใช้ยังไง"))["reply"]
    assert out == howto and len(calls) == 1, (out, len(calls))
    calls = stub_llm(["เอ่อ ผมจะบันทึกให้", json.dumps({"reply": "ไม่มีบิลให้บันทึกครับ"})])
    out = asyncio.run(agent.run_turn(ext, text="บันทึก"))["reply"]
    assert out == "ไม่มีบิลให้บันทึกครับ" and len(calls) == 2
    print("test_long_prose_is_a_reply OK")

def test_typing_indicator_and_slow_ack():
    """LINE 'typing…' animation starts immediately and is renewed while the turn runs; the text ack only after ACK_AFTER_S;
    the real answer goes out by push once the reply token was spent on the ack."""
    from app import events, line_io
    sent = []

    async def fake_post(path, body):
        sent.append((path, (body.get("messages") or [{}])[0].get("text", "")[:12] or body.get("loadingSeconds")))
        return {}
    line_io._post = fake_post
    events.ACK_AFTER_S = 0.3
    stub_llm([json.dumps({"reply": "คำตอบจริง"})])

    async def slow(contents, temperature=0.0, model=None):
        await asyncio.sleep(0.8)
        return json.dumps({"reply": "คำตอบจริง"})
    llm.generate = slow
    ev = {"type": "message", "replyToken": "tok", "source": {"userId": f"test:typing:{uuid.uuid4().hex[:6]}"},
          "message": {"type": "text", "id": uuid.uuid4().hex, "text": "ช้าหน่อยนะ"}}
    asyncio.run(events.handle_event(ev))
    paths = [p for p, _ in sent]
    assert paths[0] == "chat/loading/start", sent
    assert any(p_ == "message/reply" and str(m).startswith("กำลังอ่าน") for p_, m in sent), sent
    assert paths.count("chat/loading/start") >= 2, sent          # renewed after the ack cleared it
    assert sent[-1] == ("message/push", "คำตอบจริง"), sent
    print("test_typing_indicator_and_slow_ack OK")

def test_report_spec():
    """Reports are built to order: the agent passes a spec, report.py validates it against whitelists and does the
    arithmetic; unknown values come back as a ToolError listing the valid ones so the model can correct itself."""
    from app import report
    ext, uid = fresh_user("report")
    with session() as s:
        u = s.get(User, uid)
        for v, cat, tot in (("ร้าน ก", "อาหาร", 100.0), ("ร้าน ข", "เดินทาง", 250.0), ("ร้าน ก", "อาหาร", 50.0)):
            make_draft(u, s, vendor=v, category=cat, total=tot, subtotal=tot, vat=0.0, status="confirmed", invoice_date="2026-08-10")
        out = tools.generate_report(u, s, date_from="2026-08-01", date_to="2026-08-31", title="รายงานทดสอบ",
                                    sections=["summary", "by_vendor", "table"], columns="date,vendor,total",
                                    group_by="category", sort="total", desc=True, note="หมายเหตุ")
    assert out["count"] == 3 and out["total"] == 400.0, out
    assert out["sections"] == ["summary", "by_vendor", "table", "note"], out["sections"]   # note appended, signature not forced
    assert Path(out["_file"]).stat().st_size > 1000

    rows = [{"date": "2026-08-10", "vendor": "ร้าน ก", "category": "อาหาร", "total": 100.0, "vat": 7.0, "reimbursed": False},
            {"date": "2026-08-11", "vendor": "ร้าน ข", "category": "เดินทาง", "total": 250.0, "vat": 0.0, "reimbursed": True}]
    ctx = report.build_context(rows, {"group_by": "category", "columns": "date,total"}, profile="ส่วนตัว", period="ส.ค.")
    assert ctx["sum_total"] == 350.0 and ctx["sum_vat"] == 7.0
    assert [g["key"] for g in ctx["groups"]] == ["อาหาร", "เดินทาง"], ctx["groups"]
    assert [g["subtotal"] for g in ctx["groups"]] == [100.0, 250.0]
    assert ctx["summary"]["pending"] == 100.0 and ctx["summary"]["reimbursed"] == 250.0
    assert ctx["sections"] == ["chart", "by_category", "table", "signature"]   # defaults when not asked

    with session() as s:
        u = s.get(User, uid)
        for bad in ({"sections": "pie3d"}, {"columns": "password"}, {"group_by": "weekday"}, {"sort": "random"}):
            try:
                tools.generate_report(u, s, date_from="2026-08-01", date_to="2026-08-31", **bad)
                raise AssertionError(f"must reject {bad}")
            except tools.ToolError as e:
                assert "ใช้ได้" in str(e), e
    print("test_report_spec OK")







def test_escaped_newlines():
    r"""A model that writes a literal \n inside the JSON reply string must not send that to LINE verbatim."""
    ext, uid = fresh_user("esc")
    stub_llm([json.dumps({"reply": "บรรทัดหนึ่ง" + "\\n" + "บรรทัดสอง"})])
    out = asyncio.run(agent.run_turn(ext, text="ทดสอบ"))["reply"]
    assert out == "บรรทัดหนึ่ง\nบรรทัดสอง", repr(out)
    stub_llm([json.dumps({"reply": "ปกติ\nอยู่แล้ว"})])
    assert asyncio.run(agent.run_turn(ext, text="ทดสอบ2"))["reply"] == "ปกติ\nอยู่แล้ว"
    print("test_escaped_newlines OK")


if __name__ == "__main__":
    init_db()
    test_tools()
    test_loop_happy_and_parse_retry()
    test_loop_tool_error_feedback()
    test_loop_cap()
    test_unknown_tool_then_recover()
    test_llm_down_and_turn_budget()
    test_tool_crash_does_not_leak()
    test_image_routed_then_prose_reply()
    test_confirmation_gate()
    test_long_prose_is_a_reply()
    test_typing_indicator_and_slow_ack()
    test_report_spec()
    test_escaped_newlines()
    print("ALL W2 STUB TESTS PASSED")
