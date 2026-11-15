"""Eval-only bridge: answers the app's OpenAI-standard /v1/chat/completions by running the Claude Code CLI (`claude -p`),
so the same eval suites can compare Gemma with a commercial model on the user's own Claude subscription.
Runs on the host (the CLI and its login live there):  python scripts/claude_cli_bridge.py [port] [model]
then point the app at it:  LLM_BASE_URL=http://host.docker.internal:8765/v1 LLM_MODEL=claude-sonnet-5-5 LLM_KEEP_ALIVE= LLM_REASONING_EFFORT=

The CLI has no message-history input, so the conversation is sent as one transcript (role-tagged text + images).
Context is stripped to the request itself: no tools, no MCP servers, no settings, no skills, empty working directory.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
DEFAULT_MODEL = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-5-5"
CLAUDE = shutil.which("claude") or shutil.which("claude.cmd") or "claude"
EMPTY = tempfile.mkdtemp(prefix="claude-bridge-")
SYSTEM = ("You are the language model inside an application. You receive the conversation so far as a transcript; "
          "its first message holds the application's instructions. Write only the next assistant message, "
          "exactly in the format those instructions require. Do not add anything else.")


def blocks(messages):
    """OpenAI messages -> one user turn: role-tagged text, images kept as image blocks."""
    out = [{"type": "text", "text": "Transcript (oldest first):"}]
    for m in messages:
        parts = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        out.append({"type": "text", "text": f"\n[{m['role']}]"})
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image_url":
                head, data = p["image_url"]["url"].split(",", 1)  # data:<mime>;base64,<data>
                out.append({"type": "image", "source": {"type": "base64", "media_type": head[5:].split(";")[0], "data": data}})
    out.append({"type": "text", "text": "\n[assistant]  (write this message now)"})
    return out


def ask(model, messages):
    line = json.dumps({"type": "user", "message": {"role": "user", "content": blocks(messages)}}, ensure_ascii=False)
    cmd = [CLAUDE, "-p", "--model", model, "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--tools", "", "--strict-mcp-config", "--setting-sources", "local", "--disable-slash-commands",
           "--no-session-persistence", "--system-prompt", SYSTEM]
    r = subprocess.run(cmd, input=line, capture_output=True, text=True, encoding="utf-8", cwd=EMPTY, timeout=600)
    for ev in reversed([json.loads(x) for x in r.stdout.splitlines() if x.strip().startswith("{")]):
        if ev.get("type") == "result":
            if ev.get("is_error"):
                raise RuntimeError(str(ev.get("result"))[:300])
            return ev.get("result") or "", ev.get("usage") or {}
    raise RuntimeError((r.stderr or r.stdout)[-300:])


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        t0 = time.time()
        try:
            text, u = ask(body.get("model") or DEFAULT_MODEL, body["messages"])
            out, code = {"choices": [{"message": {"role": "assistant", "content": text}}],
                         "usage": {"prompt_tokens": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                                   + u.get("cache_creation_input_tokens", 0), "completion_tokens": u.get("output_tokens", 0)}}, 200
        except Exception as e:  # surfaces to the app as a 503, which llm.generate treats as "model unavailable"
            out, code = {"error": str(e)}, 503
        print(f"{code} {time.time() - t0:.1f}s {len(body['messages'])} msgs", flush=True)
        data = json.dumps(out, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"bridge on 127.0.0.1:{PORT} -> {DEFAULT_MODEL}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
