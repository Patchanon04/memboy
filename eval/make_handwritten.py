"""Handwritten cash-bill test set (the professor's "separate hard set") — synthetic, no real data.

Thai "บิลเงินสด" pads are pre-printed forms filled in by hand. We render the printed form with a normal font and the
filled-in parts glyph-by-glyph with per-character jitter (offset, rotation, size, ink weight, baseline wobble) on
cream paper with rules, shadow and JPEG grain. Labels are exact because we generate the numbers ourselves.

    python eval/make_handwritten.py            -> eval/handwritten/ + labels.json   (30 bills, seed 99)
Then inside the container:  EVAL_DIR=handwritten python -m eval.eval_receipts gemma-4-26b-a4b-it
"""
import json
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).with_name(os.environ.get("DATASET_OUT", "handwritten"))
OUT.mkdir(exist_ok=True)
rng = random.Random(int(os.environ.get("DATASET_SEED", "99")))
N = int(os.environ.get("DATASET_N", "30"))
FONT_PRINT = next(f for f in ["C:/Windows/Fonts/LeelawUI.ttf", "/usr/share/fonts/truetype/tlwg/Garuda.ttf"] if Path(f).exists())
FONT_HAND = next(f for f in ["C:/Windows/Fonts/leelawad.ttf", "C:/Windows/Fonts/LeelawUI.ttf", "/usr/share/fonts/truetype/tlwg/Laksaman.ttf"] if Path(f).exists())

SHOPS = [("ร้านป้าแดง ขายของชำ", "ของใช้"), ("ครัวลุงหนวด", "อาหาร"), ("ร้านน้ำแข็งสมชาย", "อาหาร"), ("อู่ช่างเบิร์ด", "เดินทาง"),
         ("ร้านวัสดุก่อสร้างรุ่งเรือง", "อุปกรณ์"), ("ร้านยาเภสัชกรนิด", "สุขภาพ"), ("บ้านพักริมน้ำ", "ที่พัก"), ("ตลาดสดโพธิ์ศรี แผง 12", "อาหาร"),
         ("ร้านเครื่องเขียนน้องบี", "อุปกรณ์"), ("แท็กซี่ป้ายเหลือง", "เดินทาง"), ("ร้านซ่อมมือถือเอก", "อุปกรณ์"), ("คลินิกหมอฟันยิ้มสวย", "สุขภาพ")]
ITEMS = {"ของใช้": [("น้ำยาล้างจาน", 45), ("ผงซักฟอก", 89), ("ถุงขยะ", 35), ("กระดาษทิชชู", 59), ("แชมพู", 120)],
         "อาหาร": [("ข้าวผัด", 50), ("น้ำเปล่า", 10), ("ก๋วยเตี๋ยว", 45), ("หมูปิ้ง", 40), ("น้ำแข็ง 1 ถุง", 20), ("ผักรวม", 60), ("ไข่ไก่ 1 แผง", 130)],
         "เดินทาง": [("ค่าโดยสาร", 120), ("เปลี่ยนน้ำมันเครื่อง", 650), ("ปะยาง", 150), ("ค่าจอดรถ", 40)],
         "อุปกรณ์": [("ปูน 1 ถุง", 135), ("ตะปู 1 กก.", 60), ("สายไฟ 10 ม.", 250), ("ปากกา 1 โหล", 96), ("แฟ้ม", 45), ("เปลี่ยนจอ", 1200)],
         "สุขภาพ": [("ยาแก้ปวด", 60), ("วิตามินซี", 250), ("อุดฟัน", 800), ("ขูดหินปูน", 900)],
         "ที่พัก": [("ห้องพัก 1 คืน", 800), ("ห้องพัก 2 คืน", 1600), ("อาหารเช้า", 150)]}
TH_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def hand(draw, im, xy, text, size, ink, wobble=1.0):
    """Handwriting: each glyph drawn on its own tile, jittered, rotated, pasted."""
    x, y = xy
    # keep a base letter together with its combining vowels/tone marks, or "บ้าน" turns into "บ าน"
    marks = set("ัิีึืฺุู็่้๊๋์ํ๎")
    clusters = []
    for ch in text:
        if ch in marks and clusters:
            clusters[-1] += ch
        else:
            clusters.append(ch)
    for ch in clusters:
        if ch == " ":
            x += size * 0.35 * rng.uniform(0.8, 1.5)
            continue
        sz = int(size * rng.uniform(0.9, 1.12))
        f = ImageFont.truetype(FONT_HAND, sz)
        w, h = f.getbbox(ch)[2] + 6, sz * 2
        tile = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        col = tuple(min(255, c + rng.randint(-25, 25)) for c in ink) + (rng.randint(200, 255),)
        for dx in range(rng.choice([1, 1, 2])):  # ink weight
            td.text((4 + dx, 4), ch, font=f, fill=col)
        tile = tile.rotate(rng.uniform(-7, 7), resample=Image.BICUBIC, expand=False)
        im.paste(tile, (int(x + rng.uniform(-1.5, 1.5)), int(y + rng.uniform(-2.5, 2.5) * wobble)), tile)
        x += (w - 6) * rng.uniform(0.85, 1.05) + rng.uniform(-1, 3)
    return x


def build_one(i: int) -> dict:
    shop, cat = rng.choice(SHOPS)
    W, H = 900, 1200
    paper = tuple(rng.randint(228, 250) for _ in range(3))
    im = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(im)
    fp = ImageFont.truetype(FONT_PRINT, 30); fps = ImageFont.truetype(FONT_PRINT, 22)
    # pre-printed form
    d.text((W // 2 - 90, 40), "บิลเงินสด", font=ImageFont.truetype(FONT_PRINT, 44), fill=(60, 60, 120))
    d.text((60, 110), "ร้าน", font=fp, fill=(90, 90, 140)); d.line([(130, 145), (620, 145)], fill=(150, 150, 190), width=1)
    d.text((640, 110), "วันที่", font=fp, fill=(90, 90, 140)); d.line([(720, 145), (860, 145)], fill=(150, 150, 190), width=1)
    d.text((60, 170), "เลขที่", font=fps, fill=(120, 120, 160))
    top = 230
    for col, label in ((60, "ลำดับ"), (150, "รายการ"), (560, "จำนวน"), (680, "ราคา"), (790, "รวม")):
        d.text((col, top), label, font=fps, fill=(90, 90, 140))
    for r in range(9):
        d.line([(50, top + 40 + r * 62), (860, top + 40 + r * 62)], fill=(170, 170, 205), width=1)
    for xx in (50, 140, 550, 670, 780, 860):
        d.line([(xx, top), (xx, top + 40 + 8 * 62)], fill=(170, 170, 205), width=1)
    d.text((560, top + 40 + 8 * 62 + 14), "รวมเงิน", font=fp, fill=(90, 90, 140))
    d.text((60, 1080), "ผู้รับเงิน ______________", font=fps, fill=(120, 120, 160))
    # handwritten fill
    ink = rng.choice([(20, 20, 90), (15, 15, 15), (30, 30, 130), (40, 20, 20)])
    hand(d, im, (140, 100), shop, 34, ink)
    day, month = rng.randint(1, 28), rng.randint(1, 12)
    date_style = rng.choice(["be_short", "be_short", "th_abbr", "ce_full", "be_full"])
    date_txt = {"be_short": f"{day}/{month}/69", "th_abbr": f"{day} {TH_MONTHS[month - 1]} 69",
                "ce_full": f"{day}/{month}/2026", "be_full": f"{day}/{month}/2569"}[date_style]
    hand(d, im, (722, 100), date_txt, 30, ink)
    hand(d, im, (150, 165), str(rng.randint(100, 9999)), 26, ink)
    items = rng.sample(ITEMS[cat], k=min(len(ITEMS[cat]), rng.randint(2, 5)))
    subtotal = 0
    for r, (name, price) in enumerate(items):
        qty = rng.choice([1, 1, 1, 2, 3])
        line = price * qty
        subtotal += line
        y = top + 48 + r * 62
        hand(d, im, (75, y), str(r + 1), 28, ink)
        hand(d, im, (155, y), name, 30, ink)
        hand(d, im, (585, y), str(qty), 28, ink)
        hand(d, im, (690, y), f"{price:,}", 28, ink)
        hand(d, im, (795, y), f"{line:,}", 28, ink)
    vat = 0.0
    total = float(subtotal)
    if rng.random() < 0.25:  # some shops add VAT by hand
        vat = round(subtotal * 0.07, 2); total = round(subtotal + vat, 2)
        hand(d, im, (560, top + 40 + 7 * 62 + 8), f"VAT 7% {vat:,.2f}", 26, ink)
    tot_txt = f"{total:,.2f}" if total != int(total) else f"{int(total):,}"
    tx = hand(d, im, (700, top + 40 + 8 * 62 + 12), tot_txt + " บาท", 34, ink)
    if rng.random() < 0.5:  # circled total
        d.ellipse([690, top + 40 + 8 * 62 + 2, tx + 12, top + 40 + 8 * 62 + 60], outline=ink, width=2)
    if rng.random() < 0.4:  # a stamp
        d.rectangle([600, 1000, 850, 1090], outline=(180, 40, 40), width=3)
        d.text((615, 1020), "ชำระแล้ว / PAID", font=fp, fill=(190, 50, 50))
    # camera-like degradation: rotation, shadow, blur, jpeg grain
    im = im.rotate(rng.uniform(-4, 4), resample=Image.BICUBIC, expand=True, fillcolor=(120, 110, 100))
    shade = Image.new("L", im.size, 0); ImageDraw.Draw(shade).rectangle([0, 0, im.width, im.height], fill=0)
    sd = ImageDraw.Draw(shade)
    for k in range(im.width):
        sd.line([(k, 0), (k, im.height)], fill=int(40 * k / im.width))
    im = Image.composite(Image.new("RGB", im.size, (60, 50, 40)), im, shade.point(lambda v: min(255, v)))
    if rng.random() < 0.6:
        im = im.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.2)))
    name = f"{i:03d}_th_handwritten.jpg"
    im.convert("RGB").save(OUT / name, quality=rng.randint(45, 80))
    return {"file": name, "vendor": shop, "date": f"2026-{month:02d}-{day:02d}", "total": total, "vat": vat, "category": cat,
            "lang": "th", "difficulty": "handwritten", "date_style": date_style, "items": len(items)}


labels = [build_one(i) for i in range(1, N + 1)]
(OUT / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(labels)} handwritten bills -> {OUT}")
