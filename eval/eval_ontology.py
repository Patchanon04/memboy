"""Does the ontology help or hurt category accuracy? Replays the saved extraction results (no LLM calls):
the model's category vs. ontology-over-model (rule wins when a keyword knows the vendor, else the model's answer).

    python -m eval.eval_ontology            → table + eval/logs/ONTOLOGY.md

Caveat printed with the result: the keyword list was written after looking at the tuning-set misses, and the held-out
misses were seen while writing this script — the held-out number is therefore not blind for this change."""
import json
from pathlib import Path

from app import ontology

SETS = {"tuning (dataset, 200)": Path("eval/dataset"), "held-out (dataset_test, 100)": Path("eval/dataset_test")}
if Path("eval/dataset_blind/eval_results.json").exists():  # seed 31, made after the keywords were frozen; same vendor pool
    SETS["fresh images (dataset_blind, 60)"] = Path("eval/dataset_blind")


def run(folder: Path) -> dict:
    gold = {r["file"]: r for r in json.loads((folder / "labels.json").read_text(encoding="utf-8"))}
    preds = json.loads((folder / "eval_results.json").read_text(encoding="utf-8"))["gemma-4-26b-a4b-it"]
    known = [r for r in gold.values() if ontology.classify(r["vendor"])]  # coverage/precision on the true names
    rule_ok = sum(ontology.classify(r["vendor"])[0] == r["category"] for r in known)
    llm = both = 0
    fixed, broke = [], []
    for p in preds:
        g = gold[p["file"]]["category"]
        model_cat = p["pred"].get("category")
        hit = ontology.classify(p["pred"].get("vendor"))
        final = hit[0] if hit else model_cat
        llm += model_cat == g
        both += final == g
        if model_cat != g and final == g:
            fixed.append(f'{p["file"]}: "{p["pred"].get("vendor")}" {model_cat}→{final}')
        if model_cat == g and final != g:
            broke.append(f'{p["file"]}: "{p["pred"].get("vendor")}" {model_cat}→{final}')
    return {"n": len(preds), "coverage": f"{len(known)}/{len(gold)}", "rule_precision": f"{rule_ok}/{len(known)}",
            "llm": llm, "llm+ontology": both, "fixed": fixed, "broke": broke}


if __name__ == "__main__":
    lines = ["# Ontology vs model — category accuracy (replayed, no new LLM calls)", "",
             "| set | vendors the ontology knows | rule correct on those | model alone | model + ontology |",
             "|---|---|---|---|---|"]
    notes = []
    for name, folder in SETS.items():
        r = run(folder)
        lines.append(f"| {name} | {r['coverage']} | {r['rule_precision']} | {r['llm']}/{r['n']} | **{r['llm+ontology']}/{r['n']}** |")
        notes += [f"- {name} fixed: {x}" for x in r["fixed"]] + [f"- {name} **broke**: {x}" for x in r["broke"]]
    lines += ["", *notes, "",
              "> Not blind: keywords were written after seeing the tuning-set misses, and the held-out misses were seen "
              "while building this check. Keywords are generic Thai expense words/chains (ปั๊ม, บางจาก, สปา, ถ่ายเอกสาร, "
              "ร้านทุกอย่าง), not the synthetic vendor names — but treat the gain as indicative until a fresh set confirms it."]
    out = "\n".join(lines)
    print(out)
    Path("eval/logs/ONTOLOGY.md").write_text(out + "\n", encoding="utf-8")
