"""Event processing — runs inside the arq worker."""
import logging
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app import line_io
from app.db import ProcessedEvent, session

log = logging.getLogger("pbook")
UPLOADS = Path("/data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)


def already_processed(mid: str) -> bool:
    with session() as s:
        return s.get(ProcessedEvent, mid) is not None


def mark_processed(mid: str | None):
    if not mid:
        return
    with session() as s:
        try:
            s.add(ProcessedEvent(message_id=mid))
            s.commit()
        except IntegrityError:  # concurrent duplicate: someone else finished first, fine
            s.rollback()


async def handle_event(ev: dict):
    msg = ev.get("message", {})
    mid = msg.get("id")
    if mid and already_processed(mid):
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
