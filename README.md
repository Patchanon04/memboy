# PBook — ผู้ช่วยจัดการใบเสร็จและรายงานค่าใช้จ่ายผ่าน LINE

Agentic AI Application (KMITL NLP Final Project) — agent loop + JSON tool calling เขียนเองบน Gemma 4

- แผนงานเต็ม: [PLAN.md](PLAN.md) · คู่มือทีม: [TEAM_GUIDE.md](TEAM_GUIDE.md)
- รัน: `cp .env.example .env` (ใส่ key) → `docker compose up --build`
- เช็ค: `curl localhost:8080/health` · PDF ไทย: `localhost:8080/files/test.pdf`
- eval assets + dataset 220 ใบ: `eval/`

## ทดสอบผ่านหน้าเว็บ (ไม่ต้องใช้ LINE)

หน้าเว็บใช้ **agent ตัวเดียวกับ LINE** ทุกอย่าง (tools/DB/PDF/quick reply) ต่างแค่ transport

```bash
docker compose up -d                                   # เปิดระบบ
# เปิด http://localhost:8080 -> login (ชื่อผู้ใช้อะไรก็ได้ + WEB_PASSWORD ใน .env)

python scripts/dns_pin.py && docker compose up -d       # ถ้า LLM error เรื่อง DNS (WARP)
cloudflared tunnel --url http://localhost:8080          # ให้เพื่อนเข้าทดสอบจากที่อื่น
# เอา URL ที่ได้ไปใส่ PUBLIC_BASE_URL ใน .env แล้ว docker compose up -d ซ้ำ (ลิงก์ PDF ในข้อความจะได้ถูก)
```

ข้อมูลแยกตามชื่อผู้ใช้ที่ล็อกอิน (`web:<username>`) — เพื่อนหลายคนเทสพร้อมกันได้โดยบิลไม่ปนกัน

## คำสั่งที่ใช้บ่อย

```bash
docker compose up -d --build                                   # app + worker + redis + postgres
docker compose run --rm app python -m app.cli                  # คุยกับ agent (dev)
docker compose run -T --rm app python -m app.cli --user u1 --img /srv/eval/receipts/02_coffee.png
docker compose run -T --rm app python -m tests.test_w2         # stub tests (ไม่ใช้โควต้า LLM)
docker compose run -T --rm app python -m eval.eval_tools       # Eval A/D tool-selection (48 เคส)
docker compose run -T --rm app python -m eval.eval_scenarios   # Eval B end-to-end (10 scenario, assert DB)
docker compose run -T --rm app python -m eval.metrics          # Eval C จาก turn log
```

Dashboard (dev): `http://localhost:8080/dashboard?uid=<user>` · LIFF: ตั้ง `LIFF_ID` + `LINE_LOGIN_CHANNEL_ID` ใน .env
Rich menu: `python scripts/make_rich_menu.py` แล้ว `await line_io.setup_rich_menu("eval/assets/rich_menu.png")` เมื่อมี token

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
