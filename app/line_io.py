"""LINE Messaging API: signature verify, content download, reply/push.
ponytail: raw httpx instead of line-bot-sdk — the 4 calls we need are ~40 lines."""
import base64
import hashlib
import hmac
import os

import httpx

SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
API = "https://api.line.me/v2/bot"
CONTENT_API = "https://api-data.line.me/v2/bot"
_auth = {"Authorization": f"Bearer {TOKEN}"}


def verify_signature(body: bytes, signature: str) -> bool:
    mac = hmac.new(SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(mac).decode(), signature or "")


async def get_content(message_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{CONTENT_API}/message/{message_id}/content", headers=_auth)
        r.raise_for_status()
        return r.content


async def reply(reply_token: str, messages: list[dict]):
    if not TOKEN:  # dev mode without LINE credentials: log instead of failing the event
        import logging
        logging.getLogger("pbook").info("DEV reply -> %s", messages)
        return
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{API}/message/reply", headers=_auth, json={"replyToken": reply_token, "messages": messages})
        r.raise_for_status()


async def push(line_user_id: str, messages: list[dict]):
    if not TOKEN:
        import logging
        logging.getLogger("pbook").info("DEV push -> %s", messages)
        return
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{API}/message/push", headers=_auth, json={"to": line_user_id, "messages": messages})
        r.raise_for_status()


def text(msg: str) -> dict:
    return {"type": "text", "text": msg[:5000]}
