"""Container DNS can be blackholed by Cloudflare WARP on the host. Workaround: resolve on the
host and pin the few hostnames we call into docker-compose.override.yml (extra_hosts).
Rerun whenever the LLM starts failing with name-resolution errors:  python scripts/dns_pin.py && docker compose up -d
"""
import socket

HOSTS = ["generativelanguage.googleapis.com", "api.frankfurter.dev", "api.line.me", "api-data.line.me"]
lines = []
for h in HOSTS:
    try:
        lines.append(f'      - "{h}:{socket.gethostbyname(h)}"')
    except OSError:
        print("skip (host can't resolve):", h)
block = "    extra_hosts:\n" + "\n".join(lines)
open("docker-compose.override.yml", "w", encoding="utf-8").write(
    f"services:\n  app:\n{block}\n  worker:\n{block}\n")
print("wrote docker-compose.override.yml:\n" + "\n".join(lines))
