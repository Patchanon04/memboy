import base64
import io
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

REPORTS = Path("/data/reports")
REPORTS.mkdir(parents=True, exist_ok=True)
env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=True)


def render_report(context: dict, name: str | None = None) -> Path:
    html = env.get_template("report.html").render(**context)
    out = REPORTS / f"{name or uuid.uuid4()}.pdf"
    HTML(string=html).write_pdf(out)
    return out


def chart_png(by_category: dict, rows) -> str | None:
    """Pie (by category) + bar (by month) as one base64 PNG for the PDF. None if matplotlib missing."""
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
    monthly = {}
    for iv in rows:
        m = (iv.invoice_date or "")[:7]
        monthly[m] = monthly.get(m, 0) + (iv.total_thb or 0)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))
    if by_category:
        a1.pie(by_category.values(), labels=by_category.keys(), autopct="%1.0f%%", textprops={"fontsize": 9})
        a1.set_title("แยกตามหมวด", fontsize=11)
    ms = sorted(monthly)
    a2.bar(ms, [monthly[m] for m in ms], color="#4a7ebb")
    a2.set_title("ยอดรายเดือน (บาท)", fontsize=11)
    a2.tick_params(axis="x", labelrotation=30, labelsize=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
