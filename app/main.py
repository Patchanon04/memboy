"""PBook — W1: webhook echo + image intake + Thai PDF proof + DB init."""
import datetime
import json
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
    try:
        events = json.loads(body).get("events", [])
    except ValueError:
        log.warning("malformed webhook body ignored")
        return {"ok": True}
    failed = 0
    for ev in events:
        try:
            await handle_event(ev)
        except Exception:
            log.exception("event failed: %s", ev.get("message", {}).get("id"))
            failed += 1
    # any failure -> 500 so LINE redelivers; succeeded events are deduped, failed ones get retried
    return Response(status_code=500) if failed else {"ok": True}


async def handle_event(ev: dict):
    msg = ev.get("message", {})
    mid = msg.get("id")
    if mid:
        with session() as s:
            if s.get(ProcessedEvent, mid):
                log.info("duplicate event %s skipped", mid)
                return

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
    else:
        return  # sticker/audio/etc: nothing to do, and don't mark processed for nothing
    mark_processed(mid)  # AFTER success — a failed event must stay retryable


def mark_processed(mid: str | None):
    if not mid:
        return
    from sqlalchemy.exc import IntegrityError
    with session() as s:
        try:
            s.add(ProcessedEvent(message_id=mid))
            s.commit()
        except IntegrityError:  # concurrent duplicate: someone else finished first, fine
            s.rollback()
