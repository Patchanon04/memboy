# MemBoy — ผู้ช่วยจัดการใบเสร็จและรายงานค่าใช้จ่ายผ่าน LINE

Agentic AI Application (KMITL NLP Final Project) — agent loop + JSON tool calling เขียนเอง ไม่ใช้ framework
โมเดล: **Gemma 4 12B บน Ollama ในเครื่อง** เรียกผ่าน `/v1/chat/completions` (API endpoint standard ของ OpenAI)

- แผนงานเต็ม: [PLAN.md](PLAN.md) · คู่มือทีม: [TEAM_GUIDE.md](TEAM_GUIDE.md)
- ผลการทดลอง: `eval/logs/` (ตารางสรุปด้านล่าง) · ข้อมูลทั้งหมดสังเคราะห์ ไม่มีข้อมูลจริงหรือชื่อคนจริง: `eval/`

## สำหรับผู้ตรวจ — รันเองใน 5 นาที (ไม่ต้องมี LINE)

ต้องมี Docker Desktop และ [Ollama](https://ollama.com) บนเครื่อง (การ์ดจอ 12 GB ขึ้นไป หรือรันบน CPU ได้แต่ช้า)

```bash
ollama pull gemma4:12b
cp .env.example .env            # ตั้ง WEB_PASSWORD อะไรก็ได้ (ช่อง LINE_* ปล่อยว่างได้) ค่า LLM_* ใช้ค่าเริ่มต้นได้เลย
docker compose up -d --build    # app + worker + redis + postgres (~3 นาทีครั้งแรก)
curl localhost:8080/health      # {"ok":true,"queue":true}
```

แล้วเปิด <http://localhost:8080> → login ชื่ออะไรก็ได้ → ลากรูปจาก `eval/dataset/` ใส่แชท → พิมพ์ "ยืนยัน" → "สรุปเดือนสิงหา" → "ขอ PDF"
หน้าเว็บใช้ agent ตัวเดียวกับ LINE ทุกบรรทัด (ต่างแค่ transport) — log การตัดสินใจทุกเทิร์นอยู่ที่ `data/logs/turns.jsonl`

**ดูว่าตรงไหนคือ final answer ตรงไหนคือ context จาก tool** (สำหรับรันสดตอนสอบ): ส่งข้อความแล้วรัน
```bash
docker compose exec app python -m scripts.show_turn      # เทิร์นล่าสุด: tool + argument, CONTEXT จาก tool, FINAL ANSWER
```

**เปลี่ยนโมเดล:** server อะไรก็ได้ที่เป็น OpenAI standard แก้แค่ `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` ใน `.env`
(ค่าอื่น: `LLM_KEEP_ALIVE` ให้โมเดลค้างในการ์ดจอ, `LLM_REASONING_EFFORT=none` ปิดโหมดคิดของ gemma4 ที่กิน ~40 วิต่อครั้งโดยคำตอบเท่าเดิม, `LLM_MAX_TOKENS`)

ทดสอบซ้ำได้โดยไม่ใช้ LLM: `docker compose run -T --rm app python -m tests.test_w2` (loop) · `tests.test_w3` (tools) ·
`tests.test_concurrency` (ลำดับ/คิว) · `tests.test_mcp` (MCP) · `eval.eval_layers` (แต่ละชั้นของ harness) — ที่ใช้ LLM: `tests.test_harness` (18 ข้อ) · `sh eval/run_all.sh` (ทุกชุด + ablation)

## ทดสอบผ่านหน้าเว็บ (ไม่ต้องใช้ LINE)

หน้าเว็บใช้ **agent ตัวเดียวกับ LINE** ทุกอย่าง (tools/DB/PDF/quick reply) ต่างแค่ transport

```bash
docker compose up -d                                   # เปิดระบบ
# เปิด http://localhost:8080 -> login (ชื่อผู้ใช้อะไรก็ได้ + WEB_PASSWORD ใน .env)
python scripts/tunnel_watch.py                          # เปิด cloudflare quick tunnel + เฝ้าให้ตลอด + ตั้ง LINE webhook เอง
```

ข้อมูลแยกตามชื่อผู้ใช้ที่ล็อกอิน (`web:<username>`) — เพื่อนหลายคนเทสพร้อมกันได้โดยบิลไม่ปนกัน

## คำสั่งที่ใช้บ่อย

```bash
docker compose up -d --build                                   # app + worker + redis + postgres
docker compose run --rm app python -m app.cli                  # คุยกับ agent (dev)
docker compose run -T --rm app python -m app.cli --user u1 --img /srv/eval/receipts/02_coffee.png
docker compose exec -T app sh eval/run_all.sh                  # วัดผลทุกชุด แล้วต่อด้วย ablation (ผลอยู่ใน eval/logs/run/)
docker compose exec -T app python -m eval.eval_faithfulness    # correctness + faithfulness ของคำตอบ (20 คำถาม)
docker compose exec -T app python -m eval.eval_repeat5         # ถามคำถามเดิม 5 ครั้ง (harness tuning)
docker compose exec -T app python -m eval.eval_layers          # จำลองให้โมเดลทำผิด ดูว่าแต่ละชั้นกันได้ไหม (ไม่ใช้ LLM)
```

Dashboard (dev): `http://localhost:8080/dashboard?uid=<user>` · LIFF: ตั้ง `LIFF_ID` + `LINE_LOGIN_CHANNEL_ID` ใน .env
Rich menu: `python scripts/make_rich_menu.py` แล้ว `docker compose exec -T -e PYTHONPATH=/srv app python scripts/setup_line.py --richmenu /srv/eval/assets/rich_menu.png`

## ทดสอบ harness (guardrails/determinism) รายข้อ

```bash
docker compose run --rm app python -m tests.test_harness   # ตาราง 18 ข้อ + eval/logs/HARNESS_REPORT.md
```

ทุกข้อพิมพ์ "ค่าที่วัดได้จริง" ไม่ใช่แค่ pass/fail

## ผล eval ล่าสุด (Gemma 4 12B, 2026-11-15)

| ชุด | ผล | script → report |
|---|---|---|
| **Extraction — ชุด held-out (100 ใบ ไม่เคยใช้จูน)** | **ถูกครบ 5 field 54/100** (95% CI 44–63) · vendor 86% · date 76% · total 91% · VAT 81% · category 82% | `eval_receipts.py` (`EVAL_DIR=dataset_test`) |
| ภาพใหม่ 60 ใบ (`eval/dataset_blind`) | 28/60 | `eval_receipts.py` |
| ชุดจูน prompt 200 ใบ | 103/200 (date 75%) | `eval_receipts.py` |
| รันซ้ำ held-out (temperature 0) | คำตอบเหมือนเดิมครบ 5 ช่อง **98/100** · date/total/VAT เหมือนเดิม 100/100 | `eval_repeat.py` → `REPEAT.md` |
| **คำตอบของ agent: correctness + faithfulness** (20 คำถามยอดเงิน บิลสังเคราะห์ 10 ใบ) | **20/20** · faithfulness **1.00** (ตัวเลข 77 ตัวมีที่มาใน context ทุกตัว) | `eval_faithfulness.py` → `FAITHFULNESS.md` |
| **ถามคำถามเดิม 5 ครั้ง** (harness tuning) | สาระสำคัญคงเดิม **20/20** · ตัวเลขเหมือนกันทุกครั้ง 19/20 · ตอบถูก 100/100 | `eval_repeat5.py` → `REPEAT5_gemma4-12b.md` |
| tool selection 54 เคส | 47/54 (ที่ผิดส่วนใหญ่เป็นคำสั่งซ้อนที่ทำแค่ครึ่งแรก) | `eval_tools.py` |
| end-to-end 11 scenario (assert DB) | 9/11 (สองข้อที่ตกอ่านยอดบนรูปผิด เช่น 385 แทน 384) | `eval_scenarios.py` |
| คำสั่งที่พิมพ์บนใบเสร็จ (prompt injection) | ข้อมูลไม่เปลี่ยน **5/5** | `eval_injection.py` → `INJECTION.md` |
| รูปที่ไม่ใช่ใบเสร็จ | ไม่รับ **12/12** | `eval_reject.py` |
| JSON ถูกตั้งแต่รอบแรก | 96.1% (259 ครั้ง) | turn log |
| สลิปโอน 30 ใบ 6 layout | ถูกครบ 25/30 · QR ไม่ตรงกับยอด จับได้ **5/5** | `eval_slips.py` |
| ใบเสร็จลายมือสังเคราะห์ 30 ใบ (ฟอนต์ลายมือ ไม่ใช่ลายมือจริง) | ถูกครบ 5 ช่อง 27/30 | `EVAL_DIR=handwritten eval_receipts.py` |
| ชุดตัวอย่างแรก 20 ใบ / แบบยาก 20 ใบ | 8/20 / 4/20 (VAT กับวันที่ผิดบ่อยสุด) | `EVAL_DIR=receipts`, `receipts_hard` |
| บั๊กเดิม ย้อนโค้ดแล้วถามซ้ำ 3 รอบ | ลบกำกวม: ถามกลับ 6/6 · vendor: ตอบถูก 396 ทุกรอบ (ใช้หมวดเรียกรถ) · ไม่มียอดรวม: ตอบแค่ 145 กับ 130 ทุกรอบ | `eval_before_fix.py` → `BEFORE_FIX.md` |
| เวลา ส่งรูปจนได้ draft | ค่ากลาง 10 วิ (24 เทิร์นในชุดทดสอบ ไม่ใช่รูปจาก LINE จริง) · ถามยอด ~3 วิ | turn log |

ผลดิบของทุกชุดในรอบนี้: `eval/logs/run/`

## Harness: ปิดทีละชั้น และถ้าโมเดลทำผิด แต่ละชั้นกันได้ไหม

**ablation กับโมเดลจริง** (`eval_ablation.sh` → `ABLATION.md`): ปิด `_parse` ขอใหม่ ถามยอดตก 20 → 17 (โมเดลส่งข้อความว่างหลังได้ผลจาก tool) ·
ปิด ontology scenario 9 → 7 และถามยอด 20 → 19 · ปิด gate / check_args / ROUTE_IMAGE ผลเท่าเดิม เพราะในชุดนี้ 12B ไม่ได้ทำผิดแบบนั้น

**จำลองให้โมเดลทำผิด** (`eval_layers.py` → `LAYERS.md`, สคริปต์แทนโมเดล ผลเหมือนเดิมทุกครั้ง):

| ชั้น | โมเดลทำผิดแบบนี้ | เปิด | ปิด |
|---|---|---|---|
| gate (contract pre-tool-use) | สั่ง delete_invoice ทันที ผู้ใช้ยังไม่ยืนยัน | บิลยังอยู่ ได้ preview | บิลถูกลบ |
| check_args (contract pre-tool-use) | ส่ง argument ที่ tool ไม่มี | tool ตอบ error พร้อมชื่อที่ใช้ได้ | ได้ยอดรวมทุกร้าน 329 แทน 184 |
| ROUTE_IMAGE | ได้รูปแล้วตอบเลย ไม่อ่านใบเสร็จ | อ่านใบเสร็จ ได้ draft | ไม่มี draft |
| `_parse` ขอใหม่ | บอกว่าจะบันทึก แต่ไม่เรียก tool | ขอ JSON ใหม่ แล้วบันทึกจริง | ไม่ได้บันทึก |
| ontology | ส่งหมวดเป็นคำที่คนพูด (ค่าน้ำมัน) | ยอด 210 ถูก | ยอด 0 |
| ตรวจคำตอบ (contract หลังตอบ) | แต่งยอด 5,400 ที่ไม่มีในผลจาก tool | ขอใหม่ ผู้ใช้ได้ 329 | ผู้ใช้ได้ 5,400 |

**Contract ที่มีในโค้ด**
- pre-tool-use: `agent.check_args` (argument ที่ไม่รู้จัก) · `gate.needs_gate`/`park` (save, update บิลที่บันทึกแล้ว, delete, mark_reimbursed, manage_category ยกเว้น list ต้องยืนยัน) · `tools._num`/`_date`/ตรวจหมวด · `tools._own_invoice` (บิลคนอื่น)
- post-tool-use: `tools._make_draft` (สมการ subtotal − discount + vat = total, checksum เลขผู้เสียภาษี, QR mismatch, บิล/เลขอ้างอิงซ้ำ) · `tools.thai_date` (โมเดลคัดลอกวันที่ โค้ดแปลงปี พ.ศ./ค.ศ.) · ontology แทนหมวดที่โมเดลเดา
- ตรวจคำตอบสุดท้าย: `agent.unsupported_numbers` — ยอดเงินในคำตอบต้องมีอยู่ใน system prompt, ข้อความผู้ใช้ หรือ TOOL_RESULT (ไม่นับวันที่ เวลา เลขข้อ และจำนวนเต็ม < 10) ไม่ผ่านให้ตอบใหม่หนึ่งครั้ง ยังไม่ผ่านแนบหมายเหตุ · รันกับ 12B จริง 20 คำถามไม่เตือนผิดเลย

## Open-source เทียบ commercial (harness ชุดเดียวกัน)

ทุกชุดรันซ้ำกับ Claude Sonnet 5.5 ผ่าน Claude CLI (`scripts/claude_cli_bridge.py` แปลงคำขอ OpenAI standard เป็น `claude -p`, ใช้กับ eval เท่านั้น) ผลอยู่ใน `eval/logs/models/claude-sonnet-5-5/`

| | Gemma 4 12B (ในเครื่อง) | Claude Sonnet 5.5 |
|---|---|---|
| ถามยอดเงิน ตอบถูก / faithfulness | 20/20 / **1.00** | 20/20 / 0.97 |
| รันซ้ำได้คำตอบเดิมทุกช่อง | **98/100** | 91/100 |
| ถามเดิม 5 ครั้ง: สาระคงเดิม / ตัวเลขเหมือนกันทุกครั้ง | 20/20 / **19/20** | 20/20 / 11/20 |
| injection / รูปที่ไม่ใช่ใบเสร็จ | 5/5 / 12/12 | 5/5 / 12/12 |
| tool selection / scenario | 47/54 / 9/11 | **52/54 / 11/11** |
| อ่านใบเสร็จ held-out / ภาพใหม่ | 54/100 / 28/60 | **98/100 / 57/60** |

ข้อจำกัด: CLI รับประวัติแชทแบบแยกบทบาทไม่ได้ จึงส่งเป็นข้อความก้อนเดียว · Sonnet 5.5 ตั้ง temperature 0 ไม่ได้ · ตัวที่ faithfulness ของ Sonnet โดนหักเป็นเลขข้อในรายการกับช่วงวันที่ ไม่ใช่การแต่งข้อมูล

## ตอนนี้ยังผิดตรงไหน (held-out 100 ใบ)

| ชุดภาพ | ถูกครบ 5 field |
|---|---|
| clean (36 ใบ) | 24/36 |
| photo (37 ใบ) | 22/37 |
| camera — ถ่ายเอียง/เงา/เบลอ (27 ใบ) | 8/27 |

- ช่องที่ผิดบ่อยในใบที่ตก: วันที่ 24 ใบ · VAT 19 · หมวด 18 · ชื่อร้าน 14 · ยอดรวม 9 — วันที่ที่ยังผิดส่วนใหญ่คือโมเดลอ่านตัวเลขผิดเอง (เห็น 2026 เป็น 2016) ซึ่งการแปลงปีในโค้ดช่วยไม่ได้
- ปัญหาอยู่ที่ชั้นอ่านภาพ: Sonnet 5.5 กับ harness เดียวกันได้ 98/100 · เมื่อพลาด ผู้ใช้เห็น draft ก่อนบันทึกเสมอ (gate)
- เรื่องวันที่ แก้หลังเห็นผลรอบแรก (19/100) โดยปรับกับชุดจูน 200 ใบ แล้วรันชุด held-out รอบเดียว
- ทางแก้ต่อไป: finetune 12B ให้อ่านใบเสร็จไทย หรือใช้โมเดลอ่านภาพที่ดีกว่าเฉพาะขั้นอ่านรูป

## Ontology (`app/ontology.py`)

ความรู้เรื่องหมวดค่าใช้จ่ายเขียนเป็นไฟล์ ไม่ปล่อยให้โมเดลเดา — 3 ความสัมพันธ์:

| relation | ตัวอย่าง | ใช้ทำอะไร |
|---|---|---|
| `is_a` | เรียกรถ ⊂ เดินทาง | สรุปแยกหมวดย่อย (`by_subcategory`), รายงาน `group_by=subcategory` |
| `instance_of` | "บางจาก" → เชื้อเพลิง | จัดหมวดด้วยกติกาเมื่อรู้จักชื่อร้าน (ลำดับ: ที่ผู้ใช้เคยแก้ > ontology > โมเดล) |
| `alias` | "ค่าน้ำมัน" → เชื้อเพลิง | ถาม "ค่าเดินทางเดือนนี้" / "ค่าน้ำมันเท่าไหร่" ได้ทันที |

6 หมวด · 18 หมวดย่อย · 169 keyword · 49 คำพ้อง — หมวดที่เก็บใน DB ยังเป็น 6 ตัวเดิม หมวดย่อยคำนวณจากชื่อร้าน (ไม่เปลี่ยน schema)

หมวดที่โมเดลอ่านจากรูป เทียบกับให้ ontology ทับเมื่อรู้จักชื่อร้าน (`python -m eval.eval_ontology` → `ONTOLOGY.md`, ใช้ผลอ่านใบเสร็จของ 12B ไม่เรียก LLM ใหม่):

| ชุด | ontology รู้จักชื่อร้าน | กฎถูก | โมเดลอย่างเดียว | โมเดล + ontology |
|---|---|---|---|---|
| ชุดจูน 200 | 194/200 | 194/194 | 173/200 | **180/200** (แก้ 8 ทำพัง 1) |
| held-out 100 | 92/100 | 92/92 | 82/100 | **85/100** · ทำพัง 0 |
| ภาพใหม่ 60 | 58/60 | 58/58 | 50/60 | **53/60** · ทำพัง 0 |

ปิด ontology แล้ว scenario 9 → 7 และถามยอด 20 → 19 (`ABLATION.md`) · ถ้าโมเดลส่งหมวดเป็น "ค่าน้ำมัน" เปิด ontology ได้ยอดถูก ปิดได้ 0 (`LAYERS.md`)

> ไม่ใช่ผลแบบ blind: keyword เขียนหลังเห็นเคสพลาดของชุดจูน · keyword เป็นคำทั่วไป เช่น ปั๊ม, บางจาก, สปา, ถ่ายเอกสาร ไม่ใช่ชื่อร้านสังเคราะห์
> ไม่ใช่ OWL/RDF เพราะบอทต้องการ roll-up/lookup/synonym ไม่ใช่ reasoner

## ลองแล้ว (Gemma 4 12B)

**embedding แทนโมเดลจัดหมวดจากชื่อร้าน** (`eval_embedding.py` → `EMBEDDING.md`): ชื่อร้าน 120 ชื่อที่ 12B แต่ง (ไม่เคยเห็น keyword)

| วิธี | ถูก |
|---|---|
| keyword ontology | 68/68 ของชื่อที่รู้จัก (รู้จัก 68/120) |
| keyword → 12B (ที่ใช้อยู่) | **119/120** |
| keyword → embedding (bge-m3 บน Ollama) | 101/120 |

12B ได้เปรียบเพราะเป็นคนแต่งชื่อเอง แต่ห่างกัน 18 ชื่อ → ไม่ใช้ embedding

**OCR ก่อนส่งให้โมเดล** (`EVAL_DIR=dataset python -m eval.eval_ocr_ablation "" 60` → `OCR_ABLATION.md`, tesseract tha+eng, 60 ใบแรกของชุดจูน):

| เงื่อนไข | ถูกครบ 5 ช่อง | prompt token เฉลี่ย |
|---|---|---|
| รูปอย่างเดียว (ที่ใช้อยู่) | 33/60 | 260 |
| รูป + ข้อความ OCR | **44/60** | 391 |
| ข้อความ OCR อย่างเดียว | 26/60 (วันที่ 50%) | 296 |

OCR ใช้เวลา ~0.3 วิต่อใบ · เวลาของ LLM ในรอบนี้ใช้เทียบไม่ได้ (มีงานอื่นใช้ Ollama ตัวเดียวกันระหว่างรัน โมเดลถูกสลับเข้าออก)
ยังไม่ได้เปิดใช้ใน production: วัดบนชุดจูน ต้องยืนยันกับ held-out ก่อน

## Privacy — pseudonymization (`app/privacy.py`)

| ข้อมูล | อยู่ที่ไหน | ระบุตัวคนได้ไหม |
|---|---|---|
| LINE userId จริง | `users.line_user_id` คอลัมน์เดียว (ต้องใช้ตอบกลับ) | ได้ — ที่เดียวในระบบ |
| บิล | ผูกกับ `users.id` (เลข int) | ไม่ได้ถ้าไม่มีตาราง users |
| turn log / log ของ cron | `line:3f9a0c1d2b7e4a55` (HMAC-SHA256 + `PSEUDONYM_KEY`) | **ไม่ได้** ถ้าไม่มี key — คนเดิมได้ค่าเดิม metrics ต่อคนยังนับได้ |
| prompt ที่ส่ง LLM | ไม่มี user id เลย | — |

- HMAC ไม่ใช่ SHA-256 เปล่า: LINE id มีรูปแบบตายตัว ถ้าไม่มี key คนที่มีรายชื่อ id ก็ไล่ hash เทียบได้
- เป็น **pseudonymization ไม่ใช่ anonymization** โดยตั้งใจ — ถือ key + ตาราง users แล้วโยงกลับได้ เพื่อหา/ลบข้อมูลของคนที่ขอลบได้
- `PSEUDONYM_KEY` แยกจาก LINE secret เพราะ secret ต้อง rotate แต่ key นี้ห้ามเปลี่ยน (เปลี่ยน = คนเดียวกลายเป็นสองนามแฝง)
- log เก่าแปลงแล้ว: `python -m app.privacy FILE.jsonl` (1,343 แถวใน turn log + 47 แถวใน `eval/logs/*.jsonl`) — harness D5 ตรวจว่าไม่มี id จริงหลุดเข้า log
- ที่ยอมรับไว้: รูปสลิปมีชื่อผู้โอน/ผู้รับ ส่งให้ Gemma ทั้งรูป — ปิดชื่อก่อนส่งต้อง OCR+redact ซึ่งทดลองแล้วว่าช้าลงโดยไม่ได้ความแม่น · ตอนนี้โมเดลรันบนเครื่องเอง (Ollama) รูปไม่ออกนอกเครื่อง
- ⚠️ id จริง 16 แถวเคยอยู่ใน log ที่ commit ไปแล้ว — ไฟล์ถูกลบแล้ว แต่ยังอยู่ใน git history

## Troubleshooting (dev machine)

- **LLM error `Name or service not known` / `ConnectError` to Ollama** — the containers reach the host through
  `host.docker.internal` (mapped to `host-gateway` in `docker-compose.yml`). Check `curl http://127.0.0.1:11434/api/version`
  on the host and `ollama list` shows `gemma4:12b`.
- **Every call takes ~40 s with gemma4** — its thinking mode is on; keep `LLM_REASONING_EFFORT=none` (same answers, <1 s).
- **Calls suddenly crawl (~3 tokens/s) or time out** — a runaway generation kept running after the client gave up and a
  second copy of the model loaded. Restart Ollama; `LLM_MAX_TOKENS` (default 2048) now caps one reply.
- **Docker Desktop dies right after start / "backend crashed … initializing Inference manager … dockerInference"** —
  a stale unix socket from Docker AI. Fix: rename `%LOCALAPPDATA%\Docker\run` away (the file itself refuses `del`),
  set `"EnableDockerAI": false` in `%APPDATA%\Docker\settings-store.json`, start Docker Desktop once (single instance).
- **LINE stops replying** — check `data/logs/watch.out`. The tunnel watchdog (`scripts/tunnel_watch.py`) needs
  3 consecutive failed `/health` (body `"ok":true`, not just HTTP 200) before it swaps hostnames; it writes the new
  URL to `data/public_base_url`, which the containers read per request, so no container restart is needed.

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
| secrets | `.env` is git-ignored; rotate `LINE_CHANNEL_ACCESS_TOKEN`, `MCP_TOKEN` (and `LLM_API_KEY` if a hosted provider is used) before hand-in |

Optional extras: Cloudflare WAF rate-limit rule on `/webhook` and `/mcp`; Cloudflare Access (email OTP) in front of `/` if the chat UI stays up.

> Dev note: `app` hot-reloads (uvicorn `--reload`), the **worker does not** — after editing `app/*.py` run
> `docker compose restart worker`, or LINE keeps being served by the old code (`up -d` alone leaves a running worker untouched).

## What the agent decides vs what the program enforces

| layer | owns | code |
|---|---|---|
| agent (Gemma 4) | intent across turns, tool choice, ask-back on ambiguity, wording | `app/agent.py` |
| Python / SQL | money math, search, schema validation, arithmetic/tax-id/QR checks | `app/tools.py` |
| control layer (the model cannot bypass) | per-user ownership at tool level · **confirm-before-save/edit/delete/mark-reimbursed/category-change** (`app/gate.py`: the call is parked as a pending action, runs only after the user's own "ยืนยัน", 10-min TTL) · draft→confirmed · loop cap · rate limit | `app/gate.py`, `app/tools.py` |
| transport | LINE HMAC signature on every webhook, event idempotency, signed expiring file links, bearer token on `/mcp` | `app/main.py`, `app/files.py` |

Retention: `purge_old_data` runs daily (reports >7 d, images of deleted invoices >30 d, orphan uploads >7 d, chat rows >30 d).
Backup: `sh scripts/backup.sh` (pg_dump, keeps 14) — a bind-mounted volume is not a backup.
- **Worker log shows `httpx.ConnectTimeout` on every LINE call after a Docker restart** — the container resolver
  returns AAAA first and IPv6 is blackholed on the dev host. `docker-compose.yml` now sets
  `net.ipv6.conf.all.disable_ipv6=1` on app/worker; if it recurs, check `docker compose exec worker python -c "import httpx;print(httpx.get('https://api.line.me/',timeout=8).status_code)"`.

## ทำไมต้องมี Redis (คิวจำเป็น แต่ Redis เป็นตัวเลือก)

LINE ให้ webhook ประมาณ 1 วินาที ส่วนการอ่านใบเสร็จใช้ 20-70 วินาที — คิวจึงไม่ใช่ของตกแต่ง
ถ้าประมวลผลในตัว handler เลย event จะถูก LINE ทิ้งทุกครั้ง `/webhook` จึงทำแค่เช็คลายเซ็นกับ enqueue แล้วตอบ 200 (~0.15 s)

ทางเลือกที่พิจารณา:

| ทาง | ได้ | เสีย |
|---|---|---|
| `asyncio.create_task()` ในโปรเซส app | ไม่ต้องมี service เพิ่ม | **restart/crash = งานที่ค้างหายเงียบ** · ไม่มี retry · ไม่มี cron |
| Postgres เป็นคิว (`SELECT … FOR UPDATE SKIP LOCKED`) | เหลือ 4 service ใช้ DB ที่มีอยู่แล้ว | ต้องเขียน retry/backoff/dead-letter/cron/visibility-timeout เอง ~80 บรรทัด ในส่วนที่พลาดง่ายที่สุด |
| **Redis + arq (ที่ใช้)** | retry 3 ครั้ง, dead-letter, cron 4 ตัว, AOF — ได้มาโดยไม่เขียนเอง | +1 container (~10 MB RSS) |

ข้อแรกถูกตัดด้วยเหตุการณ์จริง: ตอน Docker Desktop ตายกลางการประมวลผล งานในคิวรอดเพราะ `--appendonly yes`
และบิล 3 ใบของผู้ใช้อีกคนถูกรีเพลย์กลับมาครบเมื่อ worker กลับขึ้น — ถ้าเป็น `create_task` บิลพวกนั้นหายไปโดยไม่มีใครรู้ว่าหาย

ข้อสองดีกว่าในแง่จำนวน service แต่แลกมาด้วยโค้ดคิวที่ต้องดูแลเอง ซึ่งไม่ใช่สิ่งที่โปรเจคนี้ตั้งใจพิสูจน์ (เป้าคือ agent loop)
ถ้าจะย้ายขึ้น VPS ที่คิดค่าแรม ข้อสองคือทางที่ควรทบทวนก่อน

Redis ไม่ได้ถูกใช้เป็น cache และไม่เก็บข้อมูลบิล (บิลอยู่ PostgreSQL) — หน้าที่เดียวคือส่งงานต่อ
การเรียงลำดับต่อผู้ใช้ arq ไม่ได้ให้มา ต้องล็อกเองที่ `app/worker.py` (`_locks`) ไม่งั้นบิลที่ส่งรวดกันจะประมวลผลสลับลำดับ

## รายงานสั่งได้ (generate_report)

The agent turns what the user asks for into a small spec; `app/report.py` validates it against whitelists and does
every sum in Python — the model never produces a number that reaches the PDF.

| spec key | values |
|---|---|
| `sections` | `summary, chart, by_category, by_vendor, by_month, by_day, table, items, images, note, signature` (order = order in the PDF; default `chart,by_category,table,signature`) |
| `columns` | `id, date, vendor, category, profile, doc_type, subtotal, discount, vat, total, reimbursed` |
| `group_by` | `category, vendor, month, profile, reimbursed` — adds a subtotal row per group |
| `sort` / `desc` | `date, total, vendor, category` / `true,false` |
| filters | `date_from, date_to, profile, reimbursed, category, vendor, min_total, max_total` |
| `vat_mode` | `separate` (ก่อน VAT / VAT / ยอดรวม + ตารางสรุป VAT), `included` (ยอดเดียวรวม VAT), `none` (ไม่มี VAT เลย) |
| extras | `title`, `note`, `top_n` (rows in by_vendor) |

Unknown values raise a ToolError listing the valid ones, so the agent corrects itself instead of failing the turn.
Examples that work in LINE: "ขอรายงานสิงหา แยกตามหมวด มีสรุปกับกราฟ" · "เอาแค่ตาราง ไม่เอากราฟ คอลัมน์วันที่ ร้าน ยอด เรียงมากไปน้อย"
· "แนบรูปใบเสร็จด้วย ตั้งชื่อว่า เบิกค่าเดินทาง ส.ค." · "เฉพาะหมวดอาหารที่ยังไม่เบิก ยอดเกิน 500" · "แยก VAT ด้วย จะเอาไปยื่นภาษีซื้อ"

### If LINE says REQUEST_TIMEOUT while `/health` is fine from here

LINE reaches the tunnel from Japan; that edge-to-edge path flaps independently of your own latency (local curl can be
150 ms while LINE times out). The webhook therefore does nothing but verify the signature and enqueue before answering
200 — no outbound LINE call in that path — and the worker sends the acks (loading animation at once, text at 25 s).

Turn on **Webhook redelivery** in the LINE Developers console (Messaging API → Webhook settings): LINE then retries an
event it failed to deliver, and `processed_events` already makes the retry a no-op if the first attempt did land.
`cron:tunnel_probe` records every check in the worker log and pushes an alert to `ADMIN_LINE_USER_ID` after two misses.
