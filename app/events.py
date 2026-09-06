"""Event processing — runs inside the arq worker. Every LINE event becomes one agent turn."""
import collections
import io
import logging
import time
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app import agent, line_io
from app.db import ProcessedEvent, session

log = logging.getLogger("pbook")
UPLOADS = Path("/data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)
CONFIRM_QUICK = ["ยืนยัน บันทึกเลย", "ขอแก้ไข", "ยกเลิก ไม่บันทึก"]
RATE_LIMIT, RATE_WINDOW = 10, 60  # guardrail #7: max turns per user per minute (in-memory; worker is a single process)
_hits: dict[str, collections.deque] = collections.defaultdict(collections.deque)


def rate_limited(uid: str) -> bool:
    now, q = time.time(), _hits[uid]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


def shrink(data: bytes, max_px: int = 1280) -> bytes:
    """guardrail #8: LINE photos are 1-3 MB; the model needs ~1280px at most."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return data

WELCOME = ("สวัสดีค่ะ 👋 PBook ช่วยเก็บใบเสร็จและทำรายงานเบิกให้ค่ะ\n"
           "ลองส่ง 📷 รูปใบเสร็จมาได้เลย เดี๋ยวสรุปให้ยืนยันก่อนบันทึก\n"
           "ถามได้เช่น: \"เดือนนี้ใช้ไปเท่าไหร่\" / \"ขอรายงาน PDF\" / \"สร้างโปรไฟล์ทริปเชียงใหม่\"")


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


def _messages(out: dict) -> list[dict]:
    msgs = [line_io.text(out["reply"], quick=CONFIRM_QUICK if out["draft"] else None)]
    for p in out["images"]:
        msgs.append(line_io.image(f"{line_io.base_url()}/uploads/{Path(p).name}"))
    for p in out["files"]:
        kind = "PDF" if p.endswith(".pdf") else "CSV"
        msgs.append(line_io.file_link(f"📄 รายงาน {kind} พร้อมแล้ว", f"{line_io.base_url()}/files/{Path(p).name}"))
    return msgs


async def handle_event(ev: dict):
    msg = ev.get("message", {})
    mid = msg.get("id")
    if mid and already_processed(mid):
        log.info("duplicate event %s skipped", mid)
        return
    uid = ev.get("source", {}).get("userId")
    token = ev.get("replyToken")

    if ev.get("type") == "follow":  # onboarding
        await line_io.send(token, uid, [line_io.text(WELCOME, quick=["วิธีใช้", "สรุปค่าใช้จ่ายเดือนนี้"])])
        return
    if ev.get("type") != "message" or not uid:
        return

    kind = msg.get("type")
    if kind in ("image", "file", "text") and rate_limited(uid):
        await line_io.send(token, uid, [line_io.text("ส่งมาเร็วไปนิดนึงค่ะ 🙏 รอสักครู่แล้วลองใหม่นะคะ")])
        mark_processed(mid)
        return
    text, image_path = None, None
    if kind in ("image", "file"):
        if ev.get("_acked"):
            token = None  # the webhook already used the reply token to ack; result goes out as a push
        data = await line_io.get_content(mid)
        is_pdf = kind == "file" and msg.get("fileName", "").lower().endswith(".pdf")
        image_path = str(UPLOADS / f"{mid}{'.pdf' if is_pdf else '.jpg'}")
        Path(image_path).write_bytes(data if is_pdf else shrink(data))
        log.info("saved %s (%d bytes)", image_path, len(data))
    elif kind == "text":
        text = msg.get("text", "")
    else:
        return  # sticker/audio/etc: nothing to do, and don't mark processed for nothing

    out = await agent.run_turn(uid, text=text, image_path=image_path)
    await line_io.send(token, uid, _messages(out))
    mark_processed(mid)  # AFTER success — a failed event must stay retryable
