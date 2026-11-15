"""Eval F: correctness + faithfulness of the agent's ANSWERS (not the OCR), scored from the captured context of every turn.

Each question runs on a fresh user seeded with the same synthetic invoices (no real data). After the turn we read back
exactly what the model saw from tools (the TOOL_RESULT rows) and what it replied, and save both to faithfulness.jsonl.
  correctness  = the reply contains the right number (ground truth computed from SEED in code, not by the model)
  faithfulness = numbers in the reply that appear in the context (tool results + the question) / all numbers in the reply
Run inside the container:  python -m eval.eval_faithfulness
"""
import asyncio
import datetime
import json
import re
import uuid
from pathlib import Path

from sqlalchemy import select

from app import agent, tools
from app.db import Conversation, Invoice, User, init_db, session

OUT = Path(__file__).parent / "logs"
# (vendor, date, total, vat, category, reimbursed) — invented shops, dummy amounts
SEED = [
    ("ข้าวมันไก่เจ๊หน่อย", "2026-08-03", 60.0, 0.0, "อาหาร", False),
    ("Grab", "2026-08-05", 184.0, 0.0, "เดินทาง", True),
    ("ร้านกาแฟสามแยก", "2026-08-12", 145.0, 9.49, "อาหาร", False),
    ("ปั๊มน้ำมันศรีนคร", "2026-08-19", 1200.0, 78.5, "เดินทาง", True),
    ("ร้านหนังสือบ้านอ่าน", "2026-08-27", 450.0, 29.44, "ของใช้", False),
    ("ข้าวมันไก่เจ๊หน่อย", "2026-09-02", 65.0, 0.0, "อาหาร", False),
    ("Grab", "2026-09-04", 212.0, 0.0, "เดินทาง", False),
    ("ร้านเครื่องเขียนดีดี", "2026-09-10", 389.0, 25.45, "ของใช้", False),
    ("ร้านกาแฟสามแยก", "2026-09-15", 130.0, 8.5, "อาหาร", False),
    ("ร้านสุกี้ริมคลอง", "2026-09-21", 742.0, 48.54, "อาหาร", False),
]


def total(pred) -> float:
    return round(sum(r[2] for r in SEED if pred(r)), 2)


AUG, SEP = (lambda r: r[1][:7] == "2026-08"), (lambda r: r[1][:7] == "2026-09")
QUESTIONS = [  # (question, ground-truth number)
    ("เดือนสิงหาคม 2026 ใช้ไปทั้งหมดเท่าไหร่", total(AUG)),
    ("เดือนกันยายน 2026 ใช้ไปทั้งหมดเท่าไหร่", total(SEP)),
    ("ค่าอาหารเดือนกันยายน 2026 เท่าไหร่", total(lambda r: SEP(r) and r[4] == "อาหาร")),
    ("ค่าเดินทางเดือนสิงหาคม 2026 รวมเท่าไหร่", total(lambda r: AUG(r) and r[4] == "เดินทาง")),
    ("ค่าของใช้เดือนสิงหาคม 2026 เท่าไหร่", total(lambda r: AUG(r) and r[4] == "ของใช้")),  # was "ช้อปปิ้ง", not a category in the system
    ("เดือนสิงหาคม 2026 มีบิลกี่ใบ", float(sum(map(AUG, SEED)))),
    ("เดือนกันยายน 2026 มีบิลกี่ใบ", float(sum(map(SEP, SEED)))),
    ("จ่ายค่า Grab ไปทั้งหมดกี่บาท", total(lambda r: r[0] == "Grab")),
    ("ร้านกาแฟสามแยกจ่ายไปรวมเท่าไหร่", total(lambda r: r[0] == "ร้านกาแฟสามแยก")),
    ("ข้าวมันไก่เจ๊หน่อยรวมทั้งหมดเท่าไหร่", total(lambda r: r[0] == "ข้าวมันไก่เจ๊หน่อย")),
    ("VAT เดือนสิงหาคม 2026 รวมเท่าไหร่", round(sum(r[3] for r in SEED if AUG(r)), 2)),
    ("VAT เดือนกันยายน 2026 รวมเท่าไหร่", round(sum(r[3] for r in SEED if SEP(r)), 2)),
    ("บิลที่ยังไม่ได้เบิกทั้งหมดรวมเป็นเงินเท่าไหร่", total(lambda r: not r[5])),
    ("เบิกไปแล้วรวมเท่าไหร่", total(lambda r: r[5])),
    ("บิลที่แพงที่สุดเดือนกันยายน 2026 ยอดเท่าไหร่", max(r[2] for r in SEED if SEP(r))),
    ("บิลที่ถูกที่สุดเดือนสิงหาคม 2026 ยอดเท่าไหร่", min(r[2] for r in SEED if AUG(r))),
    ("วันที่ 19 สิงหาคม 2026 จ่ายอะไรไป เท่าไหร่", 1200.0),
    ("ร้านสุกี้ริมคลองจ่ายไปเท่าไหร่", 742.0),
    ("ค่าอาหารสองเดือน สิงหาคมกับกันยายน 2026 รวมกันเท่าไหร่", total(lambda r: r[4] == "อาหาร")),
    ("ใช้เงินทั้งหมดตั้งแต่ 1 สิงหาคม ถึง 30 กันยายน 2026 เท่าไหร่", total(lambda r: True)),
]

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> list[float]:
    out = []
    for m in NUM.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def seed_user(ext: str) -> int:
    uid = agent.get_user(ext)
    with session() as s:
        u = s.get(User, uid)
        pid = tools._active_profile(u, s).id
        for vendor, date, tot, vat, cat, reimb in SEED:
            s.add(Invoice(profile_id=pid, status="confirmed", vendor=vendor, invoice_date=date, total=tot,
                          subtotal=round(tot - vat, 2), vat=vat, category=cat, currency="THB", total_thb=tot,
                          reimbursed_at=datetime.datetime.utcnow() if reimb else None))
        s.commit()
    return uid


def captured(uid: int) -> tuple[list[dict], list[str]]:
    """What the model asked for and what the tools gave back, straight from the conversation table."""
    with session() as s:
        rows = s.scalars(select(Conversation).where(Conversation.user_id == uid).order_by(Conversation.id)).all()
    calls, ctx = [], []
    for r in rows:
        t = r.content.get("text") or ""
        if r.role == "model" and t.startswith('{"tool"'):
            calls.append(json.loads(t))
        elif r.role == "user" and t.startswith("TOOL_RESULT"):
            ctx.append(t)
    return calls, ctx


async def main():
    init_db()
    recs = []
    for q, truth in QUESTIONS:
        ext = f"evalF:{uuid.uuid4().hex[:8]}"
        uid = seed_user(ext)
        out = await agent.run_turn(ext, q)
        reply = out["reply"]
        calls, ctx = captured(uid)
        support = numbers(q) + [n for c in ctx for n in numbers(c)]
        claims = numbers(reply)
        unsupported = [n for n in claims if not any(abs(n - x) < 0.01 for x in support)]
        rec = {"q": q, "truth": truth, "reply": reply, "tool_calls": calls, "context": ctx,
               "claims": claims, "unsupported": unsupported,
               "correct": any(abs(n - truth) < 0.01 for n in claims),
               "faithfulness": (1 - len(unsupported) / len(claims)) if claims else None}
        recs.append(rec)
        print(("✓" if rec["correct"] else "✗"), f"faith={rec['faithfulness']}", q, "|", reply[:80].replace("\n", " "), flush=True)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "faithfulness.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    scored = [r for r in recs if r["faithfulness"] is not None]
    n_claims = sum(len(r["claims"]) for r in recs)
    n_unsup = sum(len(r["unsupported"]) for r in recs)
    lines = ["# Eval F: correctness + faithfulness ของคำตอบ", "",
             f"- คำถาม {len(recs)} ข้อ บนข้อมูลสังเคราะห์ 10 บิล (คนละ user ต่อคำถาม เริ่มจากประวัติว่าง)",
             f"- correctness: **{sum(r['correct'] for r in recs)}/{len(recs)}** ตอบตัวเลขถูก",
             f"- faithfulness (เฉลี่ยต่อคำตอบ): **{sum(r['faithfulness'] for r in scored) / len(scored):.2f}** จาก {len(scored)} คำตอบที่มีตัวเลข",
             f"- ตัวเลขในคำตอบทั้งหมด {n_claims} ตัว ไม่มีที่มาใน context {n_unsup} ตัว",
             f"- เทิร์นที่เรียก tool อย่างน้อยหนึ่งครั้ง: {sum(bool(r['tool_calls']) for r in recs)}/{len(recs)}", "",
             "| | คำถาม | เฉลย | tool | ตัวเลขไม่มีที่มา |", "|---|---|---|---|---|"]
    for r in recs:
        tl = ", ".join(c["tool"] for c in r["tool_calls"]) or "-"
        lines.append(f"| {'✓' if r['correct'] else '✗'} | {r['q']} | {r['truth']:g} | {tl} | {', '.join(f'{n:g}' for n in r['unsupported']) or '-'} |")
    (OUT / "FAITHFULNESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:7]))


if __name__ == "__main__":
    asyncio.run(main())
