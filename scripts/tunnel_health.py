"""Healthcheck for the cloudflared container — from LINE's vantage point, not ours.

On 2026-09-14 the tunnel answered Bangkok fine while LINE (Tokyo) timed out for hours: stale edge connections.
So the check asks LINE's webhook-test API to hit us. Two consecutive failures -> kill cloudflared (PID 1); the
compose restart policy brings it back with fresh edge connections. No docker socket, no host access needed.
Runs inside the cloudflared image (python:3.11-slim, stdlib only).
"""
import json
import os
import sys
import urllib.request

STATE = "/tmp/tunnel_health_fails"
token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")


def line_can_reach_us() -> tuple[bool, str]:
    if not token or not base:
        return True, "unconfigured (skipped)"
    req = urllib.request.Request("https://api.line.me/v2/bot/channel/webhook/test", method="POST",
                                 data=json.dumps({"endpoint": f"{base}/webhook"}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            j = json.loads(r.read().decode())
        return j.get("success") is True, j.get("reason", "?")
    except Exception as e:  # LINE API itself unreachable: don't punish the tunnel for our own outbound problem
        return True, f"probe error {type(e).__name__} (ignored)"


ok, detail = line_can_reach_us()
fails = 0 if ok else int(open(STATE).read() or 0) + 1 if os.path.exists(STATE) else (0 if ok else 1)
open(STATE, "w").write(str(fails))
print(f"tunnel_health ok={ok} detail={detail} fails={fails}", flush=True)
if fails >= 2:
    print("tunnel_health: LINE cannot reach us twice in a row -> restarting cloudflared", flush=True)
    os.remove(STATE)
    os.kill(1, 15)  # SIGTERM cloudflared; restart: unless-stopped re-creates the edge connections
sys.exit(0 if ok else 1)
