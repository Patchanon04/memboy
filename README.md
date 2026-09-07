# MemBoy — ผู้ช่วยจัดการใบเสร็จและรายงานค่าใช้จ่ายผ่าน LINE

Agentic AI Application (KMITL NLP Final Project) — agent loop + JSON tool calling เขียนเองบน Gemma 4

- แผนงานเต็ม: [PLAN.md](PLAN.md) · คู่มือทีม: [TEAM_GUIDE.md](TEAM_GUIDE.md)
- ผลการทดลอง: [eval/logs/EVAL_REPORT.md](eval/logs/EVAL_REPORT.md) · [HARNESS_REPORT.md](eval/logs/HARNESS_REPORT.md) · [OCR_ABLATION.md](eval/logs/OCR_ABLATION.md)
- eval assets + dataset สังเคราะห์ 230 ใบ (ไม่มีข้อมูลจริง): `eval/`

## สำหรับผู้ตรวจ — รันเองใน 5 นาที (ไม่ต้องมี LINE)

ต้องมี Docker Desktop และ Gemini API key (Gemma 4 ผ่าน Google AI Studio, free tier พอ)

```bash
cp .env.example .env            # ใส่ GEMINI_API_KEY และตั้ง WEB_PASSWORD อะไรก็ได้ (ช่อง LINE_* ปล่อยว่างได้)
docker compose up -d --build    # app + worker + redis + postgres (~3 นาทีครั้งแรก)
curl localhost:8080/health      # {"ok":true,"queue":true}
```

แล้วเปิด <http://localhost:8080> → login ชื่ออะไรก็ได้ → ลากรูปจาก `eval/dataset/` ใส่แชท → พิมพ์ "ยืนยัน" → "สรุปเดือนสิงหา" → "ขอ PDF"
หน้าเว็บใช้ agent ตัวเดียวกับ LINE ทุกบรรทัด (ต่างแค่ transport) — log การตัดสินใจทุกเทิร์นอยู่ที่ `data/logs/turns.jsonl`

ทดสอบซ้ำได้โดยไม่ใช้ LLM: `docker compose run -T --rm app python -m tests.test_w2` (loop) · `tests.test_w3` (tools) ·
`tests.test_concurrency` (ลำดับ/คิว) · `tests.test_mcp` (MCP) — ที่ใช้ LLM: `tests.test_harness` (18 ข้อ) · `eval.eval_tools` · `eval.eval_scenarios`

## ทดสอบผ่านหน้าเว็บ (ไม่ต้องใช้ LINE)

หน้าเว็บใช้ **agent ตัวเดียวกับ LINE** ทุกอย่าง (tools/DB/PDF/quick reply) ต่างแค่ transport

```bash
docker compose up -d                                   # เปิดระบบ
# เปิด http://localhost:8080 -> login (ชื่อผู้ใช้อะไรก็ได้ + WEB_PASSWORD ใน .env)

python scripts/dns_pin.py && docker compose up -d       # ถ้า LLM error เรื่อง DNS (WARP)
python scripts/tunnel_watch.py                          # เปิด cloudflare quick tunnel + เฝ้าให้ตลอด + ตั้ง LINE webhook เอง
```

ข้อมูลแยกตามชื่อผู้ใช้ที่ล็อกอิน (`web:<username>`) — เพื่อนหลายคนเทสพร้อมกันได้โดยบิลไม่ปนกัน

## คำสั่งที่ใช้บ่อย

```bash
docker compose up -d --build                                   # app + worker + redis + postgres
docker compose run --rm app python -m app.cli                  # คุยกับ agent (dev)
docker compose run -T --rm app python -m app.cli --user u1 --img /srv/eval/receipts/02_coffee.png
docker compose run -T --rm app python -m tests.test_w2         # stub tests (ไม่ใช้โควต้า LLM)
docker compose run -T --rm app python -m eval.eval_tools       # Eval A/D tool-selection (55 เคส)
docker compose run -T --rm app python -m eval.eval_scenarios   # Eval B end-to-end (11 scenario, assert DB)
docker compose run -T --rm app python -m eval.metrics          # Eval C จาก turn log
```

Dashboard (dev): `http://localhost:8080/dashboard?uid=<user>` · LIFF: ตั้ง `LIFF_ID` + `LINE_LOGIN_CHANNEL_ID` ใน .env
Rich menu: `python scripts/make_rich_menu.py` แล้ว `docker compose exec -T -e PYTHONPATH=/srv app python scripts/setup_line.py --richmenu /srv/eval/assets/rich_menu.png`

## ทดสอบ harness (guardrails/determinism) รายข้อ

```bash
docker compose run --rm app python -m tests.test_harness   # ตาราง 18 ข้อ + eval/logs/HARNESS_REPORT.md
```

ทุกข้อพิมพ์ "ค่าที่วัดได้จริง" ไม่ใช่แค่ pass/fail — ใช้แปะสไลด์ได้ตรงๆ

## ผล eval ล่าสุด (ดู `eval/logs/EVAL_REPORT.md`)

| ชุด | ผล |
|---|---|
| Extraction (200 ใบ TH/EN, png/jpg/pdf, clean/photo/camera) | ถูกครบ 5 field 95.5% (date 96%) หลัง prompt v3 |
| Eval A/D tool-selection 54 เคส | gemma-4-26b-a4b-it **54/54** · gemma-4-31b-it 47/48 (ชุด 48 เคส) |
| Eval B end-to-end 11 scenario (assert DB) | **11/11** |
| Eval C loop metrics (1,086 LLM calls) | JSON first-try 96.5%, loop-cap 0, chain ≥2 = 5%, ask-back 5% |
| Latency / token ต่อเทิร์น | p50 17.5s · p90 76s (96% เป็นเวลา LLM) · token เข้า ~4.7k ออก ~154 |
| สลิปโอน 30 ใบ (6 layout, 5 QR mismatch) | doc_type/total/ref/qr_status 100%, mismatch detection 5/5 |

## Troubleshooting (dev machine)

- **Docker Desktop dies right after start / "backend crashed … initializing Inference manager … dockerInference"** —
  a stale unix socket from Docker AI. Fix: rename `%LOCALAPPDATA%\Docker\run` away (the file itself refuses `del`),
  set `"EnableDockerAI": false` in `%APPDATA%\Docker\settings-store.json`, start Docker Desktop once (single instance).
- **LINE stops replying** — check `data/logs/watch.out`. The tunnel watchdog (`scripts/tunnel_watch.py`) needs
  3 consecutive failed `/health` (body `"ok":true`, not just HTTP 200) before it swaps hostnames; it writes the new
  URL to `data/public_base_url`, which the containers read per request, so no container restart is needed.

## Ablation: OCR before the LLM? (eval/eval_ocr_ablation.py → eval/logs/OCR_ABLATION.md)

Question: would running Tesseract (tha+eng) first make extraction faster or more accurate than sending the photo straight to Gemma 4?
60 synthetic receipts, same prompt/scoring as the main extraction eval, the three conditions run back-to-back per file. API failures ("gave up" after 4 tries) excluded.

| condition | all-5 correct | LLM p50 | prompt tokens |
|---|---|---|---|
| image only (production) | **56/58 = 97%** | 25.6 s | 463 |
| image + OCR text | 55/57 = 96% | 25.4 s (+0.3 s OCR) | 579 |
| OCR text only | 30/55 = 55% (date 53%) | 29.7 s | 323 |

Verdict: no. A receipt photo costs Gemma only ~460 tokens, so OCR text is not a smaller input; text-only loses layout
(date 53%, total 72%) and the model dawdles on noisy OCR; image+OCR just adds tokens. Latency is dominated by the API round trip,
not input size — so the speed work went into the loop instead: photos skip the "decide" call (`ROUTE_IMAGE`) and a plain-text
answer after a tool result is accepted as the reply. Live photo turn: 72 s → ~42 s (p50).

## MCP server (app/mcp_server.py)

The 18 tool functions the LINE agent calls are also served over MCP, so any MCP client — Claude Desktop, Claude Code,
another agent — can work on the same data with the same guardrails (user scoping, arg validation, draft→confirm, soft
delete). Nothing is duplicated: tools are read from `agent.TOOLS`; one extra tool `memboy_upload_receipt` takes a base64
image and hands back an `image_id` for `memboy_analyze_receipt`. One server object, two transports:

| transport | for | how |
|---|---|---|
| **HTTP** (`POST {PUBLIC_BASE_URL}/mcp`) | many remote clients at once | stateless Streamable HTTP · `Authorization: Bearer <MCP_TOKEN>` (401 without, 503 if unset) · `X-MemBoy-User: <id>` picks the user (default `mcp:remote`) |
| **stdio** | one local client | `docker compose exec -T -e MEMBOY_MCP_USER=web:alice app python -m app.mcp_server` — the repo's `.mcp.json` does this for Claude Code |

Connect a remote client (Claude Code example; Claude Desktop/claude.ai connectors take the same URL + header):

```bash
claude mcp add --transport http memboy https://memboy.ohmpire.dev/mcp -H "Authorization: Bearer <MCP_TOKEN>" -H "X-MemBoy-User: mcp:demo"
```

Test without an LLM: `docker compose exec -T app python -m tests.test_mcp` — real stdio and HTTP clients: tool list,
per-user scoping through both transports, actionable errors, upload, 401 without token.
The public URL is permanent: `https://memboy.ohmpire.dev` (Cloudflare named tunnel, see below).

## Public URL: Cloudflare named tunnel (permanent)

`https://memboy.ohmpire.dev` → Cloudflare tunnel `ohmpire` → **`cloudflared` runs inside this compose stack**
(`Dockerfile.cloudflared`, token = `TUNNEL_TOKEN` in `.env`, `--protocol http2` because UDP/QUIC does not leave the
Docker VM here) → `http://memboy-app-1:8080` on the compose network. Routes/DNS live in the Cloudflare dashboard
(Networking → Tunnels → ohmpire → Routes); nothing tunnel-related is configured locally besides the token.

Rules for routes on this tunnel (learned the hard way):
- Origin for memboy is the **container name** `memboy-app-1:8080`, not `app:8080` — the cloudflared container also joins the
  sibling project's network where `app` resolves to a different container.
- Anything published on a **host port** (other projects) uses `http://host.docker.internal:<port>`, never `127.0.0.1`
  (127.0.0.1 inside the cloudflared container is the container itself).
- Why not the `cloudflared` Windows service + `127.0.0.1:8080`: Docker Desktop's host port-forward for a container dies
  every hour or so while the container stays Up → 502. Inside the compose network there is no port-forward to die.
  If a host-port route 502s, `docker compose up -d --force-recreate <that service>` in that project rebinds it.

## Security (what stops strangers from using memboy.ohmpire.dev)

| surface | control |
|---|---|
| `/webhook` | LINE signature (HMAC-SHA256 with the channel secret) verified before anything is read; anything else → 403 |
| `/files/*`, `/uploads/*` | no static mount: every link the bot sends is **signed + expiring** (`?e=<exp>&s=<hmac>`, 7 days); unsigned/expired/tampered → 403, path traversal → 400; the browser UI reaches them via its login cookie |
| `/mcp` | bearer `MCP_TOKEN` (401 without, 503 if unset) + `X-MemBoy-User` scoping; every tool re-checks ownership |
| `/` chat UI | per-tester password → HMAC cookie, per-user rate limit |
| host | port 8080 bound to `127.0.0.1` only — the tunnel reaches the app on the compose network, nothing is reachable from the LAN |
| tunnel | outbound-only; no inbound port, no public IP; Cloudflare terminates TLS |
| secrets | `.env` is git-ignored; rotate `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY`, `MCP_TOKEN` before hand-in |

Optional extras: Cloudflare WAF rate-limit rule on `/webhook` and `/mcp`; Cloudflare Access (email OTP) in front of `/` if the chat UI stays up.
