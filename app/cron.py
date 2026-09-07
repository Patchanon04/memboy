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
