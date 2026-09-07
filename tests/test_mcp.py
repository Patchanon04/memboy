"""MCP server smoke test through real clients (no LLM): stdio, then remote HTTP at /mcp.
Run: docker compose exec -T app python -m tests.test_mcp"""
import asyncio
import base64
import io
import json
import os
import uuid

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from PIL import Image

from app import agent, tools
from app.db import Invoice, User, init_db, session

ME, OTHER = f"test:mcp:{uuid.uuid4().hex[:6]}", f"test:mcp:{uuid.uuid4().hex[:6]}"
HTTP = "http://127.0.0.1:8080/mcp"
TOKEN = os.environ.get("MCP_TOKEN", "")


def text(res) -> dict:
    return json.loads(next(c.text for c in res.content if c.type == "text"))


async def exercise(cs: ClientSession, other_id: int):
    """Same contract over any transport."""
    names = {t.name for t in (await cs.list_tools()).tools}
    assert names == {"memboy_upload_receipt", *(f"memboy_{n}" for n in agent.TOOLS)}, names

    res = await cs.call_tool("memboy_summarize_expenses", {"date_from": "2026-08-01", "date_to": "2026-08-31"})
    assert not res.is_error and text(res)["total"] == 0, res

    # guardrail #1: the other user's invoice does not exist for me
    res = await cs.call_tool("memboy_update_invoice", {"invoice_id": other_id, "fields": {"total": 1}})
    assert res.is_error and "ไม่พบบิล" in res.content[0].text, res
    res = await cs.call_tool("memboy_find_invoices", {"date_from": "2026-08-01", "date_to": "2026-08-31", "profile": "all"})
    assert not res.is_error and text(res)["count"] == 0, text(res)

    # bad args -> actionable error, not a crash
    res = await cs.call_tool("memboy_update_invoice", {"invoice_id": other_id, "fields": {"status": "confirmed"}})
    assert res.is_error, res

    # upload -> image_id lands in /data/uploads with the right extension
    buf = io.BytesIO(); Image.new("RGB", (4, 4), "white").save(buf, "PNG")
    res = await cs.call_tool("memboy_upload_receipt", {"image_base64": base64.b64encode(buf.getvalue()).decode(), "filename": "r.png"})
    up = text(res); assert not res.is_error and os.path.exists(f"/data/uploads/{up['image_id']}.png"), up
    res = await cs.call_tool("memboy_upload_receipt", {"image_base64": "not base64!!"})
    assert res.is_error, res

    res = await cs.call_tool("memboy_transfer_money", {})
    assert res.is_error, res


async def main():
    init_db()
    with session() as s:  # someone else's invoice — must stay invisible through MCP
        other = s.get(User, agent.get_user(OTHER))
        iv = Invoice(profile_id=tools._active_profile(other, s).id, vendor="ร้านของคนอื่น", invoice_date="2026-08-01",
                     subtotal=100, vat=0, total=100, total_thb=100, category="อาหาร", status="confirmed")
        s.add(iv); s.commit(); other_id = iv.id

    # --- stdio ---
    params = StdioServerParameters(command="python", args=["-m", "app.mcp_server"], env={**os.environ, "MEMBOY_MCP_USER": ME})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as cs:
        await cs.initialize()
        await exercise(cs, other_id)
    print("stdio OK")

    # --- remote HTTP: fail closed without the token, then the same contract with it ---
    assert TOKEN, "MCP_TOKEN must be set in the container env"
    async with httpx.AsyncClient() as c:
        assert (await c.post(HTTP, json={})).status_code == 401
        assert (await c.post(HTTP, json={}, headers={"Authorization": "Bearer wrong"})).status_code == 401
    hc = create_mcp_http_client(headers={"Authorization": f"Bearer {TOKEN}", "X-MemBoy-User": ME})
    async with streamable_http_client(HTTP, http_client=hc) as (r, w, *_), ClientSession(r, w) as cs:
        await cs.initialize()
        await exercise(cs, other_id)
        # header picks the user: as OTHER the invoice is visible
    hc2 = create_mcp_http_client(headers={"Authorization": f"Bearer {TOKEN}", "X-MemBoy-User": OTHER})
    async with streamable_http_client(HTTP, http_client=hc2) as (r, w, *_), ClientSession(r, w) as cs:
        await cs.initialize()
        res = await cs.call_tool("memboy_find_invoices", {"date_from": "2026-08-01", "date_to": "2026-08-31"})
        assert not res.is_error and text(res)["count"] == 1, text(res)
    print("http OK")
    print("ALL MCP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
