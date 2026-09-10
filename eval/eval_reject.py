"""Non-receipt rejection: the production extraction prompt must answer doc_type="other" for images that are not
receipts/slips (professor's metric: "ความสามารถในการปฏิเสธภาพที่ไม่ใช่ใบเสร็จ").
Generates 12 synthetic non-receipts (no personal data) into eval/non_receipts/ the first time, then scores them.
Run inside the container:  python -m eval.eval_reject
"""
import asyncio
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app import llm, tools

DIR = Path(__file__).with_name("non_receipts")
FONT = "/usr/share/fonts/truetype/tlwg/Laksaman.ttf"


def _font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def make_images():
    DIR.mkdir(exist_ok=True)
    rng = random.Random(11)
    kinds = []
    for i in range(12):
        im = Image.new("RGB", (600, 800), (rng.randint(200, 255), rng.randint(200, 255), rng.randint(200, 255)))
        d = ImageDraw.Draw(im)
        k = i % 6
        if k == 0:    # landscape photo-ish: sky + hills
            d.rectangle([0, 0, 600, 400], fill=(120, 170, 230)); d.polygon([(0, 800), (200, 350), (400, 800)], fill=(60, 120, 60))
            d.polygon([(250, 800), (480, 420), (600, 800)], fill=(80, 140, 70)); kind = "landscape"
        elif k == 1:  # chat screenshot
            for j in range(8):
                x = 40 if j % 2 else 260; d.rounded_rectangle([x, 60 + j * 85, x + 300, 120 + j * 85], 18, fill=(180, 230, 180) if j % 2 else (230, 230, 230))
                d.text((x + 16, 78 + j * 85), rng.choice(["เดี๋ยวเจอกัน", "โอเคครับ", "กี่โมงดี", "ok see you"]), font=_font(22), fill="black")
            kind = "chat"
        elif k == 2:  # bar chart
            d.text((40, 40), "ยอดขายรายเดือน", font=_font(30), fill="black")
            for j in range(6):
                h = rng.randint(80, 500); d.rectangle([60 + j * 85, 700 - h, 120 + j * 85, 700], fill=(70, 100, 200))
            kind = "chart"
        elif k == 3:  # poster / announcement
            d.rectangle([40, 40, 560, 760], outline="black", width=6)
            d.text((80, 120), "ประกาศ", font=_font(60), fill="red"); d.text((80, 220), "งดจ่ายน้ำ วันเสาร์นี้\n09:00-15:00", font=_font(36), fill="black")
            kind = "poster"
        elif k == 4:  # id-card-like layout but fake (no real data) -> should still be "other"
            d.rounded_rectangle([60, 250, 540, 550], 20, fill=(240, 240, 250), outline="gray", width=3)
            d.rectangle([90, 290, 220, 460], fill=(200, 200, 210)); d.text((250, 300), "บัตรสมาชิกฟิตเนส\nMEMBER 0000", font=_font(28), fill="black")
            kind = "card"
        else:         # handwritten-ish note (not a receipt)
            for j in range(9):
                d.text((60, 80 + j * 75), rng.choice(["ซื้อนม", "โทรหาแม่", "ประชุม 10 โมง", "อ่านหนังสือ", "วิ่ง 5 กม"]), font=_font(34), fill=(30, 30, 90))
            kind = "note"
        im = im.rotate(rng.uniform(-3, 3), fillcolor="white")
        im.save(DIR / f"{i + 1:02d}_{kind}.png"); kinds.append(f"{i + 1:02d}_{kind}.png")
    return kinds


async def main():
    files = sorted(p.name for p in DIR.glob("*.png")) if DIR.exists() and any(DIR.glob("*.png")) else make_images()
    prompt = tools._extract_prompt(tools.CATS_DEFAULT)
    sem = asyncio.Semaphore(3)

    async def one(name):
        async with sem:
            raw = await llm.generate([{"role": "user", "parts": [llm.image_part(DIR / name), {"text": prompt}]}])
            d = tools._extract_json(raw)
            d = d[0] if isinstance(d, list) else d
            return name, d.get("doc_type"), d.get("total")
    rows = await asyncio.gather(*(one(n) for n in files))
    ok = sum(1 for _, dt, _ in rows if dt == "other")
    for name, dt, total in rows:
        print(f"{'✓' if dt == 'other' else '✗'} {name:20} doc_type={dt!r} total={total!r}")
    print(f"REJECTED {ok}/{len(rows)} non-receipts (doc_type=other)")
    Path("/data/logs/eval_reject.json").write_text(json.dumps({"rejected": ok, "n": len(rows), "rows": rows}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
