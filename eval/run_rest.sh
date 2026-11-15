#!/bin/sh
# The suites run_all.sh doesn't cover, on the current LLM. Inside the app container:  sh eval/run_rest.sh
cd /srv
O=eval/logs/run; mkdir -p $O
step() { echo "=== $1 $(date +%T)"; }
step before_fix;  python -m eval.eval_before_fix 3 > $O/before_fix.txt 2>&1
step handwritten; EVAL_DIR=handwritten python -m eval.eval_receipts > $O/handwritten.txt 2>&1
step receipts20;  EVAL_DIR=receipts python -m eval.eval_receipts > $O/receipts20.txt 2>&1
step hard20;      EVAL_DIR=receipts_hard python -m eval.eval_receipts > $O/hard20.txt 2>&1
step slips;       python -m eval.eval_slips > $O/slips.txt 2>&1
step ontology;    python -m eval.eval_ontology > $O/ontology.txt 2>&1
step embedding;   python -m eval.eval_embedding > $O/embedding.txt 2>&1
step ocr;         EVAL_DIR=dataset python -m eval.eval_ocr_ablation "" 60 > $O/ocr_ablation.txt 2>&1
step done
