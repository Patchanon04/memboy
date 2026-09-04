# PBook — Evaluation Report (auto-generated)


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

- turns: 614 · LLM calls: 1086 · JSON first-try: **96.5%** · tool calls: 438 (avg 0.71/turn) · tool errors: 40 · loop-cap hits: 0
- per tool: analyze_receipt 98, save_invoice 77, update_invoice 36, summarize_expenses 33, find_invoices 33, manage_profile 28, remember_note 22, mark_reimbursed 21, generate_report 19, delete_invoice 13, analyze_trends 12, restore_invoice 9, get_invoice_image 9, split_bill 9, export_csv 7, convert_currency 7, manage_category 5

### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)

- เวลาต่อเทิร์น: p50 **17.48s** · p90 **76.46s** · สูงสุด 131.69s (n=246) — 96% ของเวลาอยู่ที่การเรียก LLM
- token เฉลี่ยต่อเทิร์น: เข้า 4723 · ออก 154 (รวมทั้งชุด 1,161,955 / 37,788)

### Agency depth

- tool-chain length distribution: {0: 207, 1: 378, 2: 27, 3: 2} — turns with ≥2 tool calls: **29** (5%)
- ask-back turns (no tool, clarifying question): 33 (5%)
- self-recovery after a tool error (agent tried another call): 3/39
