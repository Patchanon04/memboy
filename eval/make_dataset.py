"""200-file mixed eval dataset: TH/EN receipts, PNG/JPG/PDF, clean/photo/camera-sim.
Reuses the render engine from make_receipts and camera effects from make_hard
(importing them regenerates those two small sets as a benign, deterministic side effect).
Output: dataset/ + dataset/labels.json (ground truth auto — no manual labeling)."""
import json
import random
from pathlib import Path

import make_receipts as R   # render, photo_effect, money, vat_split, items_block
import make_hard as H       # perspective, crumple, cheap_camera, ... EFFECTS

import os
OUT = Path(__file__).with_name(os.environ.get("DATASET_OUT", "dataset"))  # dataset = prompt-tuning set, dataset_test = held-out
OUT.mkdir(exist_ok=True)
rng = random.Random(int(os.environ.get("DATASET_SEED", "2026")))

# ---------- content pools ----------
TH = {
    "อาหาร": (["ครัวป้าแดง", "ก๋วยเตี๋ยวเรือรุ่งเรือง", "ส้มตำนัวเด้อ", "กาแฟบ้านสวน", "ชาบูอิ่มบุฟเฟ่ต์", "ข้าวแกงใต้ถุนตึก", "โจ๊กกองปราบ", "หมูทอดเจ๊จู"],
               [("ข้าวผัดกะเพรา", 60), ("ก๋วยเตี๋ยวน้ำตก", 55), ("ส้มตำไทย", 50), ("ลาเต้เย็น", 65), ("ชานมไข่มุก", 45), ("ข้าวมันไก่", 50), ("หมูปิ้ง", 10), ("น้ำเปล่า", 10), ("โค้ก", 20), ("ข้าวเหนียว", 10)]),
    "เดินทาง": (["วินมอเตอร์ไซค์ปากซอย", "แท็กซี่มิเตอร์", "รถตู้สายอนุสาวรีย์", "ปั๊มบางจาก สาขาร่มเกล้า", "เรือด่วนเจ้าพระยา"],
                 [("ค่าโดยสาร", 60), ("ค่าน้ำมันดีเซล", 800), ("ค่าทางด่วน", 50), ("ตั๋วรายเดือน", 1200)]),
    "อุปกรณ์": (["ร้านเครื่องเขียนศึกษาภัณฑ์", "ไอทีซิตี้ สาขาแฟชั่น", "ร้านถ่ายเอกสารหน้ามอ", "ห้างหุ้นส่วน อะไหล่รุ่งเจริญ"],
                 [("ปากกาลูกลื่น", 15), ("สมุดโน้ต A5", 35), ("ถ่ายเอกสาร (แผ่น)", 1), ("เมาส์ไร้สาย", 390), ("สาย USB-C", 120), ("แฟ้มเอกสาร", 45)]),
    "ของใช้": (["มินิมาร์ทป้าอ้วน", "ตลาดสดคลองเตย แผง 12", "ร้านยี่สิบบาทของแท้", "ซุปเปอร์ชุมชนวัดใต้"],
                [("ผงซักฟอก", 55), ("สบู่ก้อน", 25), ("ยาสีฟัน", 45), ("กระดาษทิชชู่", 40), ("น้ำยาล้างจาน", 35), ("ไม้แขวนเสื้อ (แพ็ค)", 29)]),
    "สุขภาพ": (["คลินิกหมอสมศรี", "ร้านยาฟาร์มาซีพลัส", "สปาเท้าผ่อนคลาย"],
                [("ค่าตรวจรักษา", 300), ("ยาแก้แพ้", 60), ("วิตามินซี", 120), ("นวดเท้า 1 ชม.", 250)]),
}
EN = {
    "อาหาร": (["Daily Grind Coffee", "Burger Barn", "Noodle House 88", "Green Bowl Salads", "Pizza Piazza"],
               [("Americano", 70), ("Cheeseburger set", 189), ("Ramen bowl", 220), ("Caesar salad", 150), ("Margherita 12\"", 259), ("Sparkling water", 45)]),
    "เดินทาง": (["City Cab Co., Ltd.", "Metro Fuel Station", "Airport Rail Link"],
                 [("Taxi fare", 180), ("Gasohol 95", 1000), ("Airport express ticket", 150)]),
    "อุปกรณ์": (["TechHub Gadget Store", "Office Supply Depot", "PrintPro Center"],
                 [("Wireless keyboard", 890), ("A4 paper ream", 115), ("Ink cartridge", 650), ("HDMI cable 2m", 190), ("Laptop stand", 450)]),
    "ที่พัก": (["Sunrise Beach Resort", "City Center Hotel", "Cozy Hostel Bangkok"],
                [("Deluxe room / night", 1850), ("Standard room / night", 1200), ("Dorm bed / night", 450), ("Breakfast", 250)]),
}
PAY = ["เงินสด", "PromptPay", "บัตรเครดิต VISA ****{:04d}", "QR Payment", "Cash", "TrueMoney Wallet"]


def th_date(d, m, y, style):
    if style == "be_short":
        return f"{d}/{m}/{str(y + 543)[-2:]}"
    if style == "be_full":
        return f"{d:02d}/{m:02d}/{y + 543}"
    if style == "ce_short":
        return f"{d:02d}/{m:02d}/{str(y)[-2:]}"
    if style == "en":
        return f"{d} {['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m]} {y}"
    return f"{d:02d}/{m:02d}/{y}"


def build_one(i):
    lang = "th" if rng.random() < 0.6 else "en"
    pool = TH if lang == "th" else EN
    cat = rng.choice(list(pool))
    vendors, items = pool[cat]
    vendor = rng.choice(vendors)
    picks = rng.sample(items, rng.randint(2, min(6, len(items))))
    picks = [(n, rng.randint(1, 3), p) for n, p in picks]
    total = sum(q * p for _, q, p in picks)
    has_vat = rng.random() < 0.55
    d, m, y = rng.randint(1, 28), rng.randint(1, 12), 2026
    style = rng.choice(["be_short", "be_full", "ce_short", "ce_full", "en"] if lang == "th" else ["en", "ce_full"])
    date_txt = th_date(d, m, y, style)
    fnt = rng.choice(["tahoma", "leela", "cordia", "browa"] if lang == "th" else ["tahoma", "leela", "consola"])
    big = {"tahoma": 0, "leela": 0, "cordia": 6, "browa": 6, "consola": 0}[fnt]
    fb = fnt + ("b" if fnt in ("tahoma", "leela") else "")
    sz = 13 + big

    rows = [(vendor, "c", fb, 20 + big)]
    if rng.random() < 0.5:
        rows.append((f"TAX ID {rng.randint(10**12, 10**13 - 1)}", "c", fnt, sz - 2))
    if has_vat:
        rows.append(("ใบกำกับภาษีอย่างย่อ" if lang == "th" else "ABB. TAX INVOICE", "c", fnt, sz - 2))
    rows += [("--",), ("2col", date_txt + f" {rng.randint(8, 21):02d}:{rng.randint(0, 59):02d}", f"No.{rng.randint(1, 9999):04d}", fnt, sz - 1), ("--",)]
    rows += R.items_block(picks, fnt, sz)
    rows.append(("--",))
    if has_vat:
        b, v = R.vat_split(total)
        rows += [("2col", "ก่อน VAT" if lang == "th" else "Subtotal", R.money(b), fnt, sz - 1),
                 ("2col", "VAT 7%", R.money(v), fnt, sz - 1)]
    else:
        v = 0.0
        if rng.random() < 0.4:
            rows.append(("ไม่รวม VAT" if lang == "th" else "VAT not registered", "c", fnt, sz - 2))
    rows.append(("2col", "รวมทั้งสิ้น" if lang == "th" else "TOTAL", R.money(total), fb, sz + 3))
    pay = rng.choice(PAY)
    rows.append((pay.format(rng.randint(0, 9999)) if "{" in pay else pay, "c" if rng.random() < 0.5 else "l", fnt, sz - 2))

    im = R.render(rows, width=rng.choice([320, 360, 420]), bg=rng.choice([(255, 255, 255), (252, 250, 243), (248, 248, 250)]))

    difficulty = rng.choice(["clean", "photo", "camera"])
    if difficulty == "clean":
        im = R.photo_effect(im, rot=rng.uniform(-1.5, 1.5))
    elif difficulty == "photo":
        im = R.photo_effect(im, rot=rng.uniform(-5, 5), blur=rng.uniform(0, 0.7), noise=rng.uniform(0, 0.015),
                            fade=rng.uniform(0, 0.35), shadow=rng.random() < 0.5)
    else:  # camera: full hard pipeline
        im = R.photo_effect(im, rot=rng.uniform(-6, 6), fade=rng.uniform(0, 0.25))
        h_rng = random.Random(i)
        for fx in h_rng.sample(H.EFFECTS, h_rng.randint(2, 4)):
            im = fx(im, h_rng)

    ext = rng.choices(["png", "jpg", "pdf"], weights=[0.35, 0.45, 0.20])[0]
    name = f"{i:03d}_{lang}_{difficulty}.{ext}"
    if ext == "pdf":
        im.save(OUT / name, "PDF", resolution=100)
    else:
        im.save(OUT / name, quality=rng.randint(70, 92) if ext == "jpg" else None)
    return {"file": name, "vendor": vendor, "date": f"{y}-{m:02d}-{d:02d}", "total": float(total),
            "vat": v, "category": cat, "lang": lang, "difficulty": difficulty, "date_style": style}


labels = [build_one(i) for i in range(1, int(os.environ.get("DATASET_N", "200")) + 1)]
(OUT / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
for k in ("lang", "difficulty", "date_style"):
    print(k, dict(Counter(l[k] for l in labels)))
print("ext", dict(Counter(l["file"].rsplit(".", 1)[1] for l in labels)))
print(f"{len(labels)} files -> {OUT}")
