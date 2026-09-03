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

## Eval B — end-to-end task success: 10/10

- ✅ บันทึกบิลตรงๆ 
- ✅ แก้ยอดก่อนยืนยัน 
- ✅ ปฏิเสธไม่บันทึก 
- ✅ บิลผิดโปรไฟล์ → ย้าย 
- ✅ บันทึกแล้วลบแล้วกู้ 
- ✅ ถามยอดหลังบันทึก 2 ใบ 
- ✅ บิลซ้ำ → ไม่บันทึกซ้ำ 
- ✅ จำงบ + เตือนเมื่อเกิน 
- ✅ ติ๊กเบิกแล้ว + รายงานเฉพาะยังไม่เบิก 
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

- turns: 431 · LLM calls: 788 · JSON first-try: **96.6%** · tool calls: 333 (avg 0.77/turn) · tool errors: 32 · loop-cap hits: 0
- per tool: analyze_receipt 73, save_invoice 56, update_invoice 29, find_invoices 26, summarize_expenses 25, manage_profile 22, remember_note 16, mark_reimbursed 16, generate_report 15, delete_invoice 10, analyze_trends 9, restore_invoice 7, get_invoice_image 7, split_bill 7, convert_currency 6, export_csv 5, manage_category 4

### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)

- เวลาต่อเทิร์น: p50 **16.34s** · p90 **72.09s** · สูงสุด 131.69s (n=133) — 97% ของเวลาอยู่ที่การเรียก LLM
- token เฉลี่ยต่อเทิร์น: เข้า 4607 · ออก 155 (รวมทั้งชุด 612,705 / 20,568)

### Agency depth

- tool-chain length distribution: {0: 121, 1: 287, 2: 23} — turns with ≥2 tool calls: **23** (5%)
- ask-back turns (no tool, clarifying question): 28 (6%)
- self-recovery after a tool error (agent tried another call): 1/32
