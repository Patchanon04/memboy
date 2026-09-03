"""Synthetic bank-transfer slips (fictitious banks/names/accounts) with mini-QR (ref|amount) — 6 layouts x 5 = 30.
Every 6th slip gets a deliberately MISMATCHED QR to test consistency verification."""
import json, random
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont
OUT = Path("eval/slips"); OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(7)
F = lambda n, s: ImageFont.truetype(f"C:/Windows/Fonts/{n}", s)
BANKS = [("ธนาคารกรุงศรีนคร", (0, 120, 80)), ("Siam Metro Bank", (30, 60, 150)), ("ธนาคารไทยพัฒนา", (130, 40, 120)),
         ("Bangkok Trust Bank", (200, 80, 0)), ("ธนาคารรวงข้าว", (0, 100, 170)), ("PromptPay สมมติ", (0, 150, 130))]
NAMES = ["นายสมหมาย ใจดี", "น.ส.ปาริชาต สุขใจ", "MR. ARUN TESTER", "นางสาวจริยา แซ่ตั้ง", "บจก. ร้านสมมติ จำกัด", "MS. NIDA SAMPLE"]
labels = []
for i in range(30):
    bank, col = BANKS[i % 6]; layout = i % 6
    amt = round(rng.uniform(50, 5000), 2); ref = f"{rng.randint(10**9, 10**10-1)}{rng.choice('ABCDEF')}"
    d, m = rng.randint(1, 28), rng.randint(1, 12); date = f"2026-{m:02d}-{d:02d}"
    payer, payee = rng.sample(NAMES, 2); mismatch = (i % 6 == 5)
    qr_payload = f"{ref if not mismatch else 'X'+ref[1:]}|{amt:.2f}"
    qr = qrcode.make(qr_payload).resize((150, 150))
    W, H = (420, 640) if layout != 3 else (480, 680)  # layout 3 was cropping the QR off the bottom
    im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 90], fill=col); dr.text((20, 28), bank, font=F("tahomabd.ttf", 24), fill="white")
    y = 120; f = F("tahoma.ttf", 16); fb = F("tahomabd.ttf", 18)
    dr.text((W // 2, y), "โอนเงินสำเร็จ" if layout % 2 == 0 else "Transfer Successful", font=fb, fill=(40, 40, 40), anchor="mm"); y += 40
    dr.text((W // 2, y), f"{d:02d}/{m:02d}/{2026 + (543 if layout in (0, 2) else 0)}  {rng.randint(8,22):02d}:{rng.randint(0,59):02d}", font=f, fill="gray", anchor="mm"); y += 50
    for k, v in (("จาก" if layout % 2 == 0 else "From", payer), ("ไปยัง" if layout % 2 == 0 else "To", payee),
                 ("บัญชี" if layout % 2 == 0 else "Account", f"xxx-x-x{rng.randint(1000,9999)}-x"),
                 ("จำนวนเงิน" if layout % 2 == 0 else "Amount", f"{amt:,.2f} THB"), ("ค่าธรรมเนียม" if layout % 2 == 0 else "Fee", "0.00 THB"),
                 ("เลขที่อ้างอิง" if layout % 2 == 0 else "Ref No.", ref)):
        dr.text((30, y), k, font=f, fill="gray"); dr.text((W - 30, y), v, font=fb if "เงิน" in k or "Amount" in k else f, fill="black", anchor="ra"); y += 42
    im.paste(qr, (W // 2 - 75, y + 10)); dr.text((W // 2, y + 175), "QR สำหรับตรวจสอบ", font=F("tahoma.ttf", 12), fill="gray", anchor="mm")
    name = f"slip_{i+1:02d}_L{layout}{'_MISMATCH' if mismatch else ''}.png"; im.save(OUT / name)
    labels.append({"file": name, "vendor": payee, "date": date, "total": amt, "vat": 0.0, "category": "โอนเงิน", "transfer_ref": ref,
                   "qr_expected": "mismatch" if mismatch else "verified", "layout": layout})
(OUT / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(labels), "slips ->", OUT)
