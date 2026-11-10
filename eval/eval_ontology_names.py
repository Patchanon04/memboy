"""Blind check of the ontology rule on vendor names it was NOT written from.
The names file must be written by someone who has not read app/ontology.py (e.g. a teammate), one object per line of
JSON array: [{"vendor": "...", "category": "อาหาร|เดินทาง|ที่พัก|อุปกรณ์|สุขภาพ|ของใช้"}, ...]

    python -m eval.eval_ontology_names eval/ontology_names.json

Reports coverage (how many names the rule claims) and precision (of those, how many it puts in the right category).
Unclaimed names are not errors: they fall through to the model."""
import json
import sys
from pathlib import Path

from app import ontology

rows = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "eval/ontology_names.json").read_text(encoding="utf-8"))
claimed = [(r, ontology.classify(r["vendor"])) for r in rows]
claimed = [(r, c) for r, c in claimed if c]
right = [r for r, c in claimed if c[0] == r["category"]]
print(f"coverage {len(claimed)}/{len(rows)} · precision {len(right)}/{len(claimed)}")
for r, c in claimed:
    if c[0] != r["category"]:
        print(f"  WRONG {r['vendor']!r}: rule {c} vs gold {r['category']}")
