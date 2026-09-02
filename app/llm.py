"""Gemma 4 via Gemini API — one function, retries, thought-part filtering."""
import asyncio
import base64
import os
from pathlib import Path

import httpx

KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


class LLMError(Exception):
    pass


async def generate(contents: list[dict], temperature: float = 0.0, model: str | None = None) -> str:
    body = {"contents": contents, "generationConfig": {"temperature": temperature}}
    async with httpx.AsyncClient(timeout=120) as c:
        for attempt in range(4):
            try:
                r = await c.post(URL.format(model or MODEL), params={"key": KEY}, json=body)
            except httpx.TimeoutException:
                if attempt < 3:
                    continue
                raise LLMError("LLM timeout")
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                await asyncio.sleep(3 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise LLMError(f"LLM http {r.status_code}: {r.text[:200]}")
            parts = r.json()["candidates"][0]["content"].get("parts", [])
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    raise LLMError("LLM gave up")


def image_part(path: str | Path) -> dict:
    p = Path(path)
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}
