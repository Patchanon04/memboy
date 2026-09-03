# PBook — แผนพัฒนา LINE Bot (สโคปหลักตาม proposal)

> ผู้ช่วยจัดการใบเสร็จและรายงานค่าใช้จ่ายผ่าน LINE — Agentic AI Application
> อัปเดต: 2026-08-25


## สถานะ (อัปเดต 2026-09-03)

| ส่วน | สถานะ | หลักฐาน |
|---|---|---|
| W1 โครง (docker 4 services, PDF ไทย, webhook+queue, DB, git) | ✅ | probe 11 เคส + queue durability test ผ่าน |
| W2 agent loop + tools สายบันทึก + CLI | ✅ live | 11 เทิร์นจริง 0 parse error; stub tests 5 ชุด |
| W3 tools ถามตอบ/โปรไฟล์/รายงาน/CSV/notes/เบิก + LINE wiring | ✅ โค้ด + live บางส่วน | PDF มีกราฟ, CSV, quick reply, flex card, onboarding, rich menu image |
| W3.5 รูปคืน/compare/กราฟ/สลิป+QR/undo/Flex/FX/PDF input/หลายใบ/สรุปสัปดาห์ | ✅ โค้ด | สลิป QR verified/mismatch/dup-ref live ผ่าน; cron ผ่าน arq |
| W3.6 หารบิล/ค้น item/trends/รายงานอัตโนมัติ/ค้นหลวม/หมวด custom | ✅ โค้ด | tools 19 ตัว |
| W3.7 onboarding + LIFF dashboard | ✅ โค้ด | /dashboard + /api/dashboard (dev uid mode ผ่าน) |
| W4 eval A/B/C/D runners + เคส 48 + สลิป 30 | ✅ script | ผลรันดูใน eval/logs |
| **ค้าง** | LINE credentials จริง (webhook ผ่านมือถือ, rich menu upload, LIFF id), Eval A ทั้ง 2 โมเดล, Eval B, สไลด์/video (งานเพื่อน) | |

## การตัดสินใจที่ปิดแล้ว (พร้อมเหตุผล)

| เรื่อง | ตัดสินใจ | เหตุผล |
|---|---|---|
| LLM | **Gemma 4** (ผ่าน Gemini API) — default `gemma-4-26b-a4b-it`, เทียบกับ `gemma-4-31b-it` ใน W2 | open source ตามธีมโปรเจกต์; eval 200 ใบ (คละโหด): ถูกครบ 5 field 95.5% หลังจูน prompt v3, 26b เร็วกว่า/timeout น้อยกว่า/แม่นเท่า 31b; free tier |
| Tool calling | **ทำเองผ่าน prompt** — Gemma ไม่มี native function calling: system prompt นิยาม tools + สั่งตอบ `{"tool": ..., "args": ...}` → parse → execute → ยัดผลกลับ → วน | จุดขายกับอาจารย์: agentic ทั้งระบบเขียนเองจริง ไม่พึ่ง FC ของ platform; eval ยืนยันแล้วว่า Gemma ตาม JSON format ได้ดี |
| Agent loop | เขียนเอง (while + parse + dispatch) | เกณฑ์คะแนน Implementation |
| DB | PostgreSQL + SQLAlchemy | JSONB เก็บ items, query สรุปยอด |
| ไฟล์รูป/PDF | disk ผ่าน docker volume, DB เก็บ path | ตาม proposal |
| PDF | WeasyPrint + Jinja2 HTML template | template ภาษาไทยง่าย; ส่งเข้า LINE เป็นลิงก์ (LINE ไม่รับไฟล์ PDF ตรง) |
| Deploy | docker-compose 4 services (app + worker + redis + postgres); dev ผ่าน cloudflared tunnel | worker แยกตามมติ queue |
| งานช้า | **queue**: webhook ack 200 ทันที → enqueue ลง Redis (arq) → worker container แยกประมวล → push ผลกลับ | LLM 5-20 วิ/เทิร์น ถือ connection ไม่ได้; งานทนตาย (restart แล้วทำต่อ), retry อยู่ฝั่งเรา; ⚠️ ต่างจากดราฟอีเมล ("โปรเซสเดียว") — แจ้งอาจารย์ว่าอัปเกรดเพื่อ reliability |

## สถาปัตยกรรม

```
LINE OA ── webhook ──> FastAPI ──> agent loop (Gemma 4 + JSON tool calling ที่เขียนเอง)
                                      │  เลือก tool เองทุกเหตุการณ์ (text และ image เข้า loop ทางเดียวกัน)
                                      ▼
                    tools ──> PostgreSQL + /data (รูปบิล, PDF)
                                      │
                    ผลลัพธ์/ลิงก์ PDF ◄─ push message กลับ LINE
```

## โครง repo

```
pbook/
├── docker-compose.yml          # app + postgres, volume ./data:/data
├── Dockerfile                  # python:3.11-slim + weasyprint deps + ฟอนต์ Sarabun
├── .env.example                # LINE_CHANNEL_SECRET/TOKEN, GEMINI_API_KEY, DATABASE_URL
├── app/
│   ├── main.py                 # FastAPI: /webhook, /files/{id}.pdf, /health
│   ├── agent.py                # agent loop: history + parse JSON tool call + dispatch (เขียนเอง)
│   ├── tools.py                # tool functions ทั้งหมด (ฟังก์ชันเพียวๆ เทสได้ตรงๆ)
│   ├── db.py                   # SQLAlchemy models + session
│   ├── line_io.py              # verify signature, ดึงรูปจาก content API, push/reply
│   ├── report.py               # Jinja2 → WeasyPrint → /data/reports/{uuid}.pdf
│   └── templates/report.html
├── chat_cli.py                 # คุยกับ agent ตรงๆ ไม่ผ่าน LINE (dev 90% อยู่นี่ + เก็บ log ส่งอาจารย์)
├── eval/                       # ย้ายจาก chat-test: receipts/, labels.json, eval_receipts.py
└── tests/test_tools.py         # เทส tool functions กับ DB จริงใน compose
```

## DB schema

```sql
users         (id, line_user_id UNIQUE, active_profile_id)
profiles      (id, user_id FK, name)
invoices      (id, profile_id FK, status draft|confirmed, image_path,
               doc_type receipt|transfer_slip, transfer_ref, payee,   -- สลิปโอน
               qr_status verified|mismatch|unverified,                -- QR consistency check
               vendor, invoice_date, subtotal, vat, total, category,
               currency DEFAULT 'THB', fx_rate, total_thb,          -- บิลต่างประเทศ
               reimbursed_at NULL,                                   -- สถานะเบิก
               items JSONB, raw_llm JSONB, created_at, deleted_at)
conversations (id, user_id FK, role, content JSONB, created_at)   -- history ~30 ข้อความล่าสุดเข้า loop
notes         (id, user_id FK, text, created_at)                  -- ความจำระยะยาว (remember_note)
categories    (id, user_id FK, name UNIQUE per user)              -- หมวด custom (default 6 อยู่ในโค้ด)
```

## Tools (ตาม proposal + สิ่งที่เรียนรู้จาก prototype)

1. `analyze_receipt(image_id)` — vision สกัด + จัดหมวด; ใช้กติกาวันที่ **เวอร์ชัน v3 ที่พิสูจน์แล้ว**: *เรียง วัน/เดือน/ปี เสมอ; ปี 4 หลัก >2400 คือ พ.ศ. ลบ 543; ปี 2 หลัก 50–99 คือ พ.ศ. ย่อ (25YY−543 เช่น 69→2026), 00–49 คือ ค.ศ. 20YY* — A/B บน 200 ใบ: date 87%→96% (และบทเรียน v2: กติกา "YY=20YY" ที่เขียนผิดทำแย่ลงเหลือ 76% — ห้าม copy เวอร์ชันผิด) + นิยามหมวด (ซูเปอร์ฯ=ของใช้)
2. `save_invoice(draft_id)` — บันทึกได้เฉพาะ draft ที่มีอยู่ → กันบันทึกซ้ำที่ตัว tool ไม่ใช่ prompt
3. `update_invoice(id, fields)` / `delete_invoice(id)`
4. `manage_profile(action, name)` — create/switch/list
5. `find_invoices(filters)` — ช่วงวันที่/ร้าน/หมวด
6. `summarize_expenses(filters)` — ยอดรวม/แยกหมวด/VAT
7. `check_duplicate(vendor, date, total)`
8. `generate_report(profile, period)` — PDF → คืนลิงก์
9. `remember_note(action, text)` — จำ/ลืม/ดู ข้อมูลระยะยาวของ user (ชื่อเล่น, งบต่อเดือน, กติกาเบิกของบริษัท) — save/list/delete ลงตาราง notes; notes ทั้งหมดถูกแนบเข้า system prompt ทุกเทิร์น (ของ user คนนั้น จำนวนน้อย ไม่ drown)
10. `mark_reimbursed(invoice_ids, undo?)` — ติ๊กว่าเบิกแล้ว/ยกเลิก; tools 5,6,8 รับ filter `reimbursed: true|false` ด้วย
11. `convert_currency(amount, currency, date)` — บิลต่างประเทศ: แปลงเป็น THB ด้วย rate ณ วันที่ในบิล ผ่าน frankfurter.app (ฟรี ไม่ต้องมี key, มี rate ย้อนหลัง) — โค้ดเป็นคน call ไม่ใช่โมเดลเดา rate; เก็บ currency/fx_rate/total_thb ในบิล; ยอดสรุปใช้ total_thb เสมอ
12. `export_csv(profile, period, filters)` — CSV รายบิล (วันที่, ร้าน, หมวด, ยอด, VAT, สถานะเบิก) ลง /data/reports → คืนลิงก์ เอาไปกรอกระบบเบิกบริษัทต่อ — reuse โครง generate_report ทั้งหมด แค่เปลี่ยน renderer
13. `get_invoice_image(invoice_id)` — ส่ง*รูปจริง*ของบิลกลับเข้าแชท (LINE image message จากไฟล์ใน /data) — "ขอดูบิลโรงแรมเชียงใหม่"
14. `manage_category(action, name)` — หมวดหมู่ custom ต่อ user: add/remove/rename/list ("เพิ่มหมวดค่าเลี้ยงลูกค้า") — หมวด default 6 ตัวลบไม่ได้; หมวดของ user ถูก inject เข้า prompt ของ analyze_receipt แบบ dynamic; cap 20 หมวด/คน กัน prompt บวม; ลบหมวดแล้วบิลเก่าคงค่าเดิมไว้ (agent ชวนย้ายหมวดให้); eval หมวดหมู่วัดกับ default 6 เท่านั้น

**ขยาย tool เดิม (ไม่ใช่ tool ใหม่):**
- `summarize_expenses` รับ `compare_to` — "เดือนนี้เทียบเดือนที่แล้ว" → SQL สองช่วง + ผลต่าง%
- `analyze_receipt` รองรับ **สลิปโอนเงิน** เป็น doc_type ที่สอง (ดูหัวข้อสลิปด้านล่าง) และรับ **ไฟล์ PDF** (e-Tax invoice): LINE file event → pdf2image หน้าแรก → pipeline เดิม
- **Undo** — "ยกเลิกอันเมื่อกี้" ไม่มี tool ใหม่: agent เห็น action ล่าสุดใน history แล้วเรียก delete/update ที่มีอยู่ (soft delete ทำให้ปลอดภัย)
- **Flex Message summary card** — ผลจาก summarize ส่งเป็นการ์ด (ยอดรวม, แยกหมวด, ปุ่ม "ขอ PDF/CSV") แทน text ล้วน — renderer ฝั่ง line_io ไม่แตะ agent

**สลิปโอนเงินทุกธนาคาร (deep):**
- `doc_type: receipt | transfer_slip`; สลิปสกัด ธนาคาร, ผู้โอน/ผู้รับ, วันเวลา, จำนวนเงิน, **เลขอ้างอิง (ref)**
- dedupe สลิปใช้ ref เป็นหลัก (แม่นกว่า vendor+date+total ของใบเสร็จ)
- **ข้อกำหนดอาจารย์: ห้ามข้อมูลส่วนตัว** → สลิปทั้งหมด generate เอง (ชื่อ/เลขบัญชี/แบงก์สมมติ เลียนโครง layout จริง ~6 แบบ แต่ไม่ใช้โลโก้-ชื่อแบงก์จริง) — "deep" = พิสูจน์ด้วย eval ความหลากหลาย layout ใน W4
- **QR consistency verification** — generator ฝัง mini-QR (ref+ยอด) ลงสลิปปลอม; ตอนรับสลิป โค้ด decode QR ด้วย pyzbar (deterministic) เทียบกับที่ LLM อ่านจากตัวหนังสือ: ตรง → บันทึก flag verified ✓ (โชว์ในรีพอร์ท), ไม่ตรง → เตือนและไม่บันทึกจนกว่า user ยืนยัน, ไม่มี/อ่าน QR ไม่ออก → บันทึกเป็น unverified; eval มีเคสจงใจทำ QR ไม่ตรงไว้ทดสอบว่าจับได้ — **เรียกว่า consistency verification ไม่ใช่ตรวจสลิปปลอม** (ยืนยันกับธนาคารจริงต้องใช้ bank API + ข้อมูลจริง อยู่นอกสโคป ห้ามสัญญาในพรีเซนต์)

**ฟีเจอร์ที่ไม่ใช่ tool ใหม่:**
- **Budget alert** — งบอยู่ใน notes + agent เห็นยอดสะสมจาก summarize → เตือนเองเมื่อใกล้เกิน (พฤติกรรมจาก system prompt ไม่มี if ในโค้ด — เคสโชว์ agentic ชั้นดี)
- **Quick reply ปุ่มยืนยัน** — draft confirm ส่งปุ่ม ✅บันทึก/✏️แก้/🗑️ทิ้ง (LINE quick reply; การกดปุ่ม = ส่ง text เข้า loop ตามปกติ)
- **Validate เลขผู้เสียภาษี 13 หลัก** — checksum ในโค้ดหลัง analyze; ผิด = อ่านเลขพลาด ตีกลับ
- **บิลหลายใบในรูปเดียว** — `analyze_receipt` คืน array → สร้างหลาย draft, confirm ทีละใบหรือ "บันทึกทั้งหมด"
- **สรุปรายสัปดาห์** — APScheduler ในโปรเซสเดียวกับ FastAPI push สรุปเย็นวันอาทิตย์ (เอา scheduler กลับเข้า scope)
- **Rich Menu** — เมนูลัดใต้ช่องแชท (สรุปเดือนนี้ / ขอรีพอร์ท / สลับโปรไฟล์ / ขอ CSV / วิธีใช้) — ปุ่มแค่ส่ง text สำเร็จรูปเข้า loop ไม่มี logic พิเศษ; ตั้งผ่าน LINE API ครั้งเดียว + รูปเมนู 1 รูป

## แผนรายสัปดาห์ (เกณฑ์จบต่อสัปดาห์ต้องรันโชว์ได้จริง)

**W1 — โครงถึงก้นบึ้ง (เสี่ยงสุดทำก่อน)**
- `git init` + push ขึ้น GitHub ตั้งแต่ commit แรก (โค้ดคือของส่งมอบหลัก 35% — อย่าให้อยู่แค่ในเครื่องเดียว)
- docker-compose ขึ้น, Dockerfile render PDF ภาษาไทยได้ 1 หน้า (กันตาย WeasyPrint+ฟอนต์ตั้งแต่วันแรก)
- LINE OA + webhook echo ผ่าน tunnel, ดึงรูปจาก content API ลง /data ได้
- DB schema + migration
- ✅ จบเมื่อ: ส่งรูปใน LINE แล้วไฟล์โผล่ใน /data และ `curl /files/test.pdf` ได้ PDF ไทย

**W2 — agent loop + เส้นทางบันทึก**
- `chat_cli.py` ก่อน แล้วค่อยต่อ webhook
- loop: history → Gemma → parse JSON tool call → dispatch → ยัด result กลับ → วนจนได้ text ตอบ; ทุก event เข้า loop ทางเดียว (ไม่มี if image แยก)
- กัน format หลุด: validate JSON ด้วย pydantic; parse ไม่ผ่าน → ส่ง error กลับให้โมเดลแก้เอง (สูงสุด 2 ครั้ง) แล้วค่อย fallback เป็นตอบ text; กรอง thought parts ออกก่อน parse
- **Eval A: tool-selection benchmark (~40 เคส)** — เคส = ข้อความ+context → tool+args ที่คาดหวัง, รันผ่าน chat_cli แบบ batch, เทียบอัตโนมัติ → ใช้ตัดสิน 26b-a4b vs 31b อย่างเป็นทางการ แล้วล็อกตัว default (เคสสร้างครั้งเดียว ใช้เป็น regression ทุกครั้งที่แก้ prompt)
- tools 1,2,3,7 + confirm flow (draft → ยืนยัน → confirmed)
- ✅ จบเมื่อ: ใน CLI ส่งรูป → agent วิเคราะห์ → ถามยืนยัน → "บันทึกเลย" → อยู่ใน DB; รูปแมว → agent ปฏิเสธเอง

**W3 — ถามตอบ + รายงาน + ขึ้น LINE จริง**
- tools 4,5,6,8,9,10,12 + template รายงาน (สรุปยอด, แยกหมวด, ตาราง, ลายเซ็นช่องเบิก)
- ฟีเจอร์ชั้นถูก: quick reply ปุ่มยืนยัน, budget alert (system prompt), validate เลขภาษี, สถานะเบิกใน report, export CSV, Rich Menu
- ต่อ loop เข้า webhook + push message + ส่งลิงก์ PDF
- ✅ จบเมื่อ: demo ครบใน LINE จริง: ส่งบิล→กดปุ่มบันทึก→ถามยอด→ขอรีพอร์ทใบที่ยังไม่เบิก→เปิด PDF ได้

**W3.5 — ฟีเจอร์ชั้น stretch (ทำตามลำดับนี้ ตัดจากท้ายได้โดย core ไม่พัง)**
1. `get_invoice_image` ขอรูปบิลคืน + `compare_to` เทียบช่วงเวลา (ถูกสุด เอาขึ้นก่อน)
2. กราฟใน PDF (matplotlib pie แยกหมวด + bar รายเดือน)
3. สลิปโอนเงิน (doc_type + ref dedupe) — ตัว deep eval ต่อแบงก์ไปทำใน W4
4. Undo + Flex Message summary card
5. `convert_currency` บิลต่างประเทศ (frankfurter.app)
6. รับไฟล์ PDF (e-Tax → pdf2image)
7. บิลหลายใบในรูปเดียว (หลาย draft)
8. สรุปรายสัปดาห์ผ่าน APScheduler

**W3.6 — ฟีเจอร์ชั้นสอง (unlock หลัง W3.5 หรือเมื่อ core นิ่ง — ส่วนใหญ่คือ tool ใหม่ + SQL บนฐานเดิม)**
1. **หารบิล** — "หาร 4" / "ข้าวผัดของโบ๊ท ที่เหลือหารสาม" → agent จับคู่รายการจาก items → โค้ดคำนวณใครจ่ายเท่าไหร่ → การ์ดสรุปแชร์ต่อได้ (โชว์ agentic เด่นสุด)
2. **ถามระดับรายการสินค้า** — "เดือนนี้กินกาแฟกี่แก้ว" → tool ค้น items JSONB
3. **`analyze_trends`** — แนวโน้มรายเดือน, หมวดโตเร็ว, ร้านจ่ายบ่อย → SQL aggregate + LLM เรียบเรียง insight
4. **รายงานอัตโนมัติรายเดือน** — ตั้งต่อโปรไฟล์ "ทุกวันที่ 25 ส่งรีพอร์ท" ผ่าน APScheduler ที่มีอยู่
5. **ค้นหาแบบหลวม** — "ร้านกาแฟแถวมอ" เจอชื่อร้านใกล้เคียง (ILIKE + LLM normalize คำค้น)
6. **หมวดหมู่ custom** — tool 14 `manage_category` (รายละเอียดในหัวข้อ Tools)

**W3.7 — ชั้นสุดท้าย (สโคป FREEZE แล้ว — ห้ามเพิ่มอีกจนกว่า core จะรันได้จริง)**
1. **Onboarding flow** — follow event → แนะนำตัว + ส่งรูปบิลตัวอย่างให้ลองเล่นทันที (ปิดจุดตาย "แอดบอทแล้วไม่รู้จะพิมพ์อะไร" วันพรีเซนต์)
2. **LIFF dashboard** — หน้าเว็บกราฟสรุปเปิดในแอป LINE (ปิด loop กับอีเมล proposal ที่เขียนเรื่อง LIFF ไว้; reuse ทักษะจาก pbook-chat)

⚠️ สโคป **FREEZE** ณ 2026-09-02 — เกิน 4 สัปดาห์จริงประมาณ 2.5 สัปดาห์ ลำดับ unlock ตายตัว: core W1–W3 ต้องรันได้จริงก่อน → W3.5 → W3.6 — เส้นตัดอยู่ระหว่างข้อไหนก็ได้โดย proposal ไม่เสียคำพูด เพราะชั้น stretch ทั้งหมดไม่เคยสัญญากับอาจารย์

**W4 — eval + เก็บของส่ง**
- **Eval ครบ 4 มุม** (extraction จาก W1-3 + อีก 3 ชุดใหม่) — **ข้อกำหนดอาจารย์: ห้ามใช้ข้อมูลส่วนตัว → ทุกใบ generate เอง 100%** (โบนัส: ground truth รู้ตั้งแต่ตอน generate ไม่ต้อง label มือ):
  - *Extraction*: **มีแล้ว 220 ใบ** — ชุด 20 (ทำมือ) + dataset 200 (TH/EN, png/jpg/pdf, clean/photo/camera-sim) พร้อม labels อัตโนมัติ + ผล 3 prompt versions; ทีม design สถานการณ์เพิ่มลง pool ได้เรื่อยๆ
  - *Extraction ชุด photo*: **พิมพ์ใบ generate ลงกระดาษแล้วถ่ายมือถือ ≥20 ใบ** หลายสภาพ (ยับ, เอียง, แสงน้อย, เงา, ถ่ายจอ) → วัด gap ระหว่าง clean กับ photo — คือคำตอบของคำถาม "ของจริงจะแม่นแค่ไหน" โดยไม่แตะข้อมูลจริง
  - *สลิปโอน (ถ้าทำ W3.5)*: generate สลิปสไตล์ layout ต่างกัน ~6 แบบด้วยชื่อธนาคาร/บุคคล/เลขบัญชีสมมติทั้งหมด (เลียนโครง layout ไม่ใช้โลโก้/ชื่อแบงก์จริง) → layout-diversity accuracy
  - *Eval B — end-to-end scenario (~10 เคส multi-turn)*: สคริปต์บทสนทนาเต็ม (ส่งรูป→ระบุโปรไฟล์→ยืนยัน→ถามยอด) แล้ว **assert สถานะ DB** ไม่ใช่ข้อความตอบ → task success rate
  - *Eval C — metrics จาก turn log (ฟรี)*: % tool call ที่ parse JSON ผ่านรอบแรก (วัดความเสี่ยงหลักของ prompt-based FC), tool calls เฉลี่ย/เทิร์น, อัตราชน loop cap — script อ่าน JSONL ~30 บรรทัด
  - *Eval D — adversarial (~8 เคส)*: รูปที่ไม่ใช่บิล→ปฏิเสธ, prompt injection ฝังในบิล→เป็น data, "ลบบิล" ไม่มี context→ถามกลับ, บิลซ้ำ→เตือน — ผูกกับ guardrails ที่ประกาศไว้ทุกข้อ
- เก็บ conversation log จาก CLI (เคส agentic: เลือก tool ตามบริบท, ถามกลับเมื่อกำกวม, แก้ข้อมูลจากแชท, ปฏิเสธรูปที่ไม่ใช่บิล)
- สไลด์ + ซ้อม demo (มีแผนสำรอง: video บันทึกไว้กัน demo สดพัง)

## Harness: guardrails + determinism

หลักการ: อะไรที่ผิดแล้วเจ็บ (เงิน, ข้อมูลคนอื่น, ลบของ) ต้องถูกบังคับด้วย**โค้ด** ไม่ใช่ prompt — prompt เป็นแค่คำขอ โค้ดคือกติกา

**Guardrails (บังคับใน W2 พร้อม loop)**
1. **User scoping ที่ระดับ tool** — ทุก tool รับ `user_id` จาก webhook/session เท่านั้น ไม่รับจาก args ที่โมเดลสร้าง → โมเดลเข้าถึงข้ามคนไม่ได้โดยโครงสร้าง ไม่ใช่โดยมารยาท
2. **Loop cap** — จำกัด tool call สูงสุด 6 ครั้ง/เทิร์น เกินแล้วตัดจบพร้อมข้อความบอก user → กัน loop วนไม่รู้จบเผาโควต้า
3. **Validate args ที่ปาก tool** — pydantic ทุก tool: ยอดเงิน ≥ 0, วันที่ parse ได้, profile ต้องมีจริง; ไม่ผ่าน → คืน error ให้โมเดลแก้ (ไม่ execute)
4. **ลบ = soft delete** — `deleted_at` ไม่ลบจริง; ทำผิดกู้ได้, demo พังยาก
5. **Prompt injection ผ่านรูปบิล** — บิลอาจมีข้อความสั่งโมเดล ("ignore instructions...") → `analyze_receipt` บังคับ output เป็น JSON schema เท่านั้น ข้อความในบิล = data ไม่ใช่คำสั่ง (จุดนี้เล่าในพรีเซนต์ได้ อาจารย์ NLP ชอบ)
6. **Error ไม่รั่วถึง user** — exception ใน tool → log เต็ม + ตอบ user สั้นๆ สุภาพ ไม่โชว์ stack trace/SQL
7. **Rate limit ต่อ user** — เกิน ~10 เทิร์น/นาที → ตอบ "รอสักครู่" โดยไม่เรียก LLM — กัน spam เผาโควต้า (in-memory dict พอ)
8. **Resize รูปก่อนส่ง LLM** — ย่อ ≤1280px JPEG (โค้ดมีแล้วจาก prototype) — คุม payload/โควต้า/ความเร็ว

**Determinism (ของฟรีถ้าทำแต่แรก)**
1. **`temperature: 0`** ทุก call — ทั้งสกัดบิลและเลือก tool ให้ผลซ้ำได้ ใกล้ deterministic ที่สุดที่ LLM ให้ได้
2. **เลขเงินห้าม LLM คำนวณ** — ยอดรวม/สรุปมาจาก SQL เสมอ; หลังสกัดบิล โค้ดเช็ค `subtotal + vat ≈ total` ไม่ตรง → ตีกลับให้ดูใหม่หรือถาม user
3. **Webhook idempotency** — LINE ส่ง event ซ้ำได้เมื่อ retry → เก็บ `message_id` ที่ประมวลแล้ว เจอซ้ำข้ามเงียบๆ กันบิลถูกบันทึกสองรอบแบบไม่มีใครสั่ง
4. **State machine ของบิลอยู่ใน DB** — draft → confirmed บังคับที่ tool (`save_invoice` ทำงานเฉพาะ draft) ผลเหมือนกันเสมอไม่ว่าโมเดลจะเพี้ยนยังไง
5. **Turn log เป็น JSONL** — ทุกเทิร์นเก็บ input/tool calls/results ลงไฟล์ → ได้ทั้ง debug, conversation log ที่ต้องส่ง, และ regression: แก้ prompt แล้วรัน eval + replay เคสเดิมเทียบได้
6. **Pin ทุกอย่างที่ pin ได้** — ชื่อโมเดลระบุรุ่นเต็ม, prompt อยู่ใน git, ผล eval ผูกกับ commit → ตอบได้เสมอว่า "ตัวเลขนี้มาจากโค้ดเวอร์ชันไหน"
7. **วันเวลาปัจจุบันมาจากโค้ด** — inject วันที่วันนี้ (Asia/Bangkok) เข้า system prompt ทุกเทิร์น — ไม่งั้น "เดือนนี้/เมื่อวาน" โมเดลจะเดาจาก training data; TZ pin ที่ container
8. **Serialize ต่อ user** — per-user lock ใน worker (arq ไม่การันตีลำดับเอง): ข้อความจากคนเดียวกันประมวลตามลำดับ — กัน draft race ตอนรัวรูปหลายใบ (คนละ user ยังขนานกันได้)

**ไม่ทำ (เกินสโคป term project)** — LLM-as-judge ตรวจคำตอบ, moderation layer แยก, observability platform (Langfuse ฯลฯ), circuit breaker — JSONL log + eval script ทำหน้าที่เดียวกันในสเกลนี้ (queue: ตัดสินใจใหม่ → ใช้ Redis+arq)

## ความเสี่ยงที่รู้แล้ว + ทางแก้

| ความเสี่ยง | แก้ |
|---|---|
| WeasyPrint + ฟอนต์ไทยใน docker | ทำ W1 วันแรก ไม่ใช่ W3 |
| iterate ผ่าน LINE ช้า | dev ใน chat_cli.py, LINE เป็นแค่ transport |
| Gemini API 503/429 | retry 2-3 ครั้ง (โค้ดมีแล้วใน prototype) |
| Gemma หลุด JSON format ใน tool call | validate + ให้โมเดลแก้เอง 2 รอบ; ถ้าอัตราหลุดสูงจนใช้ไม่ได้ (วัดใน W2) ค่อยพิจารณาเปลี่ยนโมเดล — รู้เร็วตั้งแต่สัปดาห์ 2 ไม่ใช่กลางเทอม |
| Gemma thought parts ปนใน output | กรอง `thought: true` ออกก่อน parse (โค้ดมีแล้ว) |
| วันที่ปี 2 หลัก | ปิดแล้ว — กติกา v3 พิสูจน์บน 200 ใบ (date 96%, พลาดที่เหลือคือภาพเบลอซึ่ง confirm flow ดักไว้) |
| agent บันทึกซ้ำ/มั่ว | บังคับที่ tool (draft state ใน DB) ไม่พึ่ง prompt |
| free tier rate limit / โมเดลล่มตอน demo | สลับ 26b↔31b ได้ทันที (ทั้งคู่คือ Gemma 4, prompt เดียวกัน); เติม billing ขั้นต่ำกันเหนียว; และมี video demo สำรองอยู่แล้ว |
| frankfurter.app ล่ม/ไม่มีสกุลนั้น | cache rate ที่เคยดึงลง DB; ไม่ได้จริงๆ เก็บบิลเป็นสกุลเดิม + ติด flag ให้ user ใส่ rate เอง |
| บิลหลายใบ → confirm กำกวม | draft มี id สั้น (#1 #2 #3) ให้ user อ้างถึงรายใบ; "บันทึกทั้งหมด" ต้องผ่าน check_duplicate รายใบ |
| สโคปบวม (stretch W3.5×8 + W3.6×6) | W1–W3 core ห้ามเลื่อน; ตัด stretch จากท้ายได้ทุกเมื่อ ไม่กระทบ proposal ที่สัญญาไว้ |

## การแบ่งงาน (ทีม 3 คน — 2 คนไม่เขียนโค้ด)

> ข้อมูลทุกชิ้น generate เอง ไม่มีข้อมูลส่วนตัว ตามข้อกำหนดอาจารย์

**คนเขียนโค้ด (เรา)** — ระบบทั้งหมดตาม W1–W4 + เครื่องมือให้เพื่อน 2 ชิ้น: converter Google Sheet → ไฟล์ที่ generator/eval ใช้, และ `run_eval.py` คำสั่งเดียวจบ

**คนที่ 1 — Data & Evaluation Lead**
- W1: ออกแบบ "สถานการณ์บิล" ~40 แบบลง Sheet (ชื่อร้านสมมติ, รายการ, ราคา, รูปแบบบิล, ภาษา) → เราป้อนเข้า generator; ออกแบบสลิปสมมติ 6 layout
- W1–W2: **พิมพ์ใบ generate แล้วถ่ายมือถือ** ≥20 ใบ หลายสภาพ (ยับ/เอียง/แสงน้อย/เงา/ถ่ายจากจอ) + จดว่ารูปไหนคือใบไหน
- W2–W3: เขียนเคส Eval A 40 เคส, Eval B 10 บทสนทนา, Eval D 8 เคสแกล้งบอท (งานออกแบบภาษา ไม่ใช่โค้ด)
- W4: รัน `run_eval.py`, อ่านผล, เขียน error analysis สำหรับรายงาน
- ตอบคำถามอาจารย์เรื่อง: methodology การ eval, ตัวเลขทุกตัวในรายงาน

**คนที่ 2 — Product & Presentation Lead**
- W1: สร้าง LINE OA + Messaging API (ทำตามคู่มือ ไม่ใช่โค้ด), ร่างรูป Rich Menu ใน Canva
- W2–W3: QA ผ่าน LINE จริงตาม test script + พยายามพังบอท → จดบั๊ก+screenshot ลง Sheet; คัด conversation log ที่จะส่งอาจารย์; mockup หน้าตา PDF report + การ์ด Flex ใน Canva (เราแปลงเป็น template); กำหนดสำนวน/บุคลิกบอท
- W4: สไลด์, สคริปต์ demo, อัด+ตัด video สำรอง, จัดคิวซ้อมพรีเซนต์
- ตอบคำถามอาจารย์เรื่อง: user flow, ฟีเจอร์, การออกแบบประสบการณ์ใช้งาน

**กติการ่วม:** ทุกคนอธิบาย architecture ภาพรวมได้ (ทำไม agentic / guardrails คืออะไร) — ซ้อมถาม-ตอบกันเองก่อนพรีเซนต์ 1 รอบ; งานเพื่อนเริ่ม W1 ได้เลยไม่ต้องรอระบบ (เขียนเคสจากสเปค)

## ของที่มีอยู่แล้ว (จาก chat-test) เอาไปใช้ต่อ

- `receipts/` 20 + `receipts_hard/` 20 + `dataset/` 200 (TH/EN, png/jpg/pdf, 3 ระดับความยาก) + labels + `make_receipts.py`/`make_hard.py`/`make_dataset.py`/`eval_receipts.py` + ผล eval 3 เวอร์ชัน (`eval_results_baseline/v2/v3.json`) → ย้ายเข้า `eval/`
- โค้ด retry Gemini, การกรอง thought parts, resize รูปก่อนส่ง
- ความรู้: LINE ส่ง PDF ตรงไม่ได้, reply token สั้น, claude.CMD/newline บน Windows
