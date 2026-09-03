"""Rich Menu image 2500x1686 (6 cells) — run on host: python scripts/make_rich_menu.py"""
from PIL import Image, ImageDraw, ImageFont
W, H = 2500, 1686
im = Image.new("RGB", (W, H), (245, 247, 250)); d = ImageDraw.Draw(im)
fb = ImageFont.truetype("C:/Windows/Fonts/tahomabd.ttf", 70); fs = ImageFont.truetype("C:/Windows/Fonts/tahoma.ttf", 40)
cells = [("📷", "ส่งบิล", "ถ่ายรูปใบเสร็จส่งมา"), ("📊", "สรุปเดือนนี้", "ยอดรวม แยกหมวด"), ("📄", "ขอรีพอร์ท", "PDF เฉพาะที่ยังไม่เบิก"),
         ("📁", "โปรไฟล์", "แยกบริษัท / ทริป"), ("📥", "ขอ CSV", "เอาไปกรอกระบบเบิก"), ("❓", "วิธีใช้", "คำสั่งที่ใช้ได้")]
emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 160)
for i, (ic, title, sub) in enumerate(cells):
    x0, y0 = (i % 3) * (W // 3), (i // 3) * (H // 2)
    d.rectangle([x0 + 18, y0 + 18, x0 + W // 3 - 18, y0 + H // 2 - 18], fill="white", outline=(210, 215, 222), width=4)
    cx = x0 + W // 6
    d.text((cx, y0 + 250), ic, font=emoji, fill="black", anchor="mm", embedded_color=True)
    d.text((cx, y0 + 500), title, font=fb, fill=(31, 58, 95), anchor="mm")
    d.text((cx, y0 + 600), sub, font=fs, fill=(107, 114, 128), anchor="mm")
im.save("eval/assets/rich_menu.png"); print("rich_menu.png", im.size)
