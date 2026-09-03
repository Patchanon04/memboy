"""Collect eval outputs into one markdown: eval/logs/EVAL_REPORT.md
Run inside container after the evals: python -m eval.make_report"""
import json
from collections import Counter
from pathlib import Path

LOGS = Path("/data/logs")
OUT = Path("/srv/eval/logs/EVAL_REPORT.md") if Path("/srv/eval/logs").exists() else Path("EVAL_REPORT.md")
md = ["# PBook — Evaluation Report (auto-generated)\n"]

# ---- A/D tool selection per model ----
for f in sorted(LOGS.glob("evalA_*.json")):
    if "subset" in f.name:
        continue
    res = json.loads(f.read_text(encoding="utf-8"))
    model = f.stem.replace("evalA_", "")
    md.append(f"\n## Eval A/D — tool selection · `{model}`\n")
    groups = {}
    for r in res:
        g = groups.setdefault(r["group"], [0, 0])
        g[0] += r["ok"]
        g[1] += 1
    md.append("| group | pass | rate |\n|---|---|---|")
    for g, (a, b) in sorted(groups.items()):
        md.append(f"| {g} | {a}/{b} | {a / b:.0%} |")
    tot = sum(r["ok"] for r in res)
    md.append(f"| **ALL** | **{tot}/{len(res)}** | **{tot / len(res):.0%}** |")
    fails = [r for r in res if not r["ok"]]
    if fails:
        md.append("\nFailures:\n")
        for r in fails:
            md.append(f"- #{r['id']} {r['group']}: {r['why']} — tools={r['tools']} — reply: {r['reply'][:80]}")

# ---- B scenarios ----
fb = LOGS / "evalB.json"
if fb.exists():
    res = json.loads(fb.read_text(encoding="utf-8"))
    md.append(f"\n## Eval B — end-to-end task success: {sum(r['ok'] for r in res)}/{len(res)}\n")
    for r in res:
        md.append(f"- {'✅' if r['ok'] else '❌'} {r['name']} {('— ' + '; '.join(r['fails'])) if r['fails'] else ''}")

# ---- C metrics from turn log ----
tl = LOGS / "turns.jsonl"
if tl.exists():
    rows = [json.loads(l) for l in tl.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if not r["user"].startswith(("test", "stub"))]
    calls = sum(len(r["steps"]) for r in rows)
    perr = sum(1 for r in rows for s in r["steps"] if "parse_error" in s)
    tools_ = [s for r in rows for s in r["steps"] if "tool" in s]
    terr = sum(1 for s in tools_ if "tool_error" in s)
    md.append("\n## Eval C — loop metrics (all live turns)\n")
    md.append(f"- turns: {len(rows)} · LLM calls: {calls} · JSON first-try: **{100 * (1 - perr / max(1, calls)):.1f}%** · tool calls: {len(tools_)} (avg {len(tools_) / max(1, len(rows)):.2f}/turn) · tool errors: {terr} · loop-cap hits: {sum(1 for r in rows if 'ขั้นตอนเยอะเกินไป' in r['out'])}")
    md.append("- per tool: " + ", ".join(f"{k} {v}" for k, v in Counter(s["tool"] for s in tools_).most_common()))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
print(OUT)
print("\n".join(md))
