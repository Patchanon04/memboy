"""Gemma 4 12B on local Ollama through the OpenAI-standard Chat Completions endpoint — one function, retries.
Any OpenAI-compatible server works (LLM_BASE_URL + LLM_API_KEY); callers pass role/parts
contents ({"role": "user"|"model", "parts": [{"text"} | {"inline_data"}]}) and this module converts them."""
import asyncio
import base64
import contextvars
import os
from pathlib import Path

import httpx
import logging
import time

log = logging.getLogger("memboy")
# per-turn accounting: agent.run_turn sets this, every call adds to it (asyncio-safe)
USAGE: contextvars.ContextVar = contextvars.ContextVar("llm_usage", default=None)
logging.getLogger("httpx").setLevel(logging.WARNING)

BASE_URL = os.environ.get("LLM_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
API_KEY = os.environ.get("LLM_API_KEY", "")          # Ollama needs none; OpenAI-compatible providers do
MODEL = os.environ.get("LLM_MODEL", "gemma4:12b")
FALLBACK = os.environ.get("LLM_FALLBACK", "")        # comma list, tried in order when the main model fails
KEEP_ALIVE = os.environ.get("LLM_KEEP_ALIVE", "24h")  # Ollama-only field; set empty for providers that reject it
# gemma4 thinks by default: ~1,900 hidden tokens (~40 s) per call for the same JSON it writes in 0.7 s without
REASONING = os.environ.get("LLM_REASONING_EFFORT", "none")
# a runaway generation (seen once: ~600 tokens at 3 tok/s) kept the GPU busy after the client timed out — cap it
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
TIMEOUT_S = int(os.environ.get("LLM_TIMEOUT_S", "300"))  # first call loads the model into VRAM


class LLMError(Exception):
    pass


def _messages(contents: list[dict]) -> list[dict]:
    """role/parts contents -> OpenAI messages (model -> assistant, inline_data -> image_url data URI)."""
    out = []
    for c in contents:
        parts = []
        for p in c["parts"]:
            if "text" in p:
                parts.append({"type": "text", "text": p["text"]})
            elif "inline_data" in p:
                d = p["inline_data"]
                parts.append({"type": "image_url", "image_url": {"url": f"data:{d['mime_type']};base64,{d['data']}"}})
        content = parts[0]["text"] if len(parts) == 1 and parts[0]["type"] == "text" else parts
        out.append({"role": "assistant" if c["role"] == "model" else "user", "content": content})
    return out


async def generate(contents: list[dict], temperature: float = 0.0, model: str | None = None) -> str:
    """One call; on a transport error or 429/5xx the same request goes to the next model in LLM_FALLBACK."""
    body = {"messages": _messages(contents), "temperature": temperature, "max_tokens": MAX_TOKENS}
    if KEEP_ALIVE:
        body["keep_alive"] = KEEP_ALIVE  # keep the weights in VRAM between turns (cold load ~12 s)
    if REASONING:
        body["reasoning_effort"] = REASONING
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    models = [model or MODEL] + [m.strip() for m in FALLBACK.split(",") if m.strip() and m.strip() != (model or MODEL)]
    last = "unknown"
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as c:
        for m in models:
            t0 = time.monotonic()
            try:
                r = await c.post(f"{BASE_URL}/chat/completions", headers=headers, json={**body, "model": m})
                log.info("llm %s %s %.1fs (%d msgs)", m, r.status_code, time.monotonic() - t0, len(contents))
            except httpx.TransportError as e:  # timeout, connect error, Ollama not running
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
                u = data.get("usage") or {}
                acc["calls"] += 1
                acc["llm_s"] = round(acc["llm_s"] + (time.monotonic() - t0), 2)
                acc["in_tok"] += u.get("prompt_tokens", 0)
                acc["out_tok"] += u.get("completion_tokens", 0)
                acc["models"].append(m)
            return data["choices"][0]["message"].get("content") or ""  # reasoning, if any, comes in a separate field
    raise LLMError(f"LLM unavailable after fallback ({last})")


def image_part(path: str | Path) -> dict:
    p = Path(path)
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}


if __name__ == "__main__":  # ponytail: the one runnable check for the converter
    msgs = _messages([{"role": "user", "parts": [{"text": "a"}]},
                      {"role": "model", "parts": [{"text": "b"}]},
                      {"role": "user", "parts": [{"inline_data": {"mime_type": "image/png", "data": "QQ=="}}, {"text": "c"}]}])
    assert msgs[0] == {"role": "user", "content": "a"} and msgs[1]["role"] == "assistant"
    assert msgs[2]["content"][0]["image_url"]["url"] == "data:image/png;base64,QQ==" and msgs[2]["content"][1]["text"] == "c"
    print("llm converter ok")
