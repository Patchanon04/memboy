#!/bin/sh
# OCR text next to the image in analyze_receipt: re-measure what reads images. Image-only results: eval/logs/run/image_only/
cd /srv
O=eval/logs/run
step() { echo "=== $1 $(date +%T)"; }
step heldout1;  EVAL_DIR=dataset_test python -m eval.eval_receipts > $O/heldout_run1.txt 2>&1
cp eval/dataset_test/eval_results.json /tmp/run1.json
step heldout2;  EVAL_DIR=dataset_test python -m eval.eval_receipts > $O/heldout_run2.txt 2>&1
mv eval/dataset_test/eval_results.json eval/dataset_test/eval_results_run2.json
cp /tmp/run1.json eval/dataset_test/eval_results.json
python eval/eval_repeat.py > $O/repeat.txt 2>&1
step fresh60;   EVAL_DIR=dataset_blind python -m eval.eval_receipts > $O/fresh60.txt 2>&1
step injection; python -m eval.eval_injection > $O/injection.txt 2>&1
step reject;    python -m eval.eval_reject > $O/reject.txt 2>&1
step slips;     python -m eval.eval_slips > $O/slips.txt 2>&1
step scenarios; python -m eval.eval_scenarios > $O/scenarios.txt 2>&1
step ontology;  python -m eval.eval_ontology > $O/ontology.txt 2>&1
step report;    python -m eval.make_report > $O/report.txt 2>&1
step done
