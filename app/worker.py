"""arq worker: pulls LINE events off Redis, processes with per-user ordering + retry."""
import asyncio
import collections
import logging
import os

from arq import Retry
from arq.connections import RedisSettings

from app import events
from app.db import init_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pbook")

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
            # ponytail: dead letter = loud log; user simply resends. DLQ table if this ever matters.
            log.exception("event %s DEAD after %d tries: %s", mid, MAX_TRIES, ev)


async def startup(ctx):
    init_db()
    log.info("worker up")


class WorkerSettings:
    functions = [process_event]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    max_tries = MAX_TRIES
    retry_jobs = True
