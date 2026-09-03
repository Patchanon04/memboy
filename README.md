# PBook — ผู้ช่วยจัดการใบเสร็จและรายงานค่าใช้จ่ายผ่าน LINE

Agentic AI Application (KMITL NLP Final Project) — agent loop + JSON tool calling เขียนเองบน Gemma 4

- แผนงานเต็ม: [PLAN.md](PLAN.md) · คู่มือทีม: [TEAM_GUIDE.md](TEAM_GUIDE.md)
- รัน: `cp .env.example .env` (ใส่ key) → `docker compose up --build`
- เช็ค: `curl localhost:8080/health` · PDF ไทย: `localhost:8080/files/test.pdf`
- eval assets + dataset 220 ใบ: `eval/`

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

## ผล eval ล่าสุด (ดู `eval/logs/EVAL_REPORT.md`)

| ชุด | ผล |
|---|---|
| Extraction (200 ใบ TH/EN, png/jpg/pdf, clean/photo/camera) | ถูกครบ 5 field 95.5% (date 96%) หลัง prompt v3 |
| Eval A/D tool-selection 48 เคส | gemma-4-26b-a4b-it 48/48 · gemma-4-31b-it 47/48 |
| Eval B end-to-end 10 scenario (assert DB) | 9/10 → 10/10 หลังเพิ่ม month_total hint |
| Eval C loop metrics (298 LLM calls) | JSON first-try 98.3%, loop-cap 0 |
| สลิปโอน 30 ใบ (6 layout, 5 QR mismatch) | doc_type/total/ref/qr_status 100%, mismatch detection 5/5 |
