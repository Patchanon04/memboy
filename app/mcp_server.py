"""PBook as an MCP server (stdio): the same 18 tool functions the LINE agent uses, exposed to any MCP client
(Claude Desktop, Claude Code, ...). Nothing is re-implemented — tools come straight from agent.TOOLS, so the
user-scoping / validation / soft-delete guardrails apply unchanged.

    docker compose exec -T -e PBOOK_MCP_USER=web:alice app python -m app.mcp_server

PBOOK_MCP_USER picks whose data the client sees (same external ids as LINE/web); default "mcp:local".
ponytail: low-level Server (mcp 2.x) + permissive schemas generated from the TOOLS hints — the tools validate their own args.
"""
import asyncio
import base64
import inspect
import json
import logging
import os
import uuid
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ImageContent, ListToolsResult, TextContent, Tool, ToolAnnotations

from app import agent, tools
from app.db import User, init_db, session
from app.line_io import base_url

log = logging.getLogger("pbook.mcp")
USER_EXT = os.environ.get("PBOOK_MCP_USER", "mcp:local")
UPLOADS = Path("/data/uploads")
READ_ONLY = {"check_duplicate", "find_invoices", "summarize_expenses", "analyze_trends", "get_invoice_image", "split_bill", "convert_currency"}
ANY = ["string", "number", "boolean", "object", "array", "null"]


def _schema(params: dict) -> dict:
    return {"type": "object",
            "properties": {k: {"type": ANY, "description": str(v)} for k, v in params.items()}}


UPLOAD_TOOL = Tool(
    name="pbook_upload_receipt",
    description="อัปโหลดรูปใบเสร็จ/สลิป (base64) เข้าระบบ คืน image_id สำหรับ pbook_analyze_receipt",
    input_schema={"type": "object", "required": ["image_base64"],
                  "properties": {"image_base64": {"type": "string", "description": "เนื้อไฟล์เข้ารหัส base64"},
                                 "filename": {"type": "string", "description": "ชื่อไฟล์เดิม ใช้เอานามสกุล (.jpg/.png/.pdf) ค่าเริ่มต้น .jpg"}}},
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False))


async def list_tools(ctx, params) -> ListToolsResult:
    out = [UPLOAD_TOOL]
    for name, (fn, desc, hints) in agent.TOOLS.items():
        out.append(Tool(name=f"pbook_{name}", description=desc, input_schema=_schema(hints),
                        annotations=ToolAnnotations(read_only_hint=name in READ_ONLY,
                                                    destructive_hint=name == "delete_invoice",
                                                    idempotent_hint=name in READ_ONLY or name in ("restore_invoice", "mark_reimbursed"),
                                                    open_world_hint=name == "convert_currency")))
    return ListToolsResult(tools=out)


def _upload(args: dict) -> dict:
    ext = Path(args.get("filename") or "x.jpg").suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".pdf"):
        raise tools.ToolError(f"รับเฉพาะ .jpg/.png/.pdf (ได้ {ext})")
    try:
        data = base64.b64decode(args.get("image_base64") or "", validate=True)
    except Exception:
        raise tools.ToolError("image_base64 ไม่ใช่ base64 ที่ถูกต้อง")
    if not data or len(data) > 10 * 1024 * 1024:
        raise tools.ToolError("ไฟล์ว่างหรือใหญ่เกิน 10 MB")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    image_id = f"mcp{uuid.uuid4().hex[:10]}"
    (UPLOADS / f"{image_id}{ext}").write_bytes(data)
    return {"image_id": image_id, "bytes": len(data), "next": f"pbook_analyze_receipt(image_id={image_id!r})"}


def _error(msg: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=msg)], is_error=True)


async def call_tool(ctx, params) -> CallToolResult:
    args = dict(params.arguments or {})
    key = params.name.removeprefix("pbook_")
    try:
        if key == "upload_receipt":
            result = _upload(args)
        elif key in agent.TOOLS:
            fn = agent.TOOLS[key][0]
            with session() as s:
                user = s.get(User, agent.get_user(USER_EXT))
                result = await fn(user, s, **args) if inspect.iscoroutinefunction(fn) else fn(user, s, **args)
        else:
            return _error(f"ไม่มี tool {params.name}; ใช้ tools/list ดูรายชื่อ")
    except tools.ToolError as e:  # the same self-correcting message the LINE agent gets
        return _error(str(e))
    except TypeError as e:  # unexpected/missing argument names
        return _error(f"อาร์กิวเมนต์ไม่ถูกต้อง: {e}")
    except Exception:
        log.exception("tool %s crashed", key)  # guardrail #6: full detail in the log, one line to the caller
        return _error("เครื่องมือขัดข้องภายใน")

    public = {k: v for k, v in result.items() if not k.startswith("_")}
    if result.get("_file"):
        public["file_path"] = result["_file"]  # inside the container; the *_url field is reachable from outside
    content: list[TextContent | ImageContent] = [TextContent(type="text", text=json.dumps(public, ensure_ascii=False, default=str))]
    if result.get("_image"):
        p = Path(result["_image"])
        content.append(ImageContent(type="image", data=base64.b64encode(p.read_bytes()).decode(),
                                    mime_type="image/png" if p.suffix.lower() == ".png" else "image/jpeg"))
    return CallToolResult(content=content, structured_content=public)


server = Server("pbook", on_list_tools=list_tools, on_call_tool=call_tool)


async def main():
    logging.basicConfig(level=logging.INFO, stream=open(os.devnull, "w"))  # stdout is the protocol channel — keep it clean
    init_db()
    log.info("pbook mcp up as %s (%s)", USER_EXT, base_url())
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
