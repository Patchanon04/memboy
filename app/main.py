"""PBook — W1: webhook -> Redis queue (arq), Thai PDF proof, DB init. Processing lives in app/worker.py."""
import datetime
import json
import logging
import os
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app import line_io, report
from app.db import init_db

log = logging.getLogger("pbook")
logging.basicConfig(level=logging.INFO)

Path("/data/uploads").mkdir(parents=True, exist_ok=True)
app = FastAPI()
app.mount("/files", StaticFiles(directory="/data/reports"), name="files")


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
