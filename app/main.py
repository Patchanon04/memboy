"""PBook — W1: webhook -> Redis queue (arq), Thai PDF proof, DB init. Processing lives in app/worker.py."""
import datetime
import json
import logging
import os
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import httpx

from app import line_io, report, tools
from app.db import User, init_db, session

log = logging.getLogger("pbook")
logging.basicConfig(level=logging.INFO)

Path("/data/uploads").mkdir(parents=True, exist_ok=True)
app = FastAPI()
app.mount("/files", StaticFiles(directory="/data/reports"), name="files")
app.mount("/uploads", StaticFiles(directory="/data/uploads"), name="uploads")


@app.on_event("startup")
async def startup():
    init_db()
    app.state.queue = await create_pool(RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379")))
    # W1 acceptance: Thai PDF must render from day one
    report.render_report({
        "profile": "ทดสอบระบบ", "period": "สิงหาคม 2569",
        "generated_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "invoices": [
            {"date": "2026-08-20", "vendor": "ครัวคุณยาย", "category": "อาหาร", "total": 470.0, "vat": 0.0, "reimbursed": False},
            {"date": "2026-08-22", "vendor": "Bean There Café", "category": "อาหาร", "total": 300.0, "vat": 19.63, "reimbursed": True},
        ],
        "sum_total": 770.0, "sum_vat": 19.63,
    }, name="test")
    log.info("startup ok — /files/test.pdf ready, queue connected")


@app.get("/health")
async def health():
    return {"ok": True, "queue": bool(app.state.queue)}


@app.post("/webhook")
async def webhook(request: Request):
    """Ack fast: verify, enqueue, 200. The worker owns processing, ordering, and retries."""
    body = await request.body()
    if not line_io.verify_signature(body, request.headers.get("X-Line-Signature", "")):
        return Response(status_code=403)
    try:
        events = json.loads(body).get("events", [])
    except ValueError:
        log.warning("malformed webhook body ignored")
        return {"ok": True}
    for ev in events:
        await app.state.queue.enqueue_job("process_event", ev)
    return {"ok": True, "queued": len(events)}


# ---------- LIFF dashboard ----------
LIFF_ID = os.environ.get("LIFF_ID", "")
LINE_LOGIN_CHANNEL_ID = os.environ.get("LINE_LOGIN_CHANNEL_ID", "")
WEB = Path(__file__).parent / "templates"


@app.get("/dashboard")
def dashboard():
    html = (WEB / "dashboard.html").read_text(encoding="utf-8").replace("<body>", f'<body data-liff="{LIFF_ID}">')
    return Response(html, media_type="text/html", headers={"Cache-Control": "no-store"})


async def _resolve_uid(id_token: str | None, uid: str | None) -> str | None:
    if id_token and LINE_LOGIN_CHANNEL_ID:  # production: verify LIFF id token with LINE
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post("https://api.line.me/oauth2/v2.1/verify", data={"id_token": id_token, "client_id": LINE_LOGIN_CHANNEL_ID})
        return r.json().get("sub") if r.status_code == 200 else None
    if uid and not LIFF_ID:  # dev mode only: no LIFF configured -> accept ?uid= for local testing
        return uid
    return None


@app.get("/api/dashboard")
async def api_dashboard(id_token: str | None = None, uid: str | None = None, months: int = 6):
    ext = await _resolve_uid(id_token, uid)
    if not ext:
        return Response(status_code=401)
    today = datetime.date.today()
    first = (today.replace(day=1) - datetime.timedelta(days=31 * (max(1, months) - 1))).replace(day=1)
    with session() as s:
        from sqlalchemy import select
        u = s.scalars(select(User).where(User.line_user_id == ext)).first()
        if not u:
            return Response(status_code=404)
        t = tools.summarize_expenses(u, s, date_from=first.isoformat(), date_to=today.isoformat(), profile="all")
        tr = tools.analyze_trends(u, s, months=months, profile="all")
        pend = tools.find_invoices(u, s, date_from=first.isoformat(), reimbursed=False, profile="all", limit=50)["invoices"]
        from app.db import Profile
        names = [p.name for p in s.scalars(select(Profile).where(Profile.user_id == u.id))]
    return {"from": first.isoformat(), "to": today.isoformat(), "profiles": names, "total": t["total"], "vat": t["vat"],
            "count": t["count"], "by_category": t["by_category"], "months": tr["months"],
            "pending": [{"date": p["date"], "vendor": p["vendor"], "total": p["total"]} for p in pend]}
