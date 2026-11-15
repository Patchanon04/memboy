"""Ablation: does OCR-before-LLM help speed or accuracy?  A image-only (prod) · B image+OCR text · C OCR text only.
Same prompt/scoring as eval_receipts.py; all three conditions run back-to-back per file so load drift hits them equally.
Run inside the app container (needs tesseract tha+eng):  EVAL_DIR=dataset python -m eval.eval_ocr_ablation [model] [N]
"""
import asyncio
import base64
import json
import re
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app import llm, tools
from eval.eval_receipts import DIR, LABELS, PROMPT, score, to_image

MODEL = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else llm.MODEL
N = int(sys.argv[2]) if len(sys.argv) > 2 else len(LABELS)
COND = ("image", "image+ocr", "ocr")


def ocr(data: bytes, mime: str) -> tuple[str, float]:
    t = time.perf_counter()
    with tempfile.NamedTemporaryFile(suffix=".jpg" if mime == "image/jpeg" else ".png", delete=False) as f:
        f.write(data)
    try:
        out = subprocess.run(["tesseract", f.name, "stdout", "-l", "tha+eng", "--psm", "6"],
                             capture_output=True, text=True, timeout=120).stdout
    finally:
        os.unlink(f.name)
    return out.strip(), time.perf_counter() - t


def parts(cond, data, mime, text):
    p = []
    if cond != "ocr":
        p.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
    if cond == "image":
        p.append({"text": PROMPT})
    elif cond == "image+ocr":
        p.append({"text": f"ข้อความ OCR จากใบเสร็จ (อาจอ่านผิดบางส่วน ใช้ประกอบกับรูป):\n{text}\n\n{PROMPT}"})
    else:
        p.append({"text": f"ข้อความ OCR จากใบเสร็จ (ไม่มีรูปแนบ อ่านจากข้อความนี้เท่านั้น):\n{text}\n\n{PROMPT}"})
    return p


async def call(contents):
    """Returns (pred, seconds, prompt_tokens, attempts)."""
    t = time.perf_counter()
    acc = {"calls": 0, "llm_s": 0.0, "in_tok": 0, "out_tok": 0, "models": []}
    tok = llm.USAGE.set(acc)
    try:
        text = await llm.generate(contents, model=MODEL)
    except llm.LLMError as e:
        return {"_raw": f"error {e}"}, time.perf_counter() - t, 0, 1
    finally:
        llm.USAGE.reset(tok)
    m = re.search(r"\{.*\}", text, re.S)
    try:
        pred = json.loads(m.group(0)) if m else {"_raw": text}
    except json.JSONDecodeError:
        pred = {"_raw": text}
    if "date_raw" in pred:  # same as the app: the model copies the date, code converts the year
        pred["date"] = tools.thai_date(pred["date_raw"]) or pred.get("date")
    return pred, time.perf_counter() - t, acc["in_tok"], 1


SAFE = MODEL.replace(":", "-")
PARTIAL = DIR / f"ocr_ablation_{SAFE}.partial.jsonl"


async def one(sem, lab):
    async with sem:
        path = DIR / lab["file"]
        data, mime = await asyncio.to_thread(to_image, path)
        text, ocr_s = await asyncio.to_thread(ocr, data, mime)
        row = {"file": lab["file"], "ocr_s": round(ocr_s, 2), "ocr_chars": len(text)}
        for c in COND:
            pred, s, ptok, att = await call([{"role": "user", "parts": parts(c, data, mime, text)}])
            row[c] = {"ok": score(pred, lab), "llm_s": round(s, 2), "prompt_tok": ptok, "attempts": att, "pred": pred}
        print(f"{lab['file']:22} ocr {ocr_s:4.1f}s/{len(text):4}ch  " +
              "  ".join(f"{c}: {sum(row[c]['ok'].values())}/5 {row[c]['llm_s']:5.1f}s {row[c]['prompt_tok']:5}tok" for c in COND), flush=True)
        with open(PARTIAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


async def main():
    labs = LABELS[:N]
    done = {}
    if PARTIAL.exists():
        for l in PARTIAL.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                done[r["file"]] = r
    todo = [l for l in labs if l["file"] not in done]
    print(f"{len(done)} files already done, {len(todo)} to go", flush=True)
    sem = asyncio.Semaphore(1)  # one local GPU
    fresh = await asyncio.gather(*(one(sem, l) for l in todo))
    rows = [done.get(l["file"]) or next(r for r in fresh if r["file"] == l["file"]) for l in labs]
    out = DIR / f"ocr_ablation_{SAFE}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    fields = list(rows[0]["image"]["ok"])
    ocr_mean = statistics.mean(r["ocr_s"] for r in rows)
    md = [f"# OCR ablation · `{MODEL}` · {len(rows)} files (tesseract 5 tha+eng, psm 6; OCR mean {ocr_mean:.2f}s/file)\n",
          "| condition | " + " | ".join(fields) + " | all-5 | LLM p50 | LLM p90 | LLM mean | +OCR mean | prompt tok mean | retries |",
          "|---|" + "---|" * (len(fields) + 7)]
    for c in COND:
        lat = [r[c]["llm_s"] for r in rows]
        extra = ocr_mean if c != "image" else 0.0
        md.append(f"| {c} | " + " | ".join(f"{sum(r[c]['ok'][f] for r in rows) / len(rows):.0%}" for f in fields)
                  + f" | **{sum(all(r[c]['ok'].values()) for r in rows)}/{len(rows)}** | {pct(lat, .5):.1f}s | {pct(lat, .9):.1f}s | {statistics.mean(lat):.1f}s"
                  f" | {statistics.mean(lat) + extra:.1f}s | {statistics.mean(r[c]['prompt_tok'] for r in rows):.0f} | {sum(r[c]['attempts'] - 1 for r in rows)} |")
    # where OCR changed the outcome
    flips = [(r["file"], sum(r["image"]["ok"].values()), sum(r["image+ocr"]["ok"].values()), sum(r["ocr"]["ok"].values()))
             for r in rows if len({sum(r[c]["ok"].values()) for c in COND}) > 1]
    md.append(f"\nfiles where conditions disagree (image / image+ocr / ocr, fields correct of 5): {len(flips)}\n")
    md += [f"- {f}: {a} / {b} / {c}" for f, a, b, c in flips]
    rep = Path("/srv/eval/logs/OCR_ABLATION.md") if Path("/srv/eval/logs").exists() else DIR / "OCR_ABLATION.md"
    rep.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md[:6]))
    print("report:", rep)


if __name__ == "__main__":
    asyncio.run(main())
