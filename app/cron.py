"""Proactive jobs (arq cron, runs inside the worker — no APScheduler needed):
- weekly summary every Sunday 18:00 Asia/Bangkok
- monthly PDF report on the 25th 09:00 for every profile with invoices this month
Both push via LINE (dev mode: logged)."""
import datetime
import logging

from sqlalchemy import select

from app import line_io, tools
from app.db import Invoice, Profile, User, session

log = logging.getLogger("pbook")


def _month_range(today: datetime.date):
    first = today.replace(day=1)
    return first.isoformat(), today.isoformat()


async def weekly_summary(ctx):
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=6)).isoformat()
    with session() as s:
        for u in s.scalars(select(User)):
            if not u.line_user_id.startswith("U"):  # only real LINE users get pushes
                continue
            t = tools.summarize_expenses(u, s, date_from=start, date_to=today.isoformat(), profile="all")
            if not t["count"]:
                continue
            card = line_io.summary_card("สรุป 7 วันที่ผ่านมา", t["total"], t["by_category"], f"{start} – {today}")
            await line_io.push(u.line_user_id, [card])
            log.info("weekly summary -> %s (%s)", u.line_user_id, t["total"])


async def monthly_report(ctx):
    today = datetime.date.today()
    d1, d2 = _month_range(today)
    with session() as s:
        for u in s.scalars(select(User)):
            if not u.line_user_id.startswith("U"):
                continue
            for p in s.scalars(select(Profile).where(Profile.user_id == u.id)):
                try:
                    r = tools.generate_report(u, s, date_from=d1, date_to=d2, profile=p.name)
                except tools.ToolError:
                    continue  # no invoices this month
                await line_io.push(u.line_user_id, [line_io.text(f"📄 รายงานประจำเดือนของโปรไฟล์ {p.name} ({r['count']} รายการ รวม {r['total']:,.2f} บาท)"),
                                                     line_io.file_link("เปิดรายงาน PDF", r["pdf_url"])])
                log.info("monthly report -> %s/%s", u.line_user_id, p.name)
