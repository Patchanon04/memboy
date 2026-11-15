#!/bin/sh
# Re-measure everything on the current LLM (app/llm.py: LLM_MODEL on an OpenAI-standard endpoint), then the harness ablation.
# Run inside the app container:  sh eval/run_all.sh      stdout of every suite → eval/logs/run/
cd /srv
O=eval/logs/run; mkdir -p $O
step() { echo "=== $1 $(date +%T)"; }

step faithfulness;  python -m eval.eval_faithfulness > $O/faithfulness.txt 2>&1
step tools;         python -m eval.eval_tools > $O/tools.txt 2>&1
step scenarios;     python -m eval.eval_scenarios > $O/scenarios.txt 2>&1
step injection;     python -m eval.eval_injection > $O/injection.txt 2>&1
step reject;        python -m eval.eval_reject > $O/reject.txt 2>&1
# held-out 100 twice: run 1 is the headline, run 2 is only for the repeatability check
step heldout1;      EVAL_DIR=dataset_test python -m eval.eval_receipts > $O/heldout_run1.txt 2>&1
cp eval/dataset_test/eval_results.json /tmp/run1.json
step heldout2;      EVAL_DIR=dataset_test python -m eval.eval_receipts > $O/heldout_run2.txt 2>&1
mv eval/dataset_test/eval_results.json eval/dataset_test/eval_results_run2.json
cp /tmp/run1.json eval/dataset_test/eval_results.json
python eval/eval_repeat.py > $O/repeat.txt 2>&1
step fresh60;       EVAL_DIR=dataset_blind python -m eval.eval_receipts > $O/fresh60.txt 2>&1

[ -z "$SKIP_ABLATION" ] && { step ablation; sh eval/eval_ablation.sh > $O/ablation.txt 2>&1; }
step done
