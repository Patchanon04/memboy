"""Run-to-run agreement at temperature 0: same 100 held-out images, two runs, how often does the model say the same thing?
    python eval/eval_repeat.py   (host or container; reads eval/dataset_test/eval_results.json (run 1, the headline) + eval_results_run2.json)"""
import json
from pathlib import Path

D = Path(__file__).parent / "dataset_test"
M = "gemma-4-26b-a4b-it"
a = {r["file"]: r for r in json.loads((D / "eval_results.json").read_text(encoding="utf-8"))[M]}
b = {r["file"]: r for r in json.loads((D / "eval_results_run2.json").read_text(encoding="utf-8"))[M]}
FIELDS = ["vendor", "date", "total", "vat", "category"]
same_all = sum(all(a[f]["pred"].get(k) == b[f]["pred"].get(k) for k in FIELDS) for f in a)
same_score = sum(a[f]["ok"] == b[f]["ok"] for f in a)
ok1 = sum(all(r["ok"].values()) for r in a.values())
ok2 = sum(all(r["ok"].values()) for r in b.values())
flips = [f"{f}: run1 {'✓' if all(a[f]['ok'].values()) else '✗'} run2 {'✓' if all(b[f]['ok'].values()) else '✗'}"
         for f in sorted(a) if all(a[f]["ok"].values()) != all(b[f]["ok"].values())]
per = {k: sum(a[f]["pred"].get(k) == b[f]["pred"].get(k) for f in a) for k in FIELDS}
lines = ["# Run-to-run agreement (held-out 100, temperature 0)", "",
         f"- all-5-correct: run1 **{ok1}/100** · run2 **{ok2}/100**",
         f"- identical prediction on all 5 fields: **{same_all}/100**",
         f"- identical right/wrong pattern: {same_score}/100",
         f"- per field identical: {per}", "", "Files whose all-5 result flipped:"] + [f"- {x}" for x in flips]
(Path(__file__).parent / "logs" / "REPEAT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
