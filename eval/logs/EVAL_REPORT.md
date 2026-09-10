# MemBoy — Evaluation Report (auto-generated)


## Eval A/D — tool selection · `gemma-4-26b-a4b-it`

| group | pass | rate |
|---|---|---|
| A-category | 2/2 | 100% |
| A-chat | 3/3 | 100% |
| A-delete | 2/2 | 100% |
| A-find | 4/4 | 100% |
| A-fx | 1/1 | 100% |
| A-image | 1/1 | 100% |
| A-image-flow | 2/2 | 100% |
| A-note | 3/3 | 100% |
| A-profile | 4/4 | 100% |
| A-reimburse | 2/2 | 100% |
| A-report | 3/3 | 100% |
| A-save | 3/3 | 100% |
| A-split | 2/2 | 100% |
| A-summary | 4/4 | 100% |
| A-trends | 3/3 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 3/3 | 100% |
| D-adversarial | 6/6 | 100% |
| E-compound | 4/4 | 100% |
| E-learned | 1/1 | 100% |
| **ALL** | **54/54** | **100%** |

## Eval A/D — tool selection · `gemma-4-31b-it`

| group | pass | rate |
|---|---|---|
| A-category | 2/2 | 100% |
| A-chat | 3/3 | 100% |
| A-delete | 1/2 | 50% |
| A-find | 4/4 | 100% |
| A-fx | 1/1 | 100% |
| A-image | 1/1 | 100% |
| A-image-flow | 2/2 | 100% |
| A-note | 3/3 | 100% |
| A-profile | 4/4 | 100% |
| A-reimburse | 2/2 | 100% |
| A-report | 3/3 | 100% |
| A-save | 3/3 | 100% |
| A-split | 2/2 | 100% |
| A-summary | 4/4 | 100% |
| A-trends | 2/2 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 3/3 | 100% |
| D-adversarial | 6/6 | 100% |
| **ALL** | **47/48** | **98%** |

Failures:

- #8 A-delete: first tool 'delete_invoice' != None — tools=['delete_invoice'] — reply: ลบบิล ครัวป้าแดง เรียบร้อยแล้วครับ

## Extraction — tuning set (prompt v1→v3 was tuned on this; not the headline number) · `gemma-4-31b-it` · 200 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 100% | 96% | 100% | 99% | 100% | **191/200** |

## Extraction — tuning set (prompt v1→v3 was tuned on this; not the headline number) · `gemma-4-26b-a4b-it` · 200 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 100% | 96% | 100% | 98% | 99% | **191/200** |

## Extraction — HELD-OUT test set (seed 7, never used for tuning) · `gemma-4-26b-a4b-it` · 100 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 97% | 93% | 100% | 100% | 96% | **90/100** |

## Extraction — HANDWRITTEN cash bills (separate hard set, synthetic, not a supported input) · `gemma-4-26b-a4b-it` · 30 files

| vendor | date | total | vat | category | all-5 |
|---|---|---|---|---|---|
| 100% | 97% | 100% | 100% | 100% | **29/30** |

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
| ref | 100% |
| qr_status | 100% |
| **all 4** | **30/30** |

## Eval C — loop metrics (all live turns)

- turns: 838 · LLM calls: 1484 · JSON first-try: **96.4%** · tool calls: 608 (avg 0.73/turn) · tool errors: 53 · loop-cap hits: 0
- per tool: analyze_receipt 146, save_invoice 110, summarize_expenses 50, update_invoice 49, find_invoices 40, manage_profile 40, remember_note 28, generate_report 27, mark_reimbursed 25, delete_invoice 18, analyze_trends 15, export_csv 12, split_bill 12, restore_invoice 11, get_invoice_image 11, convert_currency 8, manage_category 6

### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)

- เวลาต่อเทิร์น: p50 **18.89s** · p90 **71.28s** · สูงสุด 155.63s (n=420) — 96% ของเวลาอยู่ที่การเรียก LLM
- token เฉลี่ยต่อเทิร์น: เข้า 4581 · ออก 153 (รวมทั้งชุด 1,924,069 / 64,130)

### Safety — confirm-before-mutate (program-enforced)

- gated tool calls parked for a preview: 9 · executed after the user's own confirmation: 12 · **executed without a confirming user message: 0** (must be 0; n=97 turns)
- non-receipt images rejected (doc_type=other): **12/12** (eval/non_receipts, synthetic)

### Agency depth

- tool-chain length distribution: {0: 269, 1: 533, 2: 33, 3: 3} — turns with ≥2 tool calls: **36** (4%)
- ask-back turns (no tool, clarifying question): 44 (5%)
- self-recovery after a tool error (agent tried another call): 3/51
