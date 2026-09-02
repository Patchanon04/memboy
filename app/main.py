"""PBook — W1: webhook echo + image intake + Thai PDF proof + DB init."""
import datetime
import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app import line_io, report
from app.db import ProcessedEvent, init_db, session

log = logging.getLogger("pbook")
logging.basicConfig(level=logging.INFO)

UPLOADS = Path("/data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.mount("/files", StaticFiles(directory="/data/reports"), name="files")


@app.on_event("startup")
def startup():
    init_db()
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
    log.info("startup ok — /files/test.pdf ready")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    if not line_io.verify_signature(body, request.headers.get("X-Line-Signature", "")):
        return Response(status_code=403)
    events = (await request.json()).get("events", [])
    for ev in events:
        await handle_event(ev)
    return {"ok": True}


async def handle_event(ev: dict):
    msg = ev.get("message", {})
    mid = msg.get("id")
    if mid:  # idempotency: LINE redelivers events on retry
        with session() as s:
            if s.get(ProcessedEvent, mid):
                log.info("duplicate event %s skipped", mid)
                return
            s.add(ProcessedEvent(message_id=mid))
            s.commit()

    if ev.get("type") != "message":
        return
    kind = msg.get("type")
    if kind == "image":
        data = await line_io.get_content(mid)
        path = UPLOADS / f"{mid}.jpg"
        path.write_bytes(data)
        log.info("saved image %s (%d bytes)", path, len(data))
        await line_io.reply(ev["replyToken"], [line_io.text(f"ได้รับรูปแล้ว ({len(data) // 1024} KB) — W1 echo")])
    elif kind == "text":
        # ponytail: W1 echo only; W2 replaces this with the agent loop
        await line_io.reply(ev["replyToken"], [line_io.text(f"echo: {msg.get('text', '')}")])
