#!/bin/sh
# Run the main suites (no ablation) on another model without touching the current results:
# snapshot them, run, move the new outputs to eval/logs/models/<model>/, put the snapshot back.
# e.g. with the Claude CLI bridge running on the host (scripts/claude_cli_bridge.py):
#   docker compose exec -T -e LLM_BASE_URL=http://host.docker.internal:8765/v1 -e LLM_MODEL=claude-sonnet-5-5 \
#     -e LLM_KEEP_ALIVE= -e LLM_REASONING_EFFORT= app sh eval/compare_model.sh
cd /srv
M=${LLM_MODEL:?set LLM_MODEL}
KEEP=/tmp/keep; OUT=eval/logs/models/$M
FILES="eval/logs/run eval/logs/FAITHFULNESS.md eval/logs/faithfulness.jsonl eval/logs/INJECTION.md eval/logs/REPEAT.md
eval/dataset_test/eval_results.json eval/dataset_test/eval_results_run2.json eval/dataset_blind/eval_results.json"
rm -rf $KEEP $OUT; mkdir -p $KEEP $OUT
for f in $FILES; do k=$(echo $f | tr / _); cp -r $f $KEEP/$k; done
SKIP_ABLATION=1 sh eval/run_all.sh
for f in $FILES; do k=$(echo $f | tr / _); rm -rf $OUT/$k; mv $f $OUT/$k; cp -r $KEEP/$k $f; done
echo "results for $M in $OUT"
