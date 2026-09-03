"""Slip extraction + QR consistency eval over eval/slips (30 synthetic slips, 6 layouts, 5 deliberate QR mismatches).
Scores: doc_type, total, transfer_ref, qr_status per slip, per layout. Run in container: python -m eval.eval_slips"""
import asyncio
import json
import shutil
import uuid
from collections import defaultdict
from pathlib import Path

from app import agent, tools
from app.db import User, init_db, session

DIR = Path("/srv/eval/slips")
LABELS = json.loads((DIR / "labels.json").read_text(encoding="utf-8"))


async def main():
    init_db()
    uid = agent.get_user(f"evalS:{uuid.uuid4().hex[:6]}")
    rows, by_layout = [], defaultdict(lambda: [0, 0])
    with session() as s:
        u = s.get(User, uid)
        for lab in LABELS:
            dst = Path("/data/uploads") / f"evalS-{uuid.uuid4().hex[:8]}.png"
            shutil.copy(DIR / lab["file"], dst)
            try:
                r = await tools.analyze_receipt(u, s, image_id=dst.stem)
            except tools.ToolError as e:
                r = {"error": str(e)}
            ok = {"doc_type": r.get("doc_type") == "transfer_slip",
                  "total": r.get("total") is not None and abs(r["total"] - lab["total"]) < 0.01,
                  "ref": (r.get("transfer_ref") or "") == lab["transfer_ref"],
                  "qr_status": r.get("qr_status") == lab["qr_expected"]}
            rows.append({"file": lab["file"], "ok": ok, "got": {k: r.get(k) for k in ("doc_type", "total", "transfer_ref", "qr_status")}})
            by_layout[lab["layout"]][0] += all(ok.values())
            by_layout[lab["layout"]][1] += 1
            print(f"{'✓' if all(ok.values()) else '✗'} {lab['file']:28} {ok}", flush=True)
    fields = ["doc_type", "total", "ref", "qr_status"]
    print("\nSLIPS ACCURACY: " + "  ".join(f"{f}={sum(r['ok'][f] for r in rows) / len(rows):.0%}" for f in fields)
          + f"  all={sum(all(r['ok'].values()) for r in rows)}/{len(rows)}")
    print("per layout:", {k: f"{a}/{b}" for k, (a, b) in sorted(by_layout.items())})
    mism = [r for r, lab in zip(rows, LABELS) if lab["qr_expected"] == "mismatch"]
    print(f"QR mismatch detection: {sum(r['ok']['qr_status'] for r in mism)}/{len(mism)}")
    Path("/data/logs/eval_slips.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
