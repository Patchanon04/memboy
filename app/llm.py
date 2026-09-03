"""Gemma 4 via Gemini API — one function, retries, thought-part filtering."""
import asyncio
import base64
import contextvars
import os
from pathlib import Path

import httpx
import logging
import time

log = logging.getLogger("pbook")
# per-turn accounting: agent.run_turn sets this, every call adds to it (asyncio-safe)
USAGE: contextvars.ContextVar = contextvars.ContextVar("llm_usage", default=None)
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx INFO logs the full URL incl. ?key= — never

KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
FALLBACK = os.environ.get("GEMMA_FALLBACK", "gemma-4-31b-it" if "26b" in MODEL else "gemma-4-26b-a4b-it")
TIMEOUT_S = int(os.environ.get("LLM_TIMEOUT_S", "100"))  # hard images (multi-receipt) can take 26b >70s
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


class LLMError(Exception):
    pass


async def generate(contents: list[dict], temperature: float = 0.0, model: str | None = None) -> str:
    """One call with one retry; the retry switches to the fallback model (same prompt) —
    slow/hung generations tend to be per-model, so swapping beats waiting."""
    body = {"contents": contents, "generationConfig": {"temperature": temperature}}
    models = [model or MODEL, FALLBACK]
    last = "unknown"
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as c:
        for attempt, m in enumerate(models):
            t0 = time.monotonic()
            try:
                r = await c.post(URL.format(m), params={"key": KEY}, json=body)
                log.info("llm %s %s %.1fs (%d parts)", m, r.status_code, time.monotonic() - t0, sum(len(x["parts"]) for x in contents))
            except httpx.TransportError as e:  # timeout, connect error, DNS blip
                last = f"{m}: {type(e).__name__}"
                log.warning("llm %s %s after %.1fs: %r", m, type(e).__name__, time.monotonic() - t0, e)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"{m}: http {r.status_code}"
                await asyncio.sleep(2)
                continue
            if r.status_code != 200:
                raise LLMError(f"LLM http {r.status_code}: {r.text[:200]}")
            data = r.json()
            acc = USAGE.get()
            if acc is not None:
                u = data.get("usageMetadata") or {}
                acc["calls"] += 1
                acc["llm_s"] = round(acc["llm_s"] + (time.monotonic() - t0), 2)
                acc["in_tok"] += u.get("promptTokenCount", 0)
                acc["out_tok"] += u.get("candidatesTokenCount", 0)
                acc["models"].append(m)
            parts = data["candidates"][0]["content"].get("parts", [])
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    raise LLMError(f"LLM unavailable after fallback ({last})")


def image_part(path: str | Path) -> dict:
    p = Path(path)
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}
