"""LINE Messaging API: signature verify, content download, reply/push, message builders.
ponytail: raw httpx instead of line-bot-sdk — the handful of calls we need are short."""
import base64
import hashlib
import hmac
import logging
import os

import httpx

log = logging.getLogger("pbook")
SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
API = "https://api.line.me/v2/bot"
CONTENT_API = "https://api-data.line.me/v2/bot"
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
_auth = {"Authorization": f"Bearer {TOKEN}"}


def verify_signature(body: bytes, signature: str) -> bool:
    mac = hmac.new(SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(mac).decode(), signature or "")


async def get_content(message_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{CONTENT_API}/message/{message_id}/content", headers=_auth)
        r.raise_for_status()
        return r.content


async def _post(path: str, body: dict):
    if not TOKEN:  # dev mode without LINE credentials: log instead of failing the event
        log.info("DEV %s -> %s", path, body)
        return
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{API}/{path}", headers=_auth, json=body)
        r.raise_for_status()


async def reply(reply_token: str, messages: list[dict]):
    await _post("message/reply", {"replyToken": reply_token, "messages": messages[:5]})


async def push(line_user_id: str, messages: list[dict]):
    await _post("message/push", {"to": line_user_id, "messages": messages[:5]})


async def send(reply_token: str | None, line_user_id: str, messages: list[dict]):
    """Reply if the token is still valid (~1 min), otherwise push. Worker latency makes both paths real."""
    if reply_token:
        try:
            await reply(reply_token, messages)
            return
        except httpx.HTTPStatusError as e:
            log.info("reply failed (%s), pushing instead", e.response.status_code)
    await push(line_user_id, messages)


# ---------- message builders ----------
def text(msg: str, quick: list[str] | None = None) -> dict:
    m = {"type": "text", "text": msg[:5000]}
    if quick:
        m["quickReply"] = {"items": [{"type": "action", "action": {"type": "message", "label": q[:20], "text": q}} for q in quick[:13]]}
    return m


def image(url: str) -> dict:
    return {"type": "image", "originalContentUrl": url, "previewImageUrl": url}


def file_link(label: str, url: str) -> dict:
    return {"type": "template", "altText": label,
            "template": {"type": "buttons", "text": label[:160], "actions": [{"type": "uri", "label": "เปิดไฟล์", "uri": url}]}}


def summary_card(title: str, total: float, by_category: dict, period: str) -> dict:
    """Flex Message: big total + category bars."""
    mx = max(by_category.values()) if by_category else 1
    rows = [{"type": "box", "layout": "vertical", "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": c, "size": "sm", "flex": 3},
                    {"type": "text", "text": f"{v:,.2f}", "size": "sm", "align": "end", "flex": 2}]},
                {"type": "box", "layout": "vertical", "height": "6px", "backgroundColor": "#E8EEF5", "cornerRadius": "3px",
                 "contents": [{"type": "box", "layout": "vertical", "height": "6px", "cornerRadius": "3px",
                               "backgroundColor": "#4A7EBB", "width": f"{max(4, int(v / mx * 100))}%", "contents": []}]}]}
            for c, v in sorted(by_category.items(), key=lambda kv: -kv[1])[:6]]
    return {"type": "flex", "altText": f"{title} รวม {total:,.2f} บาท", "contents": {
        "type": "bubble", "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
            {"type": "text", "text": title, "weight": "bold", "size": "md"},
            {"type": "text", "text": period, "size": "xs", "color": "#888888"},
            {"type": "text", "text": f"฿{total:,.2f}", "weight": "bold", "size": "xxl", "color": "#1F3A5F"},
            {"type": "separator"}, *rows]},
        "footer": {"type": "box", "layout": "horizontal", "spacing": "sm", "contents": [
            {"type": "button", "style": "primary", "height": "sm", "action": {"type": "message", "label": "ขอ PDF", "text": "ขอรายงาน PDF ช่วงนี้"}},
            {"type": "button", "style": "secondary", "height": "sm", "action": {"type": "message", "label": "ขอ CSV", "text": "ขอไฟล์ CSV ช่วงนี้"}}]}}}


# ---------- rich menu (run once) ----------
RICH_MENU = {
    "size": {"width": 2500, "height": 1686}, "selected": True, "name": "pbook-main", "chatBarText": "เมนู PBook",
    "areas": [
        {"bounds": {"x": 0, "y": 0, "width": 833, "height": 843}, "action": {"type": "message", "text": "วิธีส่งบิล"}},
        {"bounds": {"x": 833, "y": 0, "width": 834, "height": 843}, "action": {"type": "message", "text": "สรุปค่าใช้จ่ายเดือนนี้"}},
        {"bounds": {"x": 1667, "y": 0, "width": 833, "height": 843}, "action": {"type": "message", "text": "ขอรายงาน PDF เดือนนี้เฉพาะที่ยังไม่เบิก"}},
        {"bounds": {"x": 0, "y": 843, "width": 833, "height": 843}, "action": {"type": "message", "text": "ดูรายการโปรไฟล์"}},
        {"bounds": {"x": 833, "y": 843, "width": 834, "height": 843}, "action": {"type": "message", "text": "ขอไฟล์ CSV เดือนนี้"}},
        {"bounds": {"x": 1667, "y": 843, "width": 833, "height": 843}, "action": {"type": "message", "text": "วิธีใช้"}},
    ],
}


async def setup_rich_menu(image_path: str) -> str:
    """Create + upload image + set as default. Returns richMenuId."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API}/richmenu", headers=_auth, json=RICH_MENU)
        r.raise_for_status()
        rid = r.json()["richMenuId"]
        with open(image_path, "rb") as f:
            r = await c.post(f"{CONTENT_API}/richmenu/{rid}/content", headers={**_auth, "Content-Type": "image/png"}, content=f.read())
            r.raise_for_status()
        r = await c.post(f"{API}/user/all/richmenu/{rid}", headers=_auth)
        r.raise_for_status()
    return rid
