#!/bin/sh
# Harness ablation: same model, same three suites, one harness layer switched off per run (agent.HARNESS_OFF).
#   faithfulness (20 money questions) · scenarios (11 multi-turn, scored on DB state) · injection (5 receipts with orders)
# Baseline ("none") = the reports run_all.sh just wrote. Run inside the app container:  sh eval/eval_ablation.sh
# The suites overwrite their own reports, so the baseline reports are put back at the end.
cd /srv
L=eval/logs; A=$L/ablation; mkdir -p $A
cp $L/FAITHFULNESS.md $L/faithfulness.jsonl $L/INJECTION.md $A/ 2>/dev/null
for cfg in gate args route retry ontology; do
  echo "=== $cfg $(date +%T)"
  n0=$(wc -l < /data/logs/turns.jsonl)
  {
    HARNESS_OFF=$cfg python -m eval.eval_faithfulness | grep -E "correctness|faithfulness \("
    HARNESS_OFF=$cfg python -m eval.eval_scenarios | grep -E "^✗|TASK SUCCESS"
    HARNESS_OFF=$cfg python -m eval.eval_injection | grep -E "data unchanged"
  } > $A/$cfg.log 2>&1
  tail -n +$((n0 + 1)) /data/logs/turns.jsonl > /tmp/t.jsonl
  echo "LLM_ERRORS $(grep -c llm_error /tmp/t.jsonl)/$(wc -l < /tmp/t.jsonl)" >> $A/$cfg.log
  cat $A/$cfg.log
done
cp $A/FAITHFULNESS.md $A/faithfulness.jsonl $A/INJECTION.md $L/ 2>/dev/null
rm -f $A/FAITHFULNESS.md $A/faithfulness.jsonl $A/INJECTION.md
python - <<'EOF'
import re
from pathlib import Path
L, A = Path("eval/logs"), Path("eval/logs/ablation")
name = {"none": "ครบทุกชั้น", "gate": "ปิด gate (contract pre-tool-use)", "args": "ปิด check_args",
        "route": "ปิด ROUTE_IMAGE (ให้โมเดลเลือกเองว่าจะอ่านรูป)", "retry": "ปิด _parse ขอใหม่", "ontology": "ปิด ontology"}
P_COR, P_FAI = r"correctness: \*\*(\d+)/", r"faithfulness \(.*?\*\*([\d.]+)\*\*"
P_SC, P_INJ = r"TASK SUCCESS: (\d+)/", r"unchanged without user confirmation: (\d+)/"
P_ERR = r"LLM_ERRORS (\d+/\d+)"
def num(pat, t):
    m = re.search(pat, t)
    return m.group(1) if m else "?"
def text(cfg):
    if cfg == "none":  # baseline = the full run's own outputs
        return "\n".join((L / f).read_text(encoding="utf-8") for f in ("FAITHFULNESS.md", "INJECTION.md", "run/scenarios.txt") if (L / f).exists())
    return (A / f"{cfg}.log").read_text(encoding="utf-8") if (A / f"{cfg}.log").exists() else ""
rows = ["# Harness ablation: ปิดทีละชั้น แล้วนับข้อที่ผ่าน", "",
        "โมเดลเดียวกัน (LLM_MODEL ใน app/llm.py, temperature 0) ข้อมูลสังเคราะห์ทั้งหมด รันครั้งเดียวต่อแบบ", "",
        "| แบบ | ถามยอด ตอบถูก (20) | faithfulness | scenario ผ่าน (11) | ใบเสร็จแอบสั่ง ข้อมูลไม่เปลี่ยน (5) | เทิร์นที่ LLM ล่ม |", "|---|---|---|---|---|---|"]
for cfg in name:
    t = text(cfg)
    rows.append(f"| {name[cfg]} | {num(P_COR, t)} | {num(P_FAI, t)} | {num(P_SC, t)} | {num(P_INJ, t)} | {num(P_ERR, t) if cfg != 'none' else '-'} |")
rows += ["", "scenario ที่ตกในแต่ละแบบ:"]
for cfg in name:
    fails = [l[2:].strip() for l in text(cfg).splitlines() if l.startswith("✗")]
    rows.append(f"- {name[cfg]}: {'; '.join(fails) or '-'}")
(L / "ABLATION.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("\n".join(rows))
EOF
