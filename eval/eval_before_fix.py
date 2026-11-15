"""Re-create the three bugs from the "found while testing" slides on the current model, to show the before/after with
the same model. Each fix is undone in memory only (nothing on disk changes), then the same question is asked as before.
  delete  — old prompt rule "finish every part" without the "ask first when the target is unclear" rule
  args    — summarize_expenses without `vendor`, extra args silently dropped (check_args off)
  sum     — find_invoices without the code-computed "total"
Run inside the container:  python -m eval.eval_before_fix [repeats]   → eval/logs/BEFORE_FIX.md"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

from app import agent, llm, tools
from app.db import init_db
from eval.eval_faithfulness import captured, seed_user
from eval.eval_tools import seed

OUT = Path(__file__).parent / "logs" / "BEFORE_FIX.md"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
NEW_RULE = "- คำสั่งซ้อน (\"บันทึกแล้วขอรีพอร์ทด้วย\") → ทำให้ครบทุกส่วน**ที่ระบุชัดแล้ว**"
ASK_RULE = "- กำกวมแล้วต้อง**ถามก่อน**"


def old_prompt(orig):
    def f(user, s):
        p = orig(user, s)
        assert NEW_RULE in p and ASK_RULE in p
        p = p.replace(NEW_RULE, NEW_RULE.replace("**ที่ระบุชัดแล้ว**", ""))
        return "\n".join(l for l in p.split("\n") if not l.startswith(ASK_RULE))
    return f


def no_vendor(user, s, date_from=None, date_to=None, category=None, reimbursed=None, profile=None, compare_to=None, **_):
    return tools.summarize_expenses(user, s, date_from, date_to, category, reimbursed, profile, compare_to)


def no_total(user, s, date_from=None, date_to=None, vendor=None, category=None, reimbursed=None, profile=None,
             item=None, limit=20, **_):
    out = tools.find_invoices(user, s, date_from, date_to, vendor, category, reimbursed, profile, item, limit)
    out.pop("total", None)
    return out


async def ask(ext, q):
    out = await agent.run_turn(ext, q)
    return out["reply"]


async def case(name, before):
    """before=True: undo the fix; returns (reply, tool calls)."""
    real_prompt, real_tools, off = agent.system_prompt, dict(agent.TOOLS), set(agent.HARNESS_OFF)
    try:
        if name == "delete":
            if before:
                agent.system_prompt = old_prompt(real_prompt)
            ext = f"evalB:{uuid.uuid4().hex[:8]}"
            seed(ext, {"confirmed": [{"vendor": "แท็กซี่มิเตอร์", "total": 180}, {"vendor": "ครัวป้าแดง", "total": 120}]})
            reply = await ask(ext, "ลบบิลทิ้งหน่อย")
            uid = agent.get_user(ext)
        else:
            if before and name == "args":
                fn, desc, args = real_tools["summarize_expenses"]
                agent.TOOLS["summarize_expenses"] = (no_vendor, desc, {k: v for k, v in args.items() if k != "vendor"})
                agent.HARNESS_OFF.add("args")
            if before and name == "sum":
                fn, desc, args = real_tools["find_invoices"]
                agent.TOOLS["find_invoices"] = (no_total, desc, args)
            ext = f"evalB:{uuid.uuid4().hex[:8]}"
            uid = seed_user(ext)
            reply = await ask(ext, {"args": "จ่ายค่า Grab ไปทั้งหมดกี่บาท", "sum": "ร้านกาแฟสามแยกจ่ายไปรวมเท่าไหร่"}[name])
        calls, ctx = captured(uid)
        return reply, calls, ctx
    finally:
        agent.system_prompt = real_prompt
        agent.TOOLS.clear(); agent.TOOLS.update(real_tools)
        agent.HARNESS_OFF.clear(); agent.HARNESS_OFF.update(off)


async def main():
    init_db()
    lines = [f"# บั๊กเดิม จำลองกับ {llm.MODEL}", "",
             "ย้อนการแก้แต่ละจุดในหน่วยความจำ (ไฟล์ไม่เปลี่ยน) แล้วถามคำถามเดิม เทียบกับตอนที่แก้แล้ว", ""]
    for name in ("delete", "args", "sum"):
        for before in (True, False):
            for i in range(N):
                reply, calls, ctx = await case(name, before)
                tl = ", ".join(f"{c['tool']}({json.dumps(c.get('args', {}), ensure_ascii=False)})" for c in calls) or "-"
                row = f"- **{name}** {'ก่อนแก้' if before else 'แก้แล้ว'} #{i + 1}: tool {tl} → \"{reply}\""
                if name == "sum":
                    row += f" · context มี total: {any(chr(34) + 'total' + chr(34) + ': 275' in c for c in ctx)}"
                print(row, flush=True)
                lines.append(row)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
