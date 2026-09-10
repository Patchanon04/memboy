"""Collect eval outputs into one markdown: eval/logs/EVAL_REPORT.md
Run inside container after the evals: python -m eval.make_report"""
import json
from collections import Counter
from pathlib import Path

LOGS = Path("/data/logs")
OUT = Path("/srv/eval/logs/EVAL_REPORT.md") if Path("/srv/eval/logs").exists() else Path("EVAL_REPORT.md")
md = ["# MemBoy — Evaluation Report (auto-generated)\n"]

# ---- A/D tool selection per model ----
for f in sorted(LOGS.glob("evalA_*.json")):
    if "subset" in f.name:
        continue
    res = json.loads(f.read_text(encoding="utf-8"))
    model = f.stem.replace("evalA_", "")
    fsub = f.with_name(f.stem + "_subset.json")  # cases re-run alone (CASE_IDS=...) replace their entry from the full run
    if fsub.exists() and fsub.stat().st_mtime > f.stat().st_mtime:
        latest = {r["id"]: r for r in json.loads(fsub.read_text(encoding="utf-8"))}
        res = [latest.get(r["id"], r) for r in res]
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

# ---- extraction: tuning set vs held-out ----
def _extract_block(path, title):
    if not path.exists():
        return
    res = json.loads(path.read_text(encoding="utf-8"))
    for model, rows_ in res.items():
        fields = list(rows_[0]["ok"])
        md.append(f"\n## {title} · `{model}` · {len(rows_)} files\n")
        md.append("| " + " | ".join(fields) + " | all-5 |\n|" + "---|" * (len(fields) + 1))
        md.append("| " + " | ".join(f"{sum(r['ok'][f] for r in rows_) / len(rows_):.0%}" for f in fields)
                  + f" | **{sum(all(r['ok'].values()) for r in rows_)}/{len(rows_)}** |")


EVAL = Path("/srv/eval") if Path("/srv/eval").exists() else Path("eval")
_extract_block(EVAL / "dataset" / "eval_results.json", "Extraction — tuning set (prompt v1→v3 was tuned on this; not the headline number)")
_extract_block(EVAL / "dataset_test" / "eval_results.json", "Extraction — HELD-OUT test set (seed 7, never used for tuning)")
_extract_block(EVAL / "handwritten" / "eval_results.json", "Extraction — HANDWRITTEN cash bills (separate hard set, synthetic, not a supported input)")

# ---- B scenarios ----
fb = LOGS / "evalB.json"
if fb.exists():
    res = json.loads(fb.read_text(encoding="utf-8"))
    fsub = LOGS / "evalB_subset.json"  # a scenario re-run alone (SCENARIO=...) replaces its entry from the full run
    if fsub.exists() and fsub.stat().st_mtime > fb.stat().st_mtime:
        latest = {r["name"]: r for r in json.loads(fsub.read_text(encoding="utf-8"))}
        res = [latest.get(r["name"], r) for r in res]
    md.append(f"\n## Eval B — end-to-end task success: {sum(r['ok'] for r in res)}/{len(res)}\n")
    for r in res:
        md.append(f"- {'✅' if r['ok'] else '❌'} {r['name']} {('— ' + '; '.join(r['fails'])) if r['fails'] else ''}")

# ---- slips ----
fs = LOGS / "eval_slips.json"
if fs.exists():
    res = json.loads(fs.read_text(encoding="utf-8"))
    fields = ["doc_type", "total", "ref", "qr_status"]
    md.append("\n## Slip extraction + QR consistency (30 synthetic slips, 6 layouts, 5 deliberate mismatches)\n")
    md.append("| field | accuracy |\n|---|---|")
    for f in fields:
        md.append(f"| {f} | {sum(r['ok'][f] for r in res) / len(res):.0%} |")
    md.append(f"| **all 4** | **{sum(all(r['ok'].values()) for r in res)}/{len(res)}** |")
    bad = [r for r in res if not all(r["ok"].values())]
    if bad:
        md.append("\nMisses: " + "; ".join(f"{r['file']} {[k for k, v in r['ok'].items() if not v]}" for r in bad))

# ---- C metrics from turn log ----
tl = LOGS / "turns.jsonl"
if tl.exists():
    rows = [json.loads(l) for l in tl.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if not r["user"].startswith(("test", "stub", "harness", "usage:"))]
    calls = sum(len(r["steps"]) for r in rows)
    perr = sum(1 for r in rows for s in r["steps"] if "parse_error" in s)
    tools_ = [s for r in rows for s in r["steps"] if "tool" in s]
    terr = sum(1 for s in tools_ if "tool_error" in s)
    md.append("\n## Eval C — loop metrics (all live turns)\n")
    md.append(f"- turns: {len(rows)} · LLM calls: {calls} · JSON first-try: **{100 * (1 - perr / max(1, calls)):.1f}%** · tool calls: {len(tools_)} (avg {len(tools_) / max(1, len(rows)):.2f}/turn) · tool errors: {terr} · loop-cap hits: {sum(1 for r in rows if 'ขั้นตอนเยอะเกินไป' in r['out'])}")
    md.append("- per tool: " + ", ".join(f"{k} {v}" for k, v in Counter(s["tool"] for s in tools_).most_common()))
    chain = Counter(len([s for s in r["steps"] if "tool" in s]) for r in rows)
    multi = sum(v for k, v in chain.items() if k >= 2)
    ask = sum(1 for r in rows if not any("tool" in s for s in r["steps"]) and ("?" in r["out"] or "ไหม" in r["out"]))
    errored = [r for r in rows if any("tool_error" in s for s in r["steps"])]
    recovered = sum(1 for r in errored if any("tool" in s and "tool_error" not in s for s in r["steps"][[i for i, s in enumerate(r["steps"]) if "tool_error" in s][0] + 1:]))
    u = [x["usage"] for x in rows if x.get("usage") and x["usage"].get("calls")]
    if u:
        lat = sorted(x["turn_s"] for x in u)
        pick = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))]
        md.append("\n### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)\n")
        md.append(f"- เวลาต่อเทิร์น: p50 **{pick(.5)}s** · p90 **{pick(.9)}s** · สูงสุด {lat[-1]}s (n={len(lat)}) — "
                  f"{100 * sum(x['llm_s'] for x in u) / max(.01, sum(x['turn_s'] for x in u)):.0f}% ของเวลาอยู่ที่การเรียก LLM")
        md.append(f"- token เฉลี่ยต่อเทิร์น: เข้า {sum(x['in_tok'] for x in u) / len(u):.0f} · ออก {sum(x['out_tok'] for x in u) / len(u):.0f} "
                  f"(รวมทั้งชุด {sum(x['in_tok'] for x in u):,} / {sum(x['out_tok'] for x in u):,})")
    
    # ---- safety: mutations must never run on a turn the user did not confirm (gate in app/gate.py) ----
    from app import gate
    GATE_SINCE = "2026-09-10T12:45"  # gate + 'exempt' flag for draft edits both live from here; earlier rows can't be classified
    gated_rows = [r for r in rows if r.get("ts", "") >= GATE_SINCE]
    executed = [(r, s) for r in gated_rows for s in r["steps"] if s.get("tool") in gate.GATED and "result" in s and s.get("gate") != "exempt"]
    unconfirmed = [(r, s) for r, s in executed if not (s.get("confirmed") or gate.is_confirm(r["in"].get("text")))]
    parked = sum(1 for r in gated_rows for s in r["steps"] if s.get("gated"))
    md.append("\n### Safety — confirm-before-mutate (program-enforced)\n")
    md.append(f"- gated tool calls parked for a preview: {parked} · executed after the user's own confirmation: {len(executed)} · "
              f"**executed without a confirming user message: {len(unconfirmed)}** (must be 0; n={len(gated_rows)} turns)")
    fr = LOGS / "eval_reject.json"
    if fr.exists():
        rj = json.loads(fr.read_text(encoding="utf-8"))
        md.append(f"- non-receipt images rejected (doc_type=other): **{rj['rejected']}/{rj['n']}** (eval/non_receipts, synthetic)")

    md.append("\n### Agency depth\n")
    md.append(f"- tool-chain length distribution: {dict(sorted(chain.items()))} — turns with ≥2 tool calls: **{multi}** ({100 * multi / max(1, len(rows)):.0f}%)")
    md.append(f"- ask-back turns (no tool, clarifying question): {ask} ({100 * ask / max(1, len(rows)):.0f}%)")
    md.append(f"- self-recovery after a tool error (agent tried another call): {recovered}/{len(errored)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
print(OUT)
print("\n".join(md))
