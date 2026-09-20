"""PDF reports. The agent turns "what the user wants in the report" into a small spec (sections, columns, grouping,
sorting, title, note); everything here is deterministic: the spec is validated against whitelists, every number is
summed in Python from the rows the tool selected, and the template only lays out what build_context computed.
Rows are plain dicts (tools.py converts the ORM objects) so this module never touches the database."""
import base64
import datetime
import io
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

REPORTS = Path("/data/reports")
REPORTS.mkdir(parents=True, exist_ok=True)
env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=True)

SECTIONS = {
    "summary": "กล่องสรุป: ยอดรวม จำนวนบิล เฉลี่ยต่อบิล VAT บิลที่แพงสุด เบิกแล้ว/ค้างเบิก",
    "chart": "กราฟวงกลมตามหมวด + กราฟแท่งตามเวลา",
    "by_category": "ตารางยอดแยกหมวด (พร้อม % ของทั้งหมด)",
    "by_vendor": "ร้านที่จ่ายมากสุด top_n ร้าน",
    "by_month": "ยอดรายเดือน",
    "by_day": "ยอดรายวัน",
    "table": "ตารางบิลรายใบ (เลือก columns / group_by / sort ได้)",
    "items": "รายการสินค้าในแต่ละบิล",
    "images": "แนบรูปใบเสร็จท้ายรายงาน (สูงสุด 12 รูป)",
    "note": "ข้อความหมายเหตุของ user (ใส่ใน note)",
    "signature": "ช่องลงชื่อผู้เบิก/ผู้อนุมัติ",
}
COLUMNS = {  # key -> (heading, numeric)
    "id": ("#", False), "date": ("วันที่", False), "vendor": ("ร้านค้า", False), "category": ("หมวด", False),
    "profile": ("โปรไฟล์", False), "doc_type": ("ประเภท", False), "subtotal": ("ก่อนลด/VAT", True),
    "discount": ("ส่วนลด", True), "vat": ("VAT", True), "total": ("ยอด (บาท)", True), "reimbursed": ("เบิก", False),
}
DEFAULT_SECTIONS = ["chart", "by_category", "table", "signature"]
DEFAULT_COLUMNS = ["date", "vendor", "category", "total", "vat", "reimbursed"]
GROUP_BY = {"category": "หมวด", "vendor": "ร้านค้า", "month": "เดือน", "profile": "โปรไฟล์", "reimbursed": "สถานะเบิก"}
SORT = {"date", "total", "vendor", "category"}
MAX_IMAGES = 12


def _listify(v) -> list[str]:
    if v in (None, "", []):
        return []
    if isinstance(v, str):
        v = v.replace("[", "").replace("]", "").replace('"', "").replace("'", "").split(",")
    return [str(x).strip().lower() for x in v if str(x).strip()]


def _check(values: list[str], allowed, what: str) -> list[str]:
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"{what} ไม่รู้จัก: {bad} — ใช้ได้: {sorted(allowed)}")
    return list(dict.fromkeys(values))  # de-dup, keep the user's order


def _sum(rows, key="total") -> float:
    return round(sum(r.get(key) or 0 for r in rows), 2)


def _bucket(rows, keyfn) -> dict:
    out: dict = {}
    for r in rows:
        k = keyfn(r) or "ไม่ระบุ"
        out[k] = round(out.get(k, 0) + (r.get("total") or 0), 2)
    return out


def _cell(r: dict, key: str) -> str:
    v = r.get(key)
    if key == "reimbursed":
        return "✓" if v else "—"
    if COLUMNS[key][1]:
        return f"{(v or 0):,.2f}"
    return "-" if v in (None, "") else str(v)


def _thumb(path: str) -> str | None:
    try:
        from PIL import Image
        p = Path(path)
        if not p.is_file() or p.suffix.lower() == ".pdf":
            return None
        im = Image.open(p).convert("RGB")
        im.thumbnail((700, 900))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def build_context(rows: list[dict], spec: dict | None = None, profile: str = "", period: str = "") -> dict:
    """rows: dicts with id,date,vendor,category,profile,doc_type,subtotal,discount,vat,total,reimbursed,qr,items,image.
    spec keys (all optional): title, sections, columns, group_by, sort, desc, top_n, note. Raises ValueError with the
    list of valid values so the agent can correct itself."""
    spec = spec or {}
    sections = _check(_listify(spec.get("sections")), SECTIONS, "sections") or list(DEFAULT_SECTIONS)
    columns = _check(_listify(spec.get("columns")), COLUMNS, "columns") or list(DEFAULT_COLUMNS)
    group_by = (str(spec.get("group_by") or "").strip().lower() or None)
    if group_by in ("none", "null"):
        group_by = None
    if group_by and group_by not in GROUP_BY:
        raise ValueError(f"group_by ไม่รู้จัก: {group_by!r} — ใช้ได้: {sorted(GROUP_BY)}")
    sort = str(spec.get("sort") or "date").strip().lower()
    if sort not in SORT:
        raise ValueError(f"sort ไม่รู้จัก: {sort!r} — ใช้ได้: {sorted(SORT)}")
    desc = str(spec.get("desc")).strip().lower() in ("true", "1", "yes") if spec.get("desc") is not None else sort == "total"
    try:
        top_n = max(1, min(30, int(spec.get("top_n") or 5)))
    except (TypeError, ValueError):
        raise ValueError("top_n ต้องเป็นจำนวนเต็ม 1-30")
    note = str(spec.get("note") or "").strip()[:600]
    if note and "note" not in sections:
        sections.insert(len(sections) - 1 if sections[-1] == "signature" else len(sections), "note")
    if group_by and "table" not in sections:
        sections.insert(0, "table")

    rows = sorted(rows, key=lambda r: ((r.get(sort) or 0) if sort == "total" else str(r.get(sort) or "")), reverse=desc)
    total = _sum(rows)

    def gkey(r):
        if group_by == "month":
            return (r.get("date") or "")[:7]
        if group_by == "reimbursed":
            return "เบิกแล้ว" if r.get("reimbursed") else "ยังไม่เบิก"
        return r.get(group_by)
    groups = []
    if group_by:
        for k in sorted({gkey(r) or "ไม่ระบุ" for r in rows}):
            g = [r for r in rows if (gkey(r) or "ไม่ระบุ") == k]
            groups.append({"key": k, "rows": g, "subtotal": _sum(g), "vat": _sum(g, "vat"), "count": len(g)})
    else:
        groups.append({"key": None, "rows": rows, "subtotal": total, "vat": _sum(rows, "vat"), "count": len(rows)})
    for g in groups:
        g["cells"] = [[(_cell(r, c), COLUMNS[c][1], r.get("qr") == "verified" and c == "vendor") for c in columns] for r in g["rows"]]

    by_category = dict(sorted(_bucket(rows, lambda r: r.get("category")).items(), key=lambda kv: -kv[1]))
    vendors: dict = {}
    for r in rows:
        v = vendors.setdefault(r.get("vendor") or "ไม่ระบุ", [0.0, 0])
        v[0] = round(v[0] + (r.get("total") or 0), 2)
        v[1] += 1
    biggest = max(rows, key=lambda r: r.get("total") or 0) if rows else None
    dates = sorted(r["date"] for r in rows if r.get("date"))
    done = _sum([r for r in rows if r.get("reimbursed")])
    images = []
    if "images" in sections:
        for r in rows:
            b64 = _thumb(r.get("image") or "")
            if b64:
                images.append({"b64": b64, "caption": f"{r.get('date') or ''} · {r.get('vendor') or ''} · {(r.get('total') or 0):,.2f} บาท"})
            if len(images) >= MAX_IMAGES:
                break
    return {
        "title": (str(spec.get("title") or "").strip()[:120] or f"รายงานค่าใช้จ่าย — {profile}"),
        "profile": profile, "period": period, "generated_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "count": len(rows), "sections": sections, "group_by": group_by, "group_label": GROUP_BY.get(group_by or "", ""),
        "headings": [(COLUMNS[c][0], COLUMNS[c][1]) for c in columns],
        "total_col": columns.index("total") if "total" in columns else None,
        "vat_col": columns.index("vat") if "vat" in columns else None,
        "groups": groups, "sum_total": total, "sum_vat": _sum(rows, "vat"),
        "summary": {"total": total, "count": len(rows), "avg": round(total / len(rows), 2) if rows else 0,
                    "vat": _sum(rows, "vat"), "discount": _sum(rows, "discount"),
                    "biggest": f"{biggest.get('vendor')} {(biggest.get('total') or 0):,.2f}" if biggest else "-",
                    "first": dates[0] if dates else "-", "last": dates[-1] if dates else "-",
                    "reimbursed": done, "pending": round(total - done, 2)},
        "by_category": [(k, v, round(100 * v / total, 1) if total else 0) for k, v in by_category.items()],
        "by_vendor": [(k, v[0], v[1]) for k, v in sorted(vendors.items(), key=lambda kv: -kv[1][0])[:top_n]],
        "by_month": sorted(_bucket(rows, lambda r: (r.get("date") or "")[:7]).items()),
        "by_day": sorted(_bucket(rows, lambda r: r.get("date")).items()),
        "items": [{"head": f"{r.get('date') or ''} · {r.get('vendor') or ''} · {(r.get('total') or 0):,.2f}", "items": r.get("items") or []}
                  for r in rows if r.get("items")],
        "images": images, "note": note,
        "chart": chart_png(by_category, rows) if "chart" in sections else None,
    }


def render_report(context: dict, name: str | None = None) -> Path:
    html = env.get_template("report.html").render(**context)
    out = REPORTS / f"{name or uuid.uuid4()}.pdf"
    HTML(string=html).write_pdf(out)
    return out


def chart_png(by_category: dict, rows: list[dict]) -> str | None:
    """Pie (by category) + bar over time as one base64 PNG. Daily bars for ranges up to ~6 weeks, monthly beyond."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError:
        return None
    for f in ("/usr/share/fonts/truetype/tlwg/Laksaman.ttf", "/usr/share/fonts/truetype/tlwg/Loma.ttf"):
        if Path(f).exists():
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            break
    days = sorted({r.get("date") for r in rows if r.get("date")})
    daily = len(days) > 1 and len({d[:7] for d in days}) <= 2 and len(days) <= 45
    series = _bucket(rows, (lambda r: r.get("date")) if daily else (lambda r: (r.get("date") or "")[:7]))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))
    if by_category:
        a1.pie(by_category.values(), labels=by_category.keys(), autopct="%1.0f%%", textprops={"fontsize": 9})
        a1.set_title("แยกตามหมวด", fontsize=11)
    xs = sorted(series)
    a2.bar([x[5:] if daily else x for x in xs], [series[x] for x in xs], color="#4a7ebb")
    a2.set_title("ยอดรายวัน (บาท)" if daily else "ยอดรายเดือน (บาท)", fontsize=11)
    a2.tick_params(axis="x", labelrotation=60 if daily else 30, labelsize=7 if daily else 8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
