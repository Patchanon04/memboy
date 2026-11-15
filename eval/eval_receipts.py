"""Field-level extraction accuracy: receipts/*.png vs receipts/labels.json, per model (OpenAI-standard endpoint via app.llm)."""
import asyncio
import base64
import difflib
import json
import os
import re
import sys
from pathlib import Path

from app import llm, tools

MODELS = sys.argv[1:] or [llm.MODEL]
DIR = Path(__file__).with_name(os.environ.get("EVAL_DIR", "receipts"))
LABELS = json.loads((DIR / "labels.json").read_text(encoding="utf-8"))
CATS = ["อาหาร", "เดินทาง", "ที่พัก", "อุปกรณ์", "สุขภาพ", "ของใช้"]
PROMPT = f"""สกัดข้อมูลจากใบเสร็จในรูป ตอบเป็น JSON อย่างเดียว ห้ามมีข้อความอื่น:
{{"vendor": "ชื่อร้าน/บริษัท", "date_raw": "วันที่ตามที่พิมพ์ในบิล คัดลอกตัวอักษรตรงตามรูป ห้ามแปลงปีเอง ระบบแปลงให้ (เช่น 14/07/69, 09/06/2569, 3 Aug 2026)", "total": ยอดสุทธิที่จ่ายเป็นตัวเลข, "vat": ภาษีมูลค่าเพิ่มเป็นตัวเลข (0 ถ้าไม่มี), "category": หนึ่งใน {CATS}}}"""


def to_image(path):  # Gemma is image-only: rasterize PDFs (first page) via poppler
    if path.suffix.lower() == ".pdf":
        import subprocess, tempfile
        out = Path(tempfile.gettempdir()) / f"eval_{path.stem}"
        subprocess.run(["pdftoppm", "-png", "-r", "120", "-f", "1", "-l", "1", str(path), str(out)], check=True, capture_output=True)
        pngs = sorted(Path(tempfile.gettempdir()).glob(f"eval_{path.stem}*.png"))
        return pngs[0].read_bytes(), "image/png"
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return path.read_bytes(), mime


async def extract(model, path):
    data, mime = to_image(path)
    part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
    try:
        text = await llm.generate([{"role": "user", "parts": [part, {"text": PROMPT}]}], model=model)
    except llm.LLMError as e:
        return {"_raw": f"http {e}"}  # an outage, not a model mistake (RETRY_FAILED re-asks these)
    m = re.search(r"\{.*\}", text, re.S)
    try:
        pred = json.loads(m.group(0)) if m else {"_raw": text}
    except json.JSONDecodeError:
        return {"_raw": text}
    if "date_raw" in pred:  # same as the app: the model copies the date, code converts the year
        pred["date"] = tools.thai_date(pred["date_raw"]) or pred.get("date")
    return pred


def norm(s):
    return re.sub(r"[\s\-_.,()/]+", "", str(s or "")).lower()


def num(x):
    try:
        return float(str(x).replace(",", "").replace("฿", "").replace("บาท", ""))
    except ValueError:
        return None


def score(pred, gold):
    v = norm(pred.get("vendor")); g = norm(gold["vendor"])
    vendor_ok = bool(v) and (v in g or g in v or difflib.SequenceMatcher(None, v, g).ratio() >= 0.6)
    t, vt = num(pred.get("total")), num(pred.get("vat"))
    return {
        "vendor": vendor_ok,
        "date": str(pred.get("date", "")).strip() == gold["date"],
        "total": t is not None and abs(t - gold["total"]) < 0.01,
        "vat": vt is not None and abs(vt - gold["vat"]) < 0.01,
        "category": str(pred.get("category", "")).strip() == gold["category"],
    }


async def run_model(model):
    sem = asyncio.Semaphore(3)
    # RETRY_FAILED=1: keep the saved answers, re-ask only rows that died on an API error (http 5xx/timeout) —
    # an outage is not a model mistake and must not be scored as one
    prev = {}
    if os.environ.get("RETRY_FAILED") and (DIR / "eval_results.json").exists():
        prev = {r["file"]: r for r in json.loads((DIR / "eval_results.json").read_text(encoding="utf-8")).get(model, [])
                if not str(r["pred"].get("_raw", "")).startswith(("http", "timeout", "gave up"))}
    async def one(lab):
        if lab["file"] in prev:
            return prev[lab["file"]]
        async with sem:
            pred = await extract(model, DIR / lab["file"])
            return {"file": lab["file"], "pred": pred, "ok": score(pred, lab)}
    return await asyncio.gather(*(one(l) for l in LABELS))


async def main():
    results = {}
    for model in MODELS:
        print(f"\n== {model} ==", flush=True)
        rows = await run_model(model)
        results[model] = rows
        fields = list(rows[0]["ok"])
        print(f"{'file':32}" + "".join(f"{f:>9}" for f in fields))
        for r in rows:
            print(f"{r['file']:32}" + "".join(f"{'✓' if r['ok'][f] else '✗':>9}" for f in fields))
        print(f"{'ACCURACY':32}" + "".join(f"{sum(r['ok'][f] for r in rows) / len(rows):>8.0%} " for f in fields)
              + f"   all-5-correct: {sum(all(r['ok'].values()) for r in rows)}/{len(rows)}")
    (DIR / "eval_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
