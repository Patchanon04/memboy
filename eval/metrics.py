"""Eval C: free metrics from the turn log. Run: python -m eval.metrics [/data/logs/turns.jsonl] [user-prefix]"""
import json
import sys
from collections import Counter
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/data/logs/turns.jsonl")
prefix = sys.argv[2] if len(sys.argv) > 2 else ""
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
EXCLUDE = ("test", "stub", "harness", "usage:")  # deliberate stub turns (e.g. loop-cap test) are not live behaviour
rows = [r for r in rows if r["user"].startswith(prefix) and not r["user"].startswith(EXCLUDE)]
turns = len(rows)
llm_calls = sum(len(r["steps"]) for r in rows)
parse_err = sum(1 for r in rows for s in r["steps"] if "parse_error" in s)
tool_calls = [s for r in rows for s in r["steps"] if "tool" in s]
tool_err = sum(1 for s in tool_calls if "tool_error" in s)
cap_hits = sum(1 for r in rows if "ขั้นตอนเยอะเกินไป" in r["out"])
per_tool = Counter(s["tool"] for s in tool_calls)
print(f"turns={turns} llm_calls={llm_calls}")
print(f"json_first_try={100 * (1 - parse_err / max(1, llm_calls)):.1f}%  (parse errors {parse_err})")
print(f"tool_calls={len(tool_calls)} avg/turn={len(tool_calls) / max(1, turns):.2f} tool_errors={tool_err} ({100 * tool_err / max(1, len(tool_calls)):.1f}%)")
print(f"loop_cap_hits={cap_hits}")
print("per_tool:", dict(per_tool.most_common()))

# ---- agency depth ----
from collections import Counter as _C
chain = _C(len([s for s in r["steps"] if "tool" in s]) for r in rows)
ask_back = sum(1 for r in rows if not any("tool" in s for s in r["steps"]) and ("?" in r["out"] or "ไหม" in r["out"] or "ใบไหน" in r["out"]))
recovered = sum(1 for r in rows if any("tool_error" in s for s in r["steps"]) and any("tool" in s and "tool_error" not in s for s in r["steps"][[i for i, s in enumerate(r["steps"]) if "tool_error" in s][0] + 1:]))
errored = sum(1 for r in rows if any("tool_error" in s for s in r["steps"]))
print(f"chain_length_distribution={dict(sorted(chain.items()))}  turns_with_chain>=2={sum(v for k, v in chain.items() if k >= 2)} ({100 * sum(v for k, v in chain.items() if k >= 2) / max(1, turns):.0f}%)")
print(f"ask_back_turns={ask_back} ({100 * ask_back / max(1, turns):.0f}%)  self_recovery_after_tool_error={recovered}/{errored}")

# ---- latency & tokens (turns recorded after instrumentation) ----
u = [r["usage"] for r in rows if r.get("usage") and r["usage"].get("calls")]
if u:
    import statistics as st
    lat = sorted(x["turn_s"] for x in u)
    p = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))]
    print(f"latency_turns={len(lat)} p50={p(.5)}s p90={p(.9)}s max={lat[-1]}s  llm_share={100 * sum(x['llm_s'] for x in u) / max(.01, sum(x['turn_s'] for x in u)):.0f}%")
    print(f"tokens/turn: in={st.mean(x['in_tok'] for x in u):.0f} out={st.mean(x['out_tok'] for x in u):.0f}  total_in={sum(x['in_tok'] for x in u)} total_out={sum(x['out_tok'] for x in u)}")
