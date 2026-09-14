"""Proactive jobs (arq cron, inside the worker). Agent-driven: the job hands the agent a GOAL,
the agent decides which tools to call and what to say — the scheduler only decides *when*.
- weekly summary every Sunday 18:00 Asia/Bangkok
- monthly report on the 25th 09:00
Both push via LINE (dev mode: logged)."""
import datetime
import logging
import os

from sqlalchemy import select

from app import agent, line_io
from app.db import User, session
from app.events import _messages

log = logging.getLogger("memboy")
USER_PREFIX = os.environ.get("CRON_USER_PREFIX", "U")  # real LINE ids start with "U"; override for dev tests

WEEKLY_GOAL = ("SYSTEM_GOAL: ถึงเวลาสรุปประจำสัปดาห์ (ระบบส่งเอง user ไม่ได้ถาม) — ดูค่าใช้จ่าย 7 วันล่าสุดทุกโปรไฟล์ "
               "เทียบกับสัปดาห์ก่อน เช็คแนวโน้ม/งบใน notes/บิลที่ยังไม่ได้เบิก แล้วเขียนสรุปสั้นๆ ที่มีประโยชน์จริง "
               "(ถ้าไม่มีค่าใช้จ่ายเลยให้ตอบว่า NO_SUMMARY เฉยๆ)")
MONTHLY_GOAL = ("SYSTEM_GOAL: วันที่ 25 ของเดือน (ระบบส่งเอง) — สร้างรายงาน PDF ของเดือนนี้ให้ทุกโปรไฟล์ที่มีบิล "
                "และแนบสรุปยอด บอกด้วยว่ามีบิลที่ยังไม่ได้เบิกกี่ใบ (ถ้าไม่มีบิลเลยให้ตอบ NO_SUMMARY)")


async def _run_goal(goal: str, only_user: str | None = None):
    with session() as s:
        users = [u.line_user_id for u in s.scalars(select(User)) if u.line_user_id.startswith(USER_PREFIX)]
    if only_user:
        users = [only_user]
    for uid in users:
        try:
            out = await agent.run_turn(uid, text=goal)
        except Exception:
            log.exception("proactive goal failed for %s", uid)
            continue
        if "NO_SUMMARY" in out["reply"]:
            continue
        await line_io.push(uid, _messages(out))
        log.info("proactive -> %s: %s", uid, out["reply"][:80])


async def weekly_summary(ctx, only_user: str | None = None):
    await _run_goal(WEEKLY_GOAL, only_user)


async def monthly_report(ctx, only_user: str | None = None):
    await _run_goal(MONTHLY_GOAL, only_user)


REPORT_DAYS, DELETED_IMAGE_DAYS, ORPHAN_IMAGE_DAYS, CONVERSATION_DAYS = 7, 30, 7, 30


async def purge_old_data(ctx=None) -> dict:
    """Retention (privacy, professor's note): keep only what the product still needs.
    - report PDFs/CSVs: 7 days (their signed links expire at 7 days anyway)
    - receipt images of soft-deleted invoices: 30 days after deletion (undo window), orphan uploads: 7 days
    - conversation rows: 30 days (the agent reads only the last 30 messages)
    Invoices themselves are the user's records and are never auto-deleted."""
    import datetime as dt
    from pathlib import Path
    from sqlalchemy import delete, select
    from app.db import Conversation, Invoice, session
    now = dt.datetime.utcnow()
    n = {"reports": 0, "images": 0, "conversations": 0}
    for f in Path("/data/reports").glob("*"):
        if f.is_file() and f.name != "test.pdf" and now.timestamp() - f.stat().st_mtime > REPORT_DAYS * 86400:
            f.unlink(); n["reports"] += 1
    with session() as s:
        referenced = {Path(p).name for (p,) in s.execute(select(Invoice.image_path).where(Invoice.image_path.isnot(None))) if p}
        old_deleted = {Path(iv.image_path).name for iv in s.scalars(select(Invoice).where(
            Invoice.deleted_at.isnot(None), Invoice.deleted_at < now - dt.timedelta(days=DELETED_IMAGE_DAYS), Invoice.image_path.isnot(None)))}
        for f in Path("/data/uploads").glob("*"):
            if not f.is_file():
                continue
            age = now.timestamp() - f.stat().st_mtime
            if f.name in old_deleted or (f.name not in referenced and age > ORPHAN_IMAGE_DAYS * 86400):
                f.unlink(); n["images"] += 1
        n["conversations"] = s.execute(delete(Conversation).where(Conversation.created_at < now - dt.timedelta(days=CONVERSATION_DAYS))).rowcount
        s.commit()
    log.info("purge_old_data %s", n)
    return n


_probe_fails = 0


async def tunnel_probe(ctx=None) -> dict:
    """Every 10 min ask LINE itself to hit our webhook (its vantage point, not ours). Two failures in a row -> push a
    warning to the admin's LINE (outbound still works while inbound is dead). The cloudflared container's own
    healthcheck (scripts/tunnel_health.py) does the actual restart; this job only makes the outage visible."""
    global _probe_fails
    import os, httpx
    from app import line_io
    base, token, admin = line_io.base_url(), os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""), os.environ.get("ADMIN_LINE_USER_ID", "")
    try:
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post("https://api.line.me/v2/bot/channel/webhook/test", headers={"Authorization": f"Bearer {token}"},
                             json={"endpoint": f"{base}/webhook"})
        ok = r.status_code == 200 and r.json().get("success") is True
        detail = r.json().get("reason") if r.status_code == 200 else f"http {r.status_code}"
    except Exception as e:
        ok, detail = False, type(e).__name__
    _probe_fails = 0 if ok else _probe_fails + 1
    out = {"ok": ok, "detail": detail, "fails": _probe_fails}
    if not ok and _probe_fails >= 2 and admin:
        try:
            await line_io.push(admin, [line_io.text(f"⚠️ MemBoy: LINE เข้าถึง webhook ไม่ได้ ({detail}) x{_probe_fails} — tunnel จะ restart ตัวเองภายใน ~10 นาที ถ้ายังไม่หาย docker compose restart cloudflared")])
        except Exception:
            pass
        _probe_fails = 0
    log.info("tunnel_probe %s", out)
    return out
