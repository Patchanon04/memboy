"""MCP server smoke test through a real stdio client (no LLM). Run: docker compose exec -T app python -m tests.test_mcp"""
import asyncio
import base64
import io
import json
import os
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from app import agent, tools
from app.db import Invoice, User, init_db, session

ME, OTHER = f"test:mcp:{uuid.uuid4().hex[:6]}", f"test:mcp:{uuid.uuid4().hex[:6]}"


def text(res) -> dict:
    return json.loads(next(c.text for c in res.content if c.type == "text"))


async def main():
    init_db()
    # someone else's invoice — must stay invisible through MCP
    with session() as s:
        other = s.get(User, agent.get_user(OTHER))
        iv = Invoice(profile_id=tools._active_profile(other, s).id, vendor="ร้านของคนอื่น", invoice_date="2026-08-01",
                     subtotal=100, vat=0, total=100, total_thb=100, category="อาหาร", status="confirmed")
        s.add(iv); s.commit(); other_id = iv.id

    params = StdioServerParameters(command="python", args=["-m", "app.mcp_server"], env={**os.environ, "PBOOK_MCP_USER": ME})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as cs:
        await cs.initialize()
        names = {t.name for t in (await cs.list_tools()).tools}
        assert names == {"pbook_upload_receipt", *(f"pbook_{n}" for n in agent.TOOLS)}, names

        # read tool on a fresh user
        res = await cs.call_tool("pbook_summarize_expenses", {"date_from": "2026-08-01", "date_to": "2026-08-31"})
        assert not res.is_error and text(res)["total"] == 0, res

        # guardrail #1 through MCP: the other user's invoice does not exist for me
        res = await cs.call_tool("pbook_update_invoice", {"invoice_id": other_id, "fields": {"total": 1}})
        assert res.is_error and "ไม่พบบิล" in res.content[0].text, res
        res = await cs.call_tool("pbook_find_invoices", {"date_from": "2026-08-01", "date_to": "2026-08-31", "profile": "all"})
        assert not res.is_error and text(res)["count"] == 0, text(res)

        # bad args -> actionable error, not a crash
        res = await cs.call_tool("pbook_update_invoice", {"invoice_id": other_id, "fields": {"status": "confirmed"}})
        assert res.is_error, res

        # upload -> image_id lands in /data/uploads with the right extension
        buf = io.BytesIO(); Image.new("RGB", (4, 4), "white").save(buf, "PNG")
        res = await cs.call_tool("pbook_upload_receipt", {"image_base64": base64.b64encode(buf.getvalue()).decode(), "filename": "r.png"})
        up = text(res); assert not res.is_error and os.path.exists(f"/data/uploads/{up['image_id']}.png"), up
        res = await cs.call_tool("pbook_upload_receipt", {"image_base64": "not base64!!"})
        assert res.is_error, res

        # unknown tool
        res = await cs.call_tool("pbook_transfer_money", {})
        assert res.is_error, res
    print("ALL MCP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
