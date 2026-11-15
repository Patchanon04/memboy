#!/bin/sh
cd /srv
O=eval/logs/run
step() { echo "=== $1 $(date +%T)"; }
step tuning200; EVAL_DIR=dataset python -m eval.eval_receipts > $O/tuning200.txt 2>&1
step ontology;  python -m eval.eval_ontology > $O/ontology.txt 2>&1
step ablation;  sh eval/eval_ablation.sh > $O/ablation.txt 2>&1
step report;    python -m eval.make_report > $O/report.txt 2>&1
step done
