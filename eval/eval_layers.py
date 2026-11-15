"""Does each harness layer catch the mistake it exists for? The model is replaced by a script that makes that exact
mistake, then the same turn runs with the layer on and off. Deterministic: no GPU, no real model.
(The real-model ablation is eval_ablation.sh; this one shows what each layer stops when the model does slip.)
Run inside the container:  python -m eval.eval_layers   → eval/logs/LAYERS.md
"""
import asyncio
import json
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from app import agent, llm, tools
from app.db import Conversation, Invoice, User, init_db, session

OUT = Path(__file__).parent / "logs" / "LAYERS.md"
IMG = Path(__file__).parent / "receipts" / "02_coffee.png"
EXTRACT = {"doc_type": "receipt", "vendor": "Bean There Café", "date_raw": "22/08/2026", "subtotal": 280.37, "discount": 0,
           "vat": 19.63, "total": 300.0, "currency": "THB", "category": "อาหาร", "items": []}


def user_with(bills):
    ext = f"evalL:{uuid.uuid4().hex[:8]}"
    uid = agent.get_user(ext)
    ids = []
    with session() as s:
        u = s.get(User, uid)
        pid = tools._active_profile(u, s).id
        for vendor, total, cat, status in bills:
            iv = Invoice(profile_id=pid, status=status, vendor=vendor, invoice_date="2026-08-10", total=total, subtotal=total,
                         vat=0.0, category=cat, currency="THB", total_thb=total)
            s.add(iv)
            s.commit()
            ids.append(iv.id)
    return ext, uid, ids


def script(steps):
    """The model's side of the turn. Extraction calls (image + prompt) get the receipt JSON; agent calls get `steps` in order."""
    n = {"i": 0}

    async def fake(contents, temperature=0.0, model=None):
        if any("inline_data" in p for c in contents for p in c["parts"]) and "สกัดข้อมูล" in json.dumps(contents, ensure_ascii=False):
            return json.dumps(EXTRACT, ensure_ascii=False)
        out = steps[min(n["i"], len(steps) - 1)]
        n["i"] += 1
        return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
    llm.generate = fake


def tool_results(uid):
    with session() as s:
        rows = s.scalars(select(Conversation).where(Conversation.user_id == uid).order_by(Conversation.id)).all()
    return [r.content["text"] for r in rows if (r.content.get("text") or "").startswith("TOOL_RESULT")]


def turn(ext, text=None, image=None):
    return asyncio.run(agent.run_turn(ext, text=text, image_path=image))


# each case: (layer, the mistake we script, run(off: bool) -> observed outcome as a short string)
def gate_case():
    ext, uid, (iv,) = user_with([("ครัวป้าแดง", 120.0, "อาหาร", "confirmed")])
    script([{"tool": "delete_invoice", "args": {"invoice_id": iv}}, {"reply": "ลบแล้วครับ"}])
    turn(ext, text="ลบบิลทิ้งหน่อย")
    with session() as s:
        return "บิลถูกลบ" if s.get(Invoice, iv).deleted_at else "บิลยังอยู่ ได้ preview รอยืนยัน"


def args_case():
    ext, uid, _ = user_with([("Grab", 184.0, "เดินทาง", "confirmed"), ("ร้านกาแฟสามแยก", 145.0, "อาหาร", "confirmed")])
    script([{"tool": "summarize_expenses", "args": {"shop": "Grab"}}, {"reply": "ok"}])
    turn(ext, text="จ่ายค่า Grab ไปเท่าไหร่")
    r = tool_results(uid)[-1]
    if '"error"' in r:
        return "tool ตอบ error พร้อมรายชื่อ argument ที่ใช้ได้"
    return f"tool เงียบ ได้ยอดรวมทุกร้าน {json.loads(r.split(': ', 1)[1])['total']:g} บาท (จริง 184)"


def route_case():
    ext, uid, _ = user_with([])
    dst = Path("/data/uploads") / f"evalL-{uuid.uuid4().hex[:8]}.png"
    shutil.copy(IMG, dst)
    script([{"reply": "ได้รับรูปแล้วครับ"}])  # the model answers without ever calling analyze_receipt
    out = turn(ext, image=str(dst))
    return "อ่านใบเสร็จแล้ว ได้ draft รอยืนยัน" if out["draft"] else "ไม่ได้อ่านใบเสร็จ ไม่มี draft"


def retry_case():
    ext, uid, (iv,) = user_with([("ครัวลุงหนวด", 250.0, "อาหาร", "draft")])
    script(["ผมจะบันทึกให้", {"tool": "save_invoice", "args": {"draft_id": iv}}, {"reply": "บันทึกแล้วครับ"}])
    out = turn(ext, text="ยืนยัน")
    with session() as s:
        saved = s.get(Invoice, iv).status == "confirmed"
    return "ขอ JSON ใหม่ แล้วบันทึกจริง" if saved else f"ตอบว่า \"{out['reply']}\" แต่ไม่ได้บันทึก"


def ontology_case():
    ext, uid, _ = user_with([("ปั๊มบางจาก สาขาร่มเกล้า", 210.0, "เดินทาง", "confirmed")])
    script([{"tool": "summarize_expenses", "args": {"category": "ค่าน้ำมัน"}}, {"reply": "ok"}])
    turn(ext, text="ค่าน้ำมันเท่าไหร่")
    return f"ได้ยอด {json.loads(tool_results(uid)[-1].split(': ', 1)[1])['total']:g} บาท (จริง 210)"


def answer_case():
    ext, uid, _ = user_with([("Grab", 184.0, "เดินทาง", "confirmed"), ("ร้านกาแฟสามแยก", 145.0, "อาหาร", "confirmed")])
    script([{"tool": "summarize_expenses", "args": {}}, {"reply": "เดือนนี้ใช้ไปทั้งหมด 5,400 บาทครับ"},
            {"reply": "ใช้ไปทั้งหมด 329 บาทครับ"}])
    out = turn(ext, text="ใช้ไปทั้งหมดเท่าไหร่")["reply"]
    return f"ขอใหม่ ผู้ใช้ได้ \"{out}\"" if "5,400" not in out else f"ผู้ใช้ได้ \"{out}\""


CASES = [
    ("gate (contract pre-tool-use)", "สั่ง delete_invoice ทันทีโดยผู้ใช้ยังไม่ยืนยัน", "gate", gate_case),
    ("check_args", "ส่ง argument ที่ tool ไม่มี (shop แทน vendor)", "args", args_case),
    ("ROUTE_IMAGE", "ได้รูปแล้วตอบเลย ไม่เรียก analyze_receipt", "route", route_case),
    ("_parse ขอใหม่", "ตอบเป็นข้อความว่าจะบันทึก แต่ไม่เรียก tool", "retry", retry_case),
    ("ontology", "ส่งหมวดเป็นคำที่คนพูด (ค่าน้ำมัน)", "ontology", ontology_case),
    ("ตรวจคำตอบ (contract หลังตอบ)", "แต่งยอดที่ไม่มีในผลจาก tool (5,400 แทน 329)", "answer", answer_case),
]


def main():
    init_db()
    real = llm.generate
    lines = ["# แต่ละชั้นของ harness กันอะไรได้", "",
             "จำลองให้โมเดลทำผิดแบบที่ชั้นนั้นมีไว้กัน (สคริปต์แทนโมเดลจริง) แล้วรันเทิร์นเดียวกันตอนเปิดกับปิดชั้นนั้น", "",
             "| ชั้น | โมเดลทำผิดแบบไหน | เปิดชั้นนี้ | ปิดชั้นนี้ |", "|---|---|---|---|"]
    try:
        for name, mistake, key, fn in CASES:
            res = {}
            for off in (False, True):
                agent.HARNESS_OFF.discard(key); tools._OFF.discard(key)
                if off:
                    agent.HARNESS_OFF.add(key); tools._OFF.add(key)
                res[off] = fn()
            agent.HARNESS_OFF.discard(key); tools._OFF.discard(key)
            lines.append(f"| {name} | {mistake} | {res[False]} | {res[True]} |")
            print(lines[-1], flush=True)
    finally:
        llm.generate = real
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
