"""arq worker: pulls LINE events off Redis, processes with per-user ordering + retry."""
import asyncio
import collections
import logging
import os

from arq import Retry, cron
from arq.connections import RedisSettings

from app import cron as jobs, events
from app.db import init_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("memboy")

_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)  # per-user ordering (arq itself doesn't order)

MAX_TRIES = 3


async def process_event(ctx, ev: dict):
    uid = ev.get("source", {}).get("userId", "-")
    async with _locks[uid]:
        try:
            await events.handle_event(ev)
        except Exception:
            mid = ev.get("message", {}).get("id")
            if ctx["job_try"] < MAX_TRIES:
                log.exception("event %s failed (try %d/%d) — will retry", mid, ctx["job_try"], MAX_TRIES)
                raise Retry(defer=10 * ctx["job_try"])
            log.exception("event %s DEAD after %d tries: %s", mid, MAX_TRIES, ev)
            try:  # the user must not be left hanging
                from app import line_io
                await line_io.push(uid, [line_io.text("ขออภัยค่ะ ระบบขัดข้องชั่วคราว รบกวนส่งข้อความ/รูปนี้ใหม่อีกครั้งนะคะ 🙏")])
            except Exception:
                log.exception("dead-letter notify failed")


async def startup(ctx):
    init_db()
    log.info("worker up")


class WorkerSettings:
    functions = [process_event]
    cron_jobs = [cron(jobs.weekly_summary, weekday=6, hour=18, minute=0),        # Sunday 18:00 (container TZ=Asia/Bangkok)
                 cron(jobs.monthly_report, day=25, hour=9, minute=0)]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    max_tries = MAX_TRIES
    retry_jobs = True
