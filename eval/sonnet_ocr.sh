#!/bin/sh
# Sonnet reading tests again with the OCR text (same harness as 12B now). Copies of the image sets so 12B results stay put.
cd /srv
OUT=eval/logs/models/claude-sonnet-5-5/ocr; mkdir -p $OUT
for d in dataset_test dataset_blind; do
  rm -rf eval/${d}_sonnet; mkdir eval/${d}_sonnet
  cp eval/$d/labels.json eval/$d/*.png eval/$d/*.jpg eval/$d/*.pdf eval/${d}_sonnet/ 2>/dev/null
  echo "=== $d $(date +%T)"
  EVAL_DIR=${d}_sonnet python -m eval.eval_receipts > $OUT/$d.txt 2>&1
  mv eval/${d}_sonnet/eval_results.json $OUT/${d}_eval_results.json
  rm -rf eval/${d}_sonnet
done
echo "=== done $(date +%T)"
