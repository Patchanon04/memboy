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
