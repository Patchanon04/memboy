"""Harness tuning check: ask the same 20 money questions 5 times (fresh user each time, same synthetic bills) and see
whether the essence of the answer stays the same.
  essence kept  = the right number is in the reply in all 5 runs
  same numbers  = the set of numbers in the reply is identical in all 5 runs (stricter: wording can still differ)
Run inside the container:  python -m eval.eval_repeat5      → eval/logs/REPEAT5_<model>.md + repeat5_<model>.jsonl
"""
import asyncio
import json
from pathlib import Path

from app import agent, llm
from app.db import init_db
from eval.eval_faithfulness import QUESTIONS, numbers, seed_user

RUNS = 5
OUT = Path(__file__).parent / "logs"


async def main():
    init_db()
    tag = llm.MODEL.replace(":", "-")
    rows = []
    for q, truth in QUESTIONS:
        replies = []
        for i in range(RUNS):
            ext = f"evalR5:{abs(hash((q, i))) % 10**8}:{i}"
            seed_user(ext)
            replies.append((await agent.run_turn(ext, q))["reply"])
        nums = [sorted({round(n, 2) for n in numbers(r)}) for r in replies]
        right = [any(abs(n - truth) < 0.01 for n in ns) for ns in nums]
        rows.append({"q": q, "truth": truth, "replies": replies, "numbers": nums,
                     "essence_kept": all(right), "right_runs": sum(right), "same_numbers": all(n == nums[0] for n in nums)})
        print(f"{'✓' if rows[-1]['essence_kept'] else '✗'} {sum(right)}/{RUNS} same_numbers={rows[-1]['same_numbers']} {q}", flush=True)
    with open(OUT / f"repeat5_{tag}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kept = sum(r["essence_kept"] for r in rows)
    same = sum(r["same_numbers"] for r in rows)
    lines = [f"# ถามคำถามเดิม {RUNS} ครั้ง ({llm.MODEL})", "",
             f"- คำถาม {len(rows)} ข้อ ถามข้อละ {RUNS} ครั้ง (user ใหม่ทุกครั้ง บิลสังเคราะห์ชุดเดิม ขอ temperature 0 ถ้า server ไม่รองรับจะใช้ค่าเริ่มต้นของโมเดล)",
             f"- สาระสำคัญคงเดิม (ตัวเลขที่ถูกอยู่ในคำตอบครบทั้ง {RUNS} ครั้ง): **{kept}/{len(rows)}**",
             f"- ตัวเลขในคำตอบเหมือนกันทุกครั้ง: **{same}/{len(rows)}**",
             f"- คำตอบที่มีตัวเลขถูก: {sum(r['right_runs'] for r in rows)}/{len(rows) * RUNS}", "",
             "| คำถาม | เฉลย | ถูกกี่ครั้ง | ตัวเลขเหมือนกันทุกครั้ง |", "|---|---|---|---|"]
    lines += [f"| {r['q']} | {r['truth']:g} | {r['right_runs']}/{RUNS} | {'ใช่' if r['same_numbers'] else 'ไม่'} |" for r in rows]
    (OUT / f"REPEAT5_{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:6]))


if __name__ == "__main__":
    asyncio.run(main())
