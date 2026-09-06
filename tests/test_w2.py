"""W2 tests that need no Gemini quota: tools against real Postgres + agent loop with a stubbed LLM.
Run: docker compose run -T --rm app python -m tests.test_w2
"""
import asyncio
import json
import uuid

from app import agent, llm, tools
from sqlalchemy import select

from app.db import Conversation, Invoice, init_db, session


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

    def boom(user, s, **kw):
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
    print("ALL W2 STUB TESTS PASSED")
