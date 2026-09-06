"""Rich Menu image 2500x1686 (3x2 cells) — run on host: python scripts/make_rich_menu.py [light|dark]
No emoji: line icons drawn with PIL so the look is consistent across phones. Font: Leelawadee UI (ships with Windows)."""
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 2500, 1686
FONT_B, FONT_R = "C:/Windows/Fonts/LeelaUIb.ttf", "C:/Windows/Fonts/LeelawUI.ttf"
THEMES = {
    "light": dict(bg=(244, 246, 248), tile=(255, 255, 255), border=(227, 231, 236), title=(17, 24, 39), sub=(107, 114, 128), disc_alpha=28),
    "dark": dict(bg=(11, 18, 32), tile=(19, 28, 46), border=(34, 48, 74), title=(248, 250, 252), sub=(148, 163, 184), disc_alpha=46, help=(148, 163, 184)),  # slate is too dim on dark
}
CELLS = [  # (icon, accent, title, subtitle)
    ("camera", (15, 157, 138), "ส่งบิล", "ถ่ายรูปใบเสร็จส่งมาได้เลย"),
    ("chart", (37, 99, 235), "สรุปเดือนนี้", "ยอดรวม แยกตามหมวด"),
    ("doc", (124, 58, 237), "ขอรายงาน", "PDF เฉพาะที่ยังไม่เบิก"),
    ("folder", (217, 119, 6), "โปรไฟล์", "แยกบริษัท / ทริป"),
    ("download", (5, 150, 105), "ขอ CSV", "เอาไปกรอกระบบเบิก"),
    ("help", (71, 85, 105), "วิธีใช้", "คำสั่งที่ใช้ได้ทั้งหมด"),
]


def icon(d, kind, cx, cy, col, s=1.0):
    """Line icons ~180px wide, stroke 16px. Everything relative to (cx, cy)."""
    w = int(16 * s)

    def rr(box, r):  # rounded rect outline
        d.rounded_rectangle([cx + box[0] * s, cy + box[1] * s, cx + box[2] * s, cy + box[3] * s], radius=r * s, outline=col, width=w)

    def line(a, b):
        d.line([cx + a[0] * s, cy + a[1] * s, cx + b[0] * s, cy + b[1] * s], fill=col, width=w, joint="curve")

    if kind == "camera":
        rr((-90, -50, 90, 70), 22)
        d.rounded_rectangle([cx - 34 * s, cy - 78 * s, cx + 34 * s, cy - 50 * s], radius=8 * s, fill=col)
        d.ellipse([cx - 36 * s, cy - 26 * s, cx + 36 * s, cy + 46 * s], outline=col, width=w)
        d.ellipse([cx + 52 * s, cy - 34 * s, cx + 68 * s, cy - 18 * s], fill=col)
    elif kind == "chart":
        for x, top in ((-64, 10), (-8, -40), (48, -80)):
            d.rounded_rectangle([cx + x * s, cy + top * s, cx + (x + 32) * s, cy + 70 * s], radius=8 * s, fill=col)
        line((-96, 90), (96, 90))
    elif kind == "doc":
        pts = [(-70, -90), (30, -90), (70, -50), (70, 90), (-70, 90)]
        d.polygon([(cx + x * s, cy + y * s) for x, y in pts], outline=col, width=w)
        line((30, -90), (30, -50)); line((30, -50), (70, -50))
        for y in (-10, 22, 54):
            line((-36, y), (36 if y != 54 else 6, y))
    elif kind == "folder":
        pts = [(-90, -70), (-30, -70), (-12, -48), (90, -48), (90, 70), (-90, 70), (-90, -70), (-30, -70)]
        d.line([(cx + x * s, cy + y * s) for x, y in pts], fill=col, width=w, joint="curve")
        line((-90, -20), (90, -20))
    elif kind == "download":
        line((0, -90), (0, 30)); line((-48, -14), (0, 34)); line((48, -14), (0, 34))
        line((-90, 40), (-90, 90)); line((-90, 90), (90, 90)); line((90, 90), (90, 40))
    elif kind == "help":
        d.ellipse([cx - 90 * s, cy - 90 * s, cx + 90 * s, cy + 90 * s], outline=col, width=w)
        f = ImageFont.truetype(FONT_B, int(120 * s))
        d.text((cx, cy - 4 * s), "?", font=f, fill=col, anchor="mm")


def render(theme: str) -> Image.Image:
    t = THEMES[theme]
    im = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(im, "RGBA")
    fb, fs = ImageFont.truetype(FONT_B, 82), ImageFont.truetype(FONT_R, 42)
    cw, ch, gap = W // 3, H // 2, 22
    for i, (kind, col, title, sub) in enumerate(CELLS):
        col = t.get(kind, col)
        x0, y0 = (i % 3) * cw, (i // 3) * ch
        d.rounded_rectangle([x0 + gap, y0 + gap, x0 + cw - gap, y0 + ch - gap], radius=44, fill=t["tile"], outline=t["border"], width=3)
        cx, cy = x0 + cw // 2, y0 + 330
        d.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=(*col, t["disc_alpha"]))
        icon(d, kind, cx, cy, col, 0.9)
        d.text((cx, y0 + 590), title, font=fb, fill=t["title"], anchor="mm")
        d.text((cx, y0 + 680), sub, font=fs, fill=t["sub"], anchor="mm")
        d.rounded_rectangle([cx - 36, y0 + ch - gap - 48, cx + 36, y0 + ch - gap - 40], radius=4, fill=(*col, 160))  # accent tick
    return im


if __name__ == "__main__":
    themes = sys.argv[1:] or ["light", "dark"]
    for th in themes:
        out = f"eval/assets/rich_menu_{th}.png"
        render(th).save(out)
        print(out)
