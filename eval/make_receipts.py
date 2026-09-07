"""Generate 20 varied fake Thai receipts + ground-truth labels (for extraction eval)."""
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

random.seed(42)
OUT = Path(__file__).with_name("receipts")
OUT.mkdir(exist_ok=True)
F = "C:/Windows/Fonts/"
FONTS = {"tahoma": F + "tahoma.ttf", "tahomab": F + "tahomabd.ttf", "leela": F + "LeelawUI.ttf", "leelab": F + "LeelaUIb.ttf",
         "angsana": F + "angsana.ttc", "browa": F + "browalia.ttc", "cordia": F + "cordia.ttc", "cour": F + "cour.ttf", "consola": F + "consola.ttf"}


def font(name, size):
    return ImageFont.truetype(FONTS[name], size)


def money(x):
    return f"{x:,.2f}"


# ---------- layout engine: list of rows -> image ----------
# row = (text, align, fontname, size) | ("--",) divider | ("", ) blank | ("2col", left, right, fontname, size)
def render(rows, width=380, pad=20, bg=(255, 255, 255), ink=(0, 0, 0), line_gap=6):
    H = 4000
    im = Image.new("RGB", (width, H), bg)
    d = ImageDraw.Draw(im)
    y = pad
    for r in rows:
        if r[0] == "--":
            d.line([(pad, y + 6), (width - pad, y + 6)], fill=ink, width=1)
            y += 16
            continue
        if r[0] == "":
            y += r[1] if len(r) > 1 else 12
            continue
        if r[0] == "2col":
            _, l, rt, fn, sz = r
            f = font(fn, sz)
            d.text((pad, y), l, fill=ink, font=f)
            w = d.textlength(rt, font=f)
            d.text((width - pad - w, y), rt, fill=ink, font=f)
            y += sz + line_gap
            continue
        text, align, fn, sz = r
        f = font(fn, sz)
        w = d.textlength(text, font=f)
        x = pad if align == "l" else (width - w) / 2 if align == "c" else width - pad - w
        d.text((x, y), text, fill=ink, font=f)
        y += sz + line_gap
    return im.crop((0, 0, width, y + pad))


def photo_effect(im, rot=0, blur=0, noise=0, fade=0, skew=0, shadow=False, paper=(255, 255, 255)):
    """Make it look like a phone photo: rotation, blur, noise, faded ink, paper tint."""
    if fade:
        im = Image.blend(im, Image.new("RGB", im.size, paper), fade)
    if skew:
        w, h = im.size
        im = im.transform((w + abs(skew), h), Image.AFFINE, (1, skew / h, -skew if skew > 0 else 0, 0, 1, 0), fillcolor=paper)
    if shadow:
        g = Image.linear_gradient("L").resize(im.size).rotate(random.choice([0, 90, 180]), expand=False)
        im = Image.composite(im, Image.new("RGB", im.size, (170, 170, 160)), g.point(lambda p: 255 - p // 4))
    bgc = tuple(random.choice([(120, 110, 100), (60, 60, 65), (200, 195, 185), (150, 140, 130)]))
    m = 40
    canvas = Image.new("RGB", (im.width + m * 2, im.height + m * 2), bgc)
    canvas.paste(im, (m, m))
    im = canvas.rotate(rot, expand=True, fillcolor=bgc, resample=Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if noise:
        px = im.load()
        for _ in range(int(im.width * im.height * noise)):
            x, y = random.randrange(im.width), random.randrange(im.height)
            v = random.randint(-40, 40)
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + v)), max(0, min(255, g + v)), max(0, min(255, b + v)))
    return im


def items_block(items, fn, sz, qty=True):
    rows = []
    for name, q, p in items:
        rows.append(("2col", f"{name}" + (f"  x{q}" if qty and q > 1 else ""), money(q * p), fn, sz))
    return rows


def vat_split(total, rate=0.07):
    base = round(total / (1 + rate), 2)
    return base, round(total - base, 2)


labels = []
receipts = []  # (filename, rows, style kwargs, effect kwargs, label)


def add(name, rows, label, style=None, fx=None):
    receipts.append((name, rows, style or {}, fx or {}, label))


# ---------- 1. 7-Eleven thermal ----------
it = [("เลย์รสโนริสาหร่าย 48g", 1, 20), ("น้ำดื่มคริสตัล 600ml", 2, 7), ("ไส้กรอกไก่ CP", 1, 25), ("โออิชิกรีนที 500ml", 1, 25)]
tot = sum(q * p for _, q, p in it); b, v = vat_split(tot)
add("01_7eleven.png", [("7-ELEVEN", "c", "tahomab", 22), ("บจก.ซีพี ออลล์ (มหาชน)", "c", "tahoma", 13), ("สาขา ลาดกระบัง 3 (07856)", "c", "tahoma", 13),
    ("เลขประจำตัวผู้เสียภาษี 0107542000011", "c", "tahoma", 12), ("ใบเสร็จรับเงิน/ใบกำกับภาษีอย่างย่อ", "c", "tahoma", 12), ("--",),
    ("2col", "23/08/26 14:32", "POS:2  R#0417", "tahoma", 13), ("--",), *items_block(it, "tahoma", 14), ("--",),
    ("2col", "รวม", money(tot), "tahomab", 15), ("2col", "เงินสด", "100.00", "tahoma", 14), ("2col", "เงินทอน", money(100 - tot), "tahoma", 14),
    ("2col", "มูลค่าสินค้า", money(b), "tahoma", 12), ("2col", "VAT 7%", money(v), "tahoma", 12), ("", 8), ("ขอบคุณที่ใช้บริการ", "c", "tahoma", 13), ("สะสมแต้ม ALL member 0812xxx567", "c", "tahoma", 12)],
    dict(vendor="7-Eleven สาขาลาดกระบัง 3", date="2026-08-23", total=tot, vat=v, category="อาหาร"), dict(width=340), dict(rot=-2, fade=0.25, noise=0.01, shadow=True))

# ---------- 2. Coffee shop ----------
it = [("Iced Latte (L)", 2, 75), ("Croissant", 1, 65), ("Matcha Latte", 1, 85)]
tot = sum(q * p for _, q, p in it); b, v = vat_split(tot)
add("02_coffee.png", [("Bean There Café", "c", "leelab", 24), ("123/4 ถ.ฉลองกรุง เขตลาดกระบัง กทม.", "c", "leela", 12), ("Tel 02-345-6789", "c", "leela", 12), ("--",),
    ("2col", "Order #A-1082", "Dine in", "leela", 13), ("2col", "22 Aug 2026", "09:41", "leela", 13), ("--",), *items_block(it, "leela", 15), ("--",),
    ("2col", "Subtotal", money(b), "leela", 13), ("2col", "VAT 7% (included)", money(v), "leela", 13), ("2col", "TOTAL", money(tot), "leelab", 18), ("", 6), ("PromptPay ✓", "c", "leela", 13), ("Thank you, see you again!", "c", "leela", 13)],
    dict(vendor="Bean There Café", date="2026-08-22", total=tot, vat=v, category="อาหาร"), dict(width=360, bg=(252, 250, 245)), dict(rot=3, blur=0.6, noise=0.005))

# ---------- 3. Full tax invoice (company) ----------
it = [("Monitor Dell 24\" P2422H", 2, 5900), ("USB-C Hub 7-in-1", 2, 1290), ("สาย HDMI 2.0 2m", 4, 190)]
b = sum(q * p for _, q, p in it); v = round(b * 0.07, 2); tot = b + v
add("03_tax_invoice.png", [("บริษัท เทคโนไอที โซลูชั่น จำกัด", "c", "tahomab", 20), ("99/9 อาคารเอ ชั้น 5 ถ.พระราม 9 ห้วยขวาง กรุงเทพฯ 10310", "c", "tahoma", 11),
    ("เลขประจำตัวผู้เสียภาษี 0105558123456 (สำนักงานใหญ่)", "c", "tahoma", 11), ("", 4), ("ใบกำกับภาษี / ใบเสร็จรับเงิน", "c", "tahomab", 16), ("TAX INVOICE / RECEIPT", "c", "tahoma", 12), ("--",),
    ("2col", "เลขที่ IV2608-0042", "วันที่ 15/08/2026", "tahoma", 12), ("ลูกค้า: บริษัท พีบุ๊ค เทคโนโลยี จำกัด", "l", "tahoma", 12), ("เลขผู้เสียภาษี 0105566789012", "l", "tahoma", 12), ("ที่อยู่: 1 ซ.ฉลองกรุง 1 ลาดกระบัง กทม. 10520", "l", "tahoma", 12), ("--",),
    ("2col", "รายการ                      จำนวน", "จำนวนเงิน", "tahomab", 12), *[("2col", f"{n}   x{q} @ {money(p)}", money(q * p), "tahoma", 12) for n, q, p in it], ("--",),
    ("2col", "รวมเงิน", money(b), "tahoma", 13), ("2col", "ภาษีมูลค่าเพิ่ม 7%", money(v), "tahoma", 13), ("2col", "จำนวนเงินรวมทั้งสิ้น", money(tot), "tahomab", 15),
    ("(หนึ่งหมื่นหกพันหนึ่งร้อยเก้าสิบเก้าบาทแปดสิบสตางค์)", "l", "tahoma", 11), ("", 10), ("2col", "ผู้รับเงิน ____________", "ผู้รับสินค้า ____________", "tahoma", 11)],
    dict(vendor="บริษัท เทคโนไอที โซลูชั่น จำกัด", date="2026-08-15", total=tot, vat=v, category="อุปกรณ์"), dict(width=560, pad=30), dict(rot=1, noise=0.003))

# ---------- 4. Thai restaurant (Angsana, big) ----------
it = [("ต้มยำกุ้ง", 1, 180), ("ผัดกะเพราหมูสับ", 2, 80), ("ข้าวสวย", 3, 15), ("น้ำเปล่า", 2, 20), ("ชาเย็น", 1, 45)]
tot = sum(q * p for _, q, p in it)
add("04_restaurant.png", [("ครัวคุณยาย", "c", "angsana", 40), ("อาหารตามสั่ง - ซีฟู้ด", "c", "angsana", 22), ("--",), ("2col", "โต๊ะ 7", "20/8/2569 19:25", "angsana", 22), ("--",),
    *items_block(it, "angsana", 24), ("--",), ("2col", "รวมทั้งสิ้น", f"{money(tot)} บาท", "angsana", 28), ("", 6), ("*ราคานี้ไม่รวม VAT / ไม่ออกใบกำกับภาษี", "c", "angsana", 18)],
    dict(vendor="ครัวคุณยาย", date="2026-08-20", total=tot, vat=0, category="อาหาร", note="พ.ศ. date"), dict(width=360, bg=(250, 247, 238)), dict(rot=-4, blur=0.8, fade=0.15, shadow=True))

# ---------- 5. Grab ride ----------
add("05_grab.png", [("Grab", "l", "tahomab", 28), ("ใบเสร็จการเดินทาง", "l", "tahoma", 14), ("--",), ("GrabCar · 19 ส.ค. 2026 08:12", "l", "tahoma", 13), ("", 4),
    ("● สถานีลาดกระบัง", "l", "tahoma", 13), ("○ สจล. อาคารเรียนรวม", "l", "tahoma", 13), ("", 8), ("2col", "ค่าโดยสาร", "89.00", "tahoma", 14), ("2col", "ค่าธรรมเนียมแพลตฟอร์ม", "5.00", "tahoma", 14), ("2col", "ส่วนลดโปรโมชั่น", "-10.00", "tahoma", 14), ("--",),
    ("2col", "ยอดรวม", "฿84.00", "tahomab", 18), ("ชำระด้วย GrabPay Wallet", "l", "tahoma", 12), ("รหัสการเดินทาง ADR-7Q2KX9", "l", "tahoma", 11)],
    dict(vendor="Grab", date="2026-08-19", total=84.0, vat=0, category="เดินทาง"), dict(width=380, bg=(255, 255, 255)), dict(rot=0))

# ---------- 6. Taxi handwritten bill ----------
add("06_taxi_handwritten.png", [("บิลเงินสด", "c", "browa", 30), ("--",), ("วันที่  18 / 8 / 69", "l", "browa", 24), ("จาก  สนามบินดอนเมือง", "l", "browa", 24), ("ถึง  ลาดกระบัง", "l", "browa", 24), ("", 10),
    ("ค่าแท็กซี่   350  บาท", "l", "browa", 26), ("ค่าทางด่วน   75  บาท", "l", "browa", 26), ("--",), ("รวม   425  บาท", "r", "browa", 30), ("", 20), ("ผู้รับเงิน  สมชาย", "r", "browa", 22), ("ทะเบียน 1กข 4567", "r", "browa", 20)],
    dict(vendor="แท็กซี่ (บิลเงินสด)", date="2026-08-18", total=425.0, vat=0, category="เดินทาง", note="handwritten-style, no VAT"), dict(width=380, bg=(245, 240, 225), ink=(30, 40, 120)), dict(rot=5, blur=0.5, noise=0.02, skew=15))

# ---------- 7. PTT fuel ----------
tot = 1200.00; b, v = vat_split(tot)
add("07_ptt_fuel.png", [("PTT Station", "c", "tahomab", 20), ("บจก. ปิโตรเลียมลาดกระบัง", "c", "tahoma", 12), ("TAX ID 0105540001234", "c", "tahoma", 12), ("ใบกำกับภาษีอย่างย่อ", "c", "tahoma", 12), ("--",),
    ("2col", "17/08/2026 07:55", "หัวจ่าย 04", "tahoma", 13), ("--",), ("2col", "แก๊สโซฮอล์ 95", "36.45 บ./ล.", "tahoma", 13), ("2col", "ปริมาณ", "32.92 ลิตร", "tahoma", 13), ("--",), ("2col", "รวมเงิน", money(tot), "tahomab", 16),
    ("2col", "ก่อน VAT", money(b), "tahoma", 12), ("2col", "VAT 7%", money(v), "tahoma", 12), ("บัตรเครดิต KBANK **** 4471", "l", "tahoma", 12), ("", 6), ("Blue Card: 0891234567  +12 pts", "c", "tahoma", 12)],
    dict(vendor="PTT Station ลาดกระบัง", date="2026-08-17", total=tot, vat=v, category="เดินทาง"), dict(width=340), dict(rot=-1, fade=0.4, noise=0.015))

# ---------- 8. Hotel folio ----------
room = 2 * 1850; svc = round(room * 0.10, 2); b = room + svc; v = round(b * 0.07, 2); tot = b + v
add("08_hotel.png", [("The Riverside Hotel Chiang Mai", "c", "leelab", 20), ("99 Charoenrat Rd., Chiang Mai 50000 | Tax ID 0505551000789", "c", "leela", 11), ("", 4), ("GUEST FOLIO / TAX INVOICE", "c", "leelab", 14), ("--",),
    ("2col", "Guest: Mr. Somchai Jaidee", "Room 1207", "leela", 12), ("2col", "Arrival 10 Aug 2026", "Departure 12 Aug 2026", "leela", 12), ("2col", "Folio No. F-230811", "Company: MemBoy Technology Co., Ltd.", "leela", 11), ("--",),
    ("2col", "10/08 Room Charge - Deluxe", "1,850.00", "leela", 12), ("2col", "11/08 Room Charge - Deluxe", "1,850.00", "leela", 12), ("2col", "Service Charge 10%", money(svc), "leela", 12), ("--",),
    ("2col", "Subtotal", money(b), "leela", 12), ("2col", "VAT 7%", money(v), "leela", 12), ("2col", "GRAND TOTAL (THB)", money(tot), "leelab", 16), ("2col", "Paid by VISA ****9921", "Balance 0.00", "leela", 12)],
    dict(vendor="The Riverside Hotel Chiang Mai", date="2026-08-12", total=tot, vat=v, category="ที่พัก"), dict(width=560, pad=30), dict(rot=2, blur=0.4))

# ---------- 9. Pharmacy ----------
it = [("Paracetamol 500mg x10", 2, 15), ("Cetirizine 10mg x10", 1, 45), ("หน้ากากอนามัย 50 ชิ้น", 1, 89), ("แอลกอฮอล์เจล 100ml", 1, 59)]
tot = sum(q * p for _, q, p in it); b, v = vat_split(tot)
add("09_pharmacy.png", [("ร้านยาเภสัชกรใจดี", "c", "tahomab", 18), ("ขย.1 เลขที่ กท 12345", "c", "tahoma", 12), ("เลขประจำตัวผู้เสียภาษี 3101234567890", "c", "tahoma", 11), ("--",), ("2col", "No. 000873", "16/08/2026 18:02", "tahoma", 12), ("--",),
    *items_block(it, "tahoma", 13), ("--",), ("2col", "ยอดสุทธิ", money(tot), "tahomab", 16), ("2col", "(รวม VAT", money(v) + ")", "tahoma", 11), ("ภก. สมหญิง ใจดี  เลขที่ใบอนุญาต ภ.23456", "c", "tahoma", 11)],
    dict(vendor="ร้านยาเภสัชกรใจดี", date="2026-08-16", total=tot, vat=v, category="สุขภาพ"), dict(width=350), dict(rot=-3, noise=0.01, shadow=True))

# ---------- 10. Stationery cash bill (form-style) ----------
add("10_cash_bill_form.png", [("บิลเงินสด / CASH BILL", "c", "cordia", 30), ("ร้านเครื่องเขียนสมบูรณ์", "c", "cordia", 24), ("ตลาดหัวตะเข้ ลาดกระบัง โทร 089-777-1234", "c", "cordia", 18), ("--",),
    ("2col", "เล่มที่ 12  เลขที่ 0451", "วันที่ 14/8/2026", "cordia", 20), ("นาม  สจล. คณะวิศวกรรมศาสตร์", "l", "cordia", 20), ("--",),
    ("2col", "กระดาษ A4 80g (รีม)", "5  x 115  =  575", "cordia", 20), ("2col", "ปากกาเคมี 2 หัว", "12  x 15  =  180", "cordia", 20), ("2col", "แฟ้มสันกว้าง", "6  x 45  =  270", "cordia", 20), ("2col", "เทปใส", "4  x 25  =  100", "cordia", 20), ("--",),
    ("2col", "รวมเงิน", "1,125.-", "cordia", 26), ("", 12), ("2col", "ผู้รับเงิน ..............", "ผู้ซื้อ ..............", "cordia", 18)],
    dict(vendor="ร้านเครื่องเขียนสมบูรณ์", date="2026-08-14", total=1125.0, vat=0, category="อุปกรณ์"), dict(width=420, bg=(255, 250, 230), ink=(20, 20, 100)), dict(rot=4, noise=0.02, skew=-12))

# ---------- 11. LINE MAN food delivery ----------
add("11_lineman.png", [("LINE MAN", "l", "tahomab", 24), ("ใบเสร็จรับเงิน", "l", "tahoma", 13), ("--",), ("ร้าน: ข้าวมันไก่เจ๊หมวย (ซอยลาดกระบัง 46)", "l", "tahoma", 12), ("หมายเลขคำสั่งซื้อ LM-20260813-88213", "l", "tahoma", 11), ("13 ส.ค. 2026  12:08", "l", "tahoma", 11), ("--",),
    ("2col", "ข้าวมันไก่ต้ม พิเศษ x2", "140.00", "tahoma", 13), ("2col", "ข้าวมันไก่ทอด x1", "60.00", "tahoma", 13), ("2col", "น้ำซุป x3", "0.00", "tahoma", 13), ("--",), ("2col", "ค่าอาหาร", "200.00", "tahoma", 13), ("2col", "ค่าส่ง", "25.00", "tahoma", 13), ("2col", "ค่าบริการ", "5.00", "tahoma", 13), ("2col", "คูปองส่วนลด", "-20.00", "tahoma", 13), ("--",),
    ("2col", "ยอดชำระ", "฿210.00", "tahomab", 18), ("ชำระผ่าน Rabbit LINE Pay", "l", "tahoma", 12)],
    dict(vendor="LINE MAN - ข้าวมันไก่เจ๊หมวย", date="2026-08-13", total=210.0, vat=0, category="อาหาร"), dict(width=380), dict(rot=-1, blur=0.3))

# ---------- 12. Parking tiny slip ----------
add("12_parking.png", [("ลานจอดรถ เซ็นทรัล", "c", "tahomab", 14), ("บัตรจอดรถ / ใบเสร็จ", "c", "tahoma", 11), ("--",), ("เข้า 12/08/26 10:02", "l", "tahoma", 11), ("ออก 12/08/26 14:47", "l", "tahoma", 11), ("ระยะเวลา 4:45 ชม.", "l", "tahoma", 11), ("--",), ("2col", "ค่าจอด", "40.00", "tahomab", 13), ("ทะเบียน 2ขค 8899", "c", "tahoma", 10)],
    dict(vendor="ลานจอดรถ เซ็นทรัล", date="2026-08-12", total=40.0, vat=0, category="เดินทาง"), dict(width=240, pad=14), dict(rot=7, fade=0.45, noise=0.02, blur=0.5))

# ---------- 13. Mookata ----------
tot = 4 * 259 + 2 * 39 + 1 * 79 + 120
add("13_mookata.png", [("หมูกระทะ ลุงเบิ้ม บุฟเฟ่ต์", "c", "tahomab", 20), ("สาขาหัวตะเข้", "c", "tahoma", 13), ("--",), ("2col", "โต๊ะ 12  ผู้ใหญ่ 4", "11/08/2026 20:15", "tahoma", 12), ("--",),
    ("2col", "บุฟเฟ่ต์ผู้ใหญ่ x4", "1,036.00", "tahoma", 14), ("2col", "น้ำอัดลมรีฟิล x2", "78.00", "tahoma", 14), ("2col", "เบียร์ช้าง x1", "79.00", "tahoma", 14), ("2col", "ค่ามัดจำอาหารเหลือ", "120.00", "tahoma", 14), ("--",), ("2col", "รวม", money(tot), "tahomab", 18), ("ไม่รวม VAT (ร้านไม่จด VAT)", "c", "tahoma", 11)],
    dict(vendor="หมูกระทะ ลุงเบิ้ม บุฟเฟ่ต์", date="2026-08-11", total=float(tot), vat=0, category="อาหาร"), dict(width=360), dict(rot=-5, blur=1.0, noise=0.015, shadow=True))

# ---------- 14. Café Amazon ----------
it = [("อเมริกาโน่เย็น", 1, 60), ("คาปูชิโน่ร้อน", 1, 55), ("เค้กส้ม", 1, 70)]
tot = sum(q * p for _, q, p in it); b, v = vat_split(tot)
add("14_cafe_amazon.png", [("Café Amazon", "c", "tahomab", 22), ("สาขา ปตท. ร่มเกล้า", "c", "tahoma", 12), ("บจก. ปตท. น้ำมันและการค้าปลีก (มหาชน)", "c", "tahoma", 11), ("TAX#0107561000013 VAT INCLUDED", "c", "tahoma", 11), ("--",),
    ("2col", "10/08/2026 15:44", "Bill 2610-0093", "tahoma", 12), *items_block(it, "tahoma", 13), ("--",), ("2col", "TOTAL", money(tot), "tahomab", 16), ("2col", "Before VAT", money(b), "tahoma", 11), ("2col", "VAT 7%", money(v), "tahoma", 11), ("2col", "QR Payment", money(tot), "tahoma", 12)],
    dict(vendor="Café Amazon สาขา ปตท. ร่มเกล้า", date="2026-08-10", total=tot, vat=v, category="อาหาร"), dict(width=330), dict(rot=2, fade=0.3))

# ---------- 15. Online order e-receipt ----------
it = [("Logitech MX Keys Mini", 1, 3290), ("แผ่นรองเมาส์ XXL", 1, 350)]
b = sum(q * p for _, q, p in it); v = round(b * 0.07, 2); tot = b + v + 0
add("15_online_order.png", [("Lazada", "l", "tahomab", 26), ("ใบกำกับภาษี/ใบเสร็จรับเงิน (e-Tax Invoice)", "l", "tahoma", 13), ("--",), ("ผู้ขาย: บจก. ลาซาด้า จำกัด  เลขผู้เสียภาษี 0105555012345", "l", "tahoma", 11), ("หมายเลขคำสั่งซื้อ 8891023345117  วันที่ 09/08/2026", "l", "tahoma", 11), ("ผู้ซื้อ: นายสมชาย ใจดี", "l", "tahoma", 11), ("--",),
    *[("2col", n, money(q * p), "tahoma", 13) for n, q, p in it], ("2col", "ค่าจัดส่ง", "0.00", "tahoma", 13), ("--",), ("2col", "มูลค่าก่อนภาษี", money(b), "tahoma", 12), ("2col", "ภาษีมูลค่าเพิ่ม 7%", money(v), "tahoma", 12), ("2col", "ยอดรวมสุทธิ", money(tot), "tahomab", 16), ("ชำระด้วยบัตรเครดิต", "l", "tahoma", 11)],
    dict(vendor="Lazada", date="2026-08-09", total=tot, vat=v, category="อุปกรณ์"), dict(width=480, pad=26), dict(rot=0))

# ---------- 16. Expressway toll ----------
add("16_tollway.png", [("การทางพิเศษแห่งประเทศไทย", "c", "tahomab", 14), ("ทางพิเศษศรีรัช", "c", "tahoma", 12), ("ด่านอโศก 4", "c", "tahoma", 12), ("--",), ("08/08/2026 17:21", "c", "tahoma", 12), ("รถ 4 ล้อ", "c", "tahoma", 12), ("2col", "ค่าผ่านทาง", "50.00 บาท", "tahomab", 14), ("เงินสด", "c", "tahoma", 11), ("TX 0417-223981", "c", "tahoma", 10)],
    dict(vendor="การทางพิเศษฯ ด่านอโศก 4", date="2026-08-08", total=50.0, vat=0, category="เดินทาง"), dict(width=230, pad=14), dict(rot=-8, fade=0.5, noise=0.03))

# ---------- 17. Big C long supermarket slip ----------
it = [("ข้าวหอมมะลิ 5kg", 1, 189), ("น้ำมันพืช 1L", 2, 52), ("ไข่ไก่ เบอร์2 30ฟอง", 1, 129), ("นมถั่วเหลือง x6", 1, 69), ("ทิชชู่ 12 ม้วน", 1, 119), ("ผงซักฟอก 900g", 1, 95), ("แชมพู 450ml", 1, 159), ("ปลากระป๋อง", 6, 18), ("มาม่า แพ็ค 10", 2, 65), ("โค้ก 1.5L", 2, 32)]
tot = sum(q * p for _, q, p in it); b, v = vat_split(tot)
add("17_bigc.png", [("Big C", "c", "tahomab", 26), ("บิ๊กซี ซูเปอร์เซ็นเตอร์ สาขาร่มเกล้า", "c", "tahoma", 12), ("บมจ. บิ๊กซี ซูเปอร์เซ็นเตอร์ TAX 0107536000633", "c", "tahoma", 11), ("ใบกำกับภาษีอย่างย่อ", "c", "tahoma", 11), ("--",), ("2col", "07/08/2026 11:03", "เครื่อง 014  #1192", "tahoma", 11), ("--",),
    *items_block(it, "tahoma", 12), ("--",), ("2col", f"รวม {sum(q for _, q, _ in it)} รายการ", money(tot), "tahomab", 15), ("2col", "ก่อน VAT", money(b), "tahoma", 11), ("2col", "VAT 7%", money(v), "tahoma", 11), ("2col", "เงินสด", "1,500.00", "tahoma", 12), ("2col", "เงินทอน", money(1500 - tot), "tahoma", 12), ("Big Card 1234 5678 9012  คะแนน +14", "c", "tahoma", 11)],
    dict(vendor="Big C สาขาร่มเกล้า", date="2026-08-07", total=tot, vat=v, category="ของใช้"), dict(width=340), dict(rot=1, fade=0.2, noise=0.01, shadow=True))

# ---------- 18. IT repair service (abbreviated tax invoice, Consolas mono) ----------
b = 1500 + 890; v = round(b * 0.07, 2); tot = b + v
add("18_it_repair.png", [("QUICKFIX COMPUTER SERVICE", "c", "consola", 16), ("Tax ID 0115560012378", "c", "consola", 12), ("ABB. TAX INVOICE", "c", "consola", 12), ("------------------------------", "c", "consola", 12), ("Date: 06/08/2026   No: 26-0318", "l", "consola", 12), ("Cust: MemBoy Tech Co.,Ltd.", "l", "consola", 12), ("------------------------------", "c", "consola", 12),
    ("2col", "Laptop SSD upgrade 1TB", "1500.00", "consola", 12), ("2col", "Labor / diagnostic", "890.00", "consola", 12), ("------------------------------", "c", "consola", 12), ("2col", "SUBTOTAL", money(b), "consola", 12), ("2col", "VAT 7%", money(v), "consola", 12), ("2col", "TOTAL", money(tot), "consola", 15), ("Warranty 90 days", "l", "consola", 11)],
    dict(vendor="QuickFix Computer Service", date="2026-08-06", total=tot, vat=v, category="อุปกรณ์"), dict(width=380, bg=(248, 248, 248)), dict(rot=-2, blur=0.4, noise=0.008))

# ---------- 19. BTS / rail ticket ----------
add("19_bts.png", [("BTS SkyTrain", "c", "tahomab", 18), ("Rabbit Card Top-up Receipt", "c", "tahoma", 11), ("--",), ("2col", "Station", "Siam", "tahoma", 12), ("2col", "Date", "05/08/2026 08:31", "tahoma", 12), ("2col", "Card No.", "0123 4567 8901 2345", "tahoma", 12), ("--",), ("2col", "Top-up Amount", "300.00", "tahomab", 14), ("2col", "Remaining Value", "347.00", "tahoma", 12), ("Ref 050826-SIA-0092", "c", "tahoma", 10)],
    dict(vendor="BTS SkyTrain (Rabbit top-up)", date="2026-08-05", total=300.0, vat=0, category="เดินทาง"), dict(width=280, pad=16), dict(rot=3, fade=0.35, noise=0.015))

# ---------- 20. Japanese restaurant with service charge ----------
it = [("Salmon Sashimi Set", 2, 390), ("Tonkotsu Ramen", 1, 260), ("Gyoza (6 pcs)", 1, 120), ("Green Tea (refill)", 3, 40)]
food = sum(q * p for _, q, p in it); sc = round(food * 0.10, 2); b = food + sc; v = round(b * 0.07, 2); tot = round(b + v, 2)
add("20_japanese_service_charge.png", [("SUSHI-YA", "c", "leelab", 22), ("ซูชิยะ เจแปนนีส เรสเตอรองท์ (เมกาบางนา)", "c", "leela", 12), ("บจก. ซูชิยะ (ประเทศไทย)  TAX 0105559087654", "c", "leela", 11), ("--",), ("2col", "Table 21  Guests 2", "04/08/2026 19:48", "leela", 12), ("2col", "Bill No. 0804-0177", "Server: Nok", "leela", 12), ("--",),
    *items_block(it, "leela", 13), ("--",), ("2col", "Food Total", money(food), "leela", 12), ("2col", "Service Charge 10%", money(sc), "leela", 12), ("2col", "Subtotal", money(b), "leela", 12), ("2col", "VAT 7%", money(v), "leela", 12), ("2col", "GRAND TOTAL", money(tot), "leelab", 17), ("Thank you - Arigatou", "c", "leela", 12)],
    dict(vendor="Sushi-Ya (Mega Bangna)", date="2026-08-04", total=tot, vat=v, category="อาหาร", note="service charge 10%"), dict(width=380, bg=(253, 252, 248)), dict(rot=-3, blur=0.5, shadow=True))

for name, rows, style, fx, label in receipts:
    im = photo_effect(render(rows, **style), paper=style.get("bg", (255, 255, 255)), **fx)
    im.save(OUT / name, quality=88)
    labels.append({"file": name, **label})
    print(name, im.size)
(OUT / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(labels)} receipts -> {OUT}")
