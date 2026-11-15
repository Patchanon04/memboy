#!/bin/sh
# After adding mark_reimbursed/manage_category to the gate: re-run the suites that touch them, the harness, the report.
cd /srv
O=eval/logs/run
while [ ! eval/logs/OCR_ABLATION.md -nt eval/run_rest.sh ]; do sleep 15; done   # wait for run_rest.sh's last suite
step() { echo "=== $1 $(date +%T)"; }
step scenarios; python -m eval.eval_scenarios > $O/scenarios.txt 2>&1
step tools;     python -m eval.eval_tools > $O/tools.txt 2>&1
step demo;      python /tmp/demo_turns.py > $O/demo_turns.txt 2>&1
step harness;   python -m tests.test_harness > $O/harness.txt 2>&1
step report;    python -m eval.make_report > $O/report.txt 2>&1
step done
