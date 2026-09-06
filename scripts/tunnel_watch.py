"""Keep a cloudflare quick tunnel alive and keep LINE pointed at it (host-side, no container).

Quick tunnels die silently and every restart hands out a new hostname, which breaks the LINE
webhook until someone re-registers it. This watches the tunnel and, whenever it comes back with a
new URL, rewrites PUBLIC_BASE_URL in .env and re-points the webhook — no manual steps.

    python scripts/tunnel_watch.py            # foreground
    (or Start-Process to detach — see README)

curl does the HTTPS work on purpose: WARP's TLS interception breaks python's cert store here.
"""
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
LOG = ROOT / "data" / "logs" / "tunnel.log"
BASE_FILE = ROOT / "data" / "public_base_url"   # containers read this instead of their env
CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
ORIGIN = "http://127.0.0.1:8080"   # not "localhost": cloudflared resolves that to ::1, docker publishes on IPv4
CHECK_EVERY = 20


def env(key: str) -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1]
    return ""


def set_env(key: str, value: str):
    t = ENV.read_text(encoding="utf-8")
    ENV.write_text(re.sub(rf"(?m)^{key}=.*$", f"{key}={value}", t), encoding="utf-8")


def curl(*args) -> str:
    try:
        return subprocess.run(["curl", "-s", *args], capture_output=True, text=True, timeout=60).stdout
    except subprocess.TimeoutExpired:  # a hung LINE/tunnel call must never take the watchdog down with it
        return ""


def alive(base: str) -> bool:
    """Ours or not: api.trycloudflare.com also answers /health with 200, so check the body."""
    return '"ok":true' in curl("-m", "15", base + "/health").replace(" ", "")


def start_tunnel() -> str | None:
    subprocess.run(["taskkill", "/IM", "cloudflared.exe", "/F"], capture_output=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")
    with open(LOG, "ab", 0) as f:
        subprocess.Popen([CLOUDFLARED, "tunnel", "--url", ORIGIN], stdout=f, stderr=f,
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
    url = None
    for _ in range(30):
        time.sleep(2)
        # cloudflared's own control endpoint (api.trycloudflare.com) also appears in this log —
        # the assigned hostname is always multi-word, so skip anything else.
        for m in re.finditer(r"https://[a-z0-9-]+\.trycloudflare\.com", LOG.read_text(encoding="utf-8", errors="ignore")):
            if m.group(0) != "https://api.trycloudflare.com":
                url = m.group(0)
                break
        if url:
            break
    if not url:
        return None
    for _ in range(30):  # a fresh quick-tunnel hostname needs a moment before it resolves
        if alive(url):
            return url
        time.sleep(3)
    print(f"  {url} never became reachable (docker down?)", flush=True)
    return None


def point_line(url: str) -> bool:
    token = env("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        return False
    out = curl("-X", "PUT", "https://api.line.me/v2/bot/channel/webhook/endpoint",
               "-H", f"Authorization: Bearer {token}", "-H", "Content-Type: application/json",
               "-d", f'{{"endpoint": "{url}/webhook"}}')
    test = curl("-X", "POST", "https://api.line.me/v2/bot/channel/webhook/test",
                "-H", f"Authorization: Bearer {token}", "-H", "Content-Type: application/json",
                "-d", f'{{"endpoint": "{url}/webhook"}}')
    print(f"  webhook -> {url}/webhook  set={out.strip() or 'ok'}  test={test.strip()[:80]}", flush=True)
    return '"success":true' in test.replace(" ", "")


def main():
    current = env("PUBLIC_BASE_URL")
    misses = 0
    while True:
        try:
            current, misses = tick(current, misses)
        except Exception as e:  # keep watching no matter what one iteration did
            print(f"{time.strftime('%H:%M:%S')} watchdog iteration failed: {e!r}", flush=True)
        time.sleep(CHECK_EVERY)


def tick(current: str, misses: int) -> tuple[str, int]:
    if current.startswith("https://") and alive(current):
        misses = 0
    else:
        misses += 1
    # one miss is usually just an app restart; a new tunnel means a new hostname, so be sure first
    if misses >= 3:
        misses = 0
        print(f"{time.strftime('%H:%M:%S')} tunnel down ({current or 'none'}) — restarting", flush=True)
        url = start_tunnel()
        if not url:
            print("  tunnel not ready; will retry", flush=True)
            return current, misses
        print(f"  up: {url}", flush=True)
        current = url
        set_env("PUBLIC_BASE_URL", url)
        BASE_FILE.write_text(url, encoding="utf-8")
        point_line(url)
    return current, misses

if __name__ == "__main__":
    main()
