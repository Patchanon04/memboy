# MemBoy — Evaluation Report (auto-generated)


## Eval A/D — tool selection · `claude-sonnet-5-5`

| group | pass | rate |
|---|---|---|
| A-category | 2/2 | 100% |
| A-chat | 3/3 | 100% |
| A-delete | 2/2 | 100% |
| A-find | 3/4 | 75% |
| A-fx | 1/1 | 100% |
| A-image | 1/1 | 100% |
| A-image-flow | 2/2 | 100% |
| A-note | 3/3 | 100% |
| A-profile | 4/4 | 100% |
| A-reimburse | 2/2 | 100% |
| A-report | 3/3 | 100% |
| A-save | 3/3 | 100% |
| A-split | 2/2 | 100% |
| A-summary | 3/4 | 75% |
| A-trends | 3/3 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 3/3 | 100% |
| D-adversarial | 6/6 | 100% |
| E-compound | 4/4 | 100% |
| E-learned | 1/1 | 100% |
| **ALL** | **52/54** | **96%** |

Failures:

- #10 A-summary: args {'date_from': '2026-11-01', 'date_to': '2026-11-15', 'profile': 'ส่วนตัว'} missing {'date_from': '2026-09-01'} — tools=['summarize_expenses'] — reply: เดือนนี้ (1–15 พ.ย. 2026) ในโปรไฟล์ส่วนตัวยังไม่มีบิลที่บันทึกไว้เลยครับ ยอดรวมจ
- #15 A-find: args {'category': 'โรงแรม/ที่พัก', 'limit': 20} matches none of [{'vendor': 'โรงแรม'}, {'category': 'ที่พัก'}] — tools=['find_invoices', 'find_invoices'] — reply: ไม่พบบิลโรงแรม/ที่พักเลยค่ะ ผมค้นทุกโปรไฟล์ ทุกช่วงเวลาแล้ว ตอนนี้ยังไม่มีบิลในห

## Eval A/D — tool selection · `gemma4-12b`

| group | pass | rate |
|---|---|---|
| A-category | 2/2 | 100% |
| A-chat | 3/3 | 100% |
| A-delete | 2/2 | 100% |
| A-find | 3/4 | 75% |
| A-fx | 1/1 | 100% |
| A-image | 1/1 | 100% |
| A-image-flow | 2/2 | 100% |
| A-note | 2/3 | 67% |
| A-profile | 4/4 | 100% |
| A-reimburse | 2/2 | 100% |
| A-report | 3/3 | 100% |
| A-save | 2/3 | 67% |
| A-split | 2/2 | 100% |
| A-summary | 3/4 | 75% |
| A-trends | 3/3 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 3/3 | 100% |
| D-adversarial | 6/6 | 100% |
| E-compound | 1/4 | 25% |
| E-learned | 1/1 | 100% |
| **ALL** | **47/54** | **87%** |

Failures:

- #3 A-save: first tool 'delete_invoice' != None — tools=['delete_invoice'] — reply: รับทราบครับ ยกเลิกการบันทึกบิลครัวป้าแดง (120 บาท) ให้แล้วครับ
- #10 A-summary: args {'date_from': '2026-11-01', 'date_to': '2026-11-15', 'profile': 'all'} missing {'date_from': '2026-09-01'} — tools=['summarize_expenses'] — reply: เดือนนี้ (1 พ.ย. - 15 พ.ย.) ยังไม่มีการบันทึกค่าใช้จ่ายครับ
- #17 A-find: args {'date_from': '2026-11-01', 'date_to': '2026-11-15', 'category': 'คาเฟ่'} missing {'item': 'กาแฟ'} — tools=['find_invoices'] — reply: จากการตรวจสอบข้อมูลในเดือนนี้ (1 พ.ย. - 15 พ.ย.) ยังไม่พบรายการที่บันทึกในหมวดคา
- #26 A-note: first tool None != 'remember_note' — tools=[] — reply: รับทราบครับพี่โบ๊ท มีอะไรให้ MemBoy ช่วยจัดการเรื่องบิลหรือค่าใช้จ่ายแจ้งได้เลยค
- #49 E-compound: tool chain [] lacks save_invoice — tools=[] — reply: ขอโทษค่ะ ระบบขัดข้อง ลองใหม่อีกครั้งนะคะ
- #50 E-compound: chain ['mark_reimbursed'] has none of ['find_invoices', 'summarize_expenses'] after the first call — tools=['mark_reimbursed'] — reply: ติ๊กเบิกบิล แท็กซี่มิเตอร์ (180 บาท) ให้แล้วครับ

สำหรับยอดที่ยังไม่เบิกในเดือนน
- #52 E-compound: tool chain ['split_bill'] lacks get_invoice_image — tools=['split_bill'] — reply: หาร 4 คน (โบ๊ท, นัท, มิ้นท์, เจ) ตกคนละ 300 บาทครับ

ส่วนรูปบิลสามารถดูได้ที่นี่

## Extraction — tuning set (prompt v1→v3 was tuned on this; not the headline number) · `gemma4:12b` · 200 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 94% | 81% | 94% | 88% | 94% | **151/200** |

## Extraction — HELD-OUT test set (seed 7, never used for tuning) · `gemma4:12b` · 100 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 90% | 84% | 92% | 87% | 92% | **79/100** |

## Extraction — HANDWRITTEN cash bills (separate hard set, synthetic, not a supported input) · `gemma4:12b` · 30 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 93% | 97% | 100% | 100% | 97% | **27/30** |

## Eval B — end-to-end task success: 11/11

- ✅ บันทึกบิลตรงๆ 
- ✅ แก้ยอดก่อนยืนยัน 
- ✅ ปฏิเสธไม่บันทึก 
- ✅ บิลผิดโปรไฟล์ → ย้าย 
- ✅ บันทึกแล้วลบแล้วกู้ 
- ✅ ถามยอดหลังบันทึก 2 ใบ 
- ✅ บิลซ้ำ → ไม่บันทึกซ้ำ 
- ✅ จำงบ + เตือนเมื่อเกิน 
- ✅ ติ๊กเบิกแล้ว + รายงานเฉพาะยังไม่เบิก 
- ✅ สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง 
- ✅ รูปไม่ใช่บิล 

## Slip extraction + QR consistency (30 synthetic slips, 6 layouts, 5 deliberate mismatches)

| field | accuracy |
|---|---|
| doc_type | 100% |
| total | 100% |
| ref | 80% |
| qr_status | 80% |
| **all 4** | **24/30** |

Misses: slip_05_L4.png ['ref', 'qr_status']; slip_09_L2.png ['ref', 'qr_status']; slip_10_L3.png ['ref', 'qr_status']; slip_15_L2.png ['ref', 'qr_status']; slip_27_L2.png ['ref', 'qr_status']; slip_29_L4.png ['ref', 'qr_status']

## Eval C — loop metrics (turns answered by `gemma4:12b`)

- turns: 1493 · LLM calls: 3026 · JSON first-try: **97.5%** · tool calls: 1451 (avg 0.97/turn) · tool errors: 105 · loop-cap hits: 0
- per tool: summarize_expenses 390, analyze_receipt 354, save_invoice 209, find_invoices 208, update_invoice 55, manage_profile 51, delete_invoice 43, mark_reimbursed 33, generate_report 27, remember_note 25, restore_invoice 21, analyze_trends 10, split_bill 9, export_csv 4, get_invoice_image 4, manage_category 4, convert_currency 4

### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)

- เวลาต่อเทิร์น: p50 **3.83s** · p90 **17.91s** · สูงสุด 316.44s (n=1493) — 89% ของเวลาอยู่ที่การเรียก LLM
- token เฉลี่ยต่อเทิร์น: เข้า 5242 · ออก 357 (รวมทั้งชุด 7,826,712 / 533,488)

### Safety — confirm-before-mutate (program-enforced)

- gated tool calls parked for a preview: 66 · executed after the user's own confirmation: 174 · **executed without a confirming user message: 0** (must be 0; n=1493 turns)
- non-receipt images rejected (doc_type=other): **12/12** (eval/non_receipts, synthetic)

### Agency depth

- tool-chain length distribution: {0: 88, 1: 1359, 2: 46} — turns with ≥2 tool calls: **46** (3%)
- ask-back turns (no tool, clarifying question): 16 (1%)
- self-recovery after a tool error (agent tried another call): 42/105
