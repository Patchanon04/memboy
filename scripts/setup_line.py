"""One-time LINE setup once credentials exist in .env (run inside the app container):
  docker compose run --rm app python scripts/setup_line.py --webhook https://<public-url>/webhook --richmenu /srv/eval/assets/rich_menu.png
Sets the webhook endpoint, enables it, uploads + activates the rich menu."""
import argparse
import asyncio
import os

import httpx

TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
H = {"Authorization": f"Bearer {TOKEN}"}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webhook")
    ap.add_argument("--richmenu")
    a = ap.parse_args()
    async with httpx.AsyncClient(timeout=30) as c:
        if a.webhook:
            r = await c.put("https://api.line.me/v2/bot/channel/webhook/endpoint", headers=H, json={"endpoint": a.webhook})
            print("webhook endpoint:", r.status_code, r.text[:120])
            r = await c.post("https://api.line.me/v2/bot/channel/webhook/test", headers=H, json={"endpoint": a.webhook})
            print("webhook test:", r.status_code, r.json().get("success"), r.json().get("statusCode"))
        if a.richmenu:
            from app import line_io
            rid = await line_io.setup_rich_menu(a.richmenu)
            print("rich menu active:", rid)
    print("done — LIFF: create a LINE Login channel + LIFF app pointing at https://<public-url>/dashboard, then set LIFF_ID and LINE_LOGIN_CHANNEL_ID in .env")


if __name__ == "__main__":
    asyncio.run(main())
