# PBook — Evaluation Report (auto-generated)


## Eval A/D — tool selection · `gemma-4-26b-a4b-it`

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
| A-profile | 3/4 | 75% |
| A-reimburse | 2/2 | 100% |
| A-report | 2/3 | 67% |
| A-save | 3/3 | 100% |
| A-split | 2/2 | 100% |
| A-summary | 4/4 | 100% |
| A-trends | 2/2 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 3/3 | 100% |
| D-adversarial | 6/6 | 100% |
| E-compound | 4/4 | 100% |
| E-learned | 1/1 | 100% |
| **ALL** | **50/53** | **94%** |

Failures:

- #8 A-delete: first tool 'delete_invoice' != None — tools=['delete_invoice'] — reply: ลบบิล ครัวป้าแดง 120.0 บาท เรียบร้อยแล้วครับ (หากต้องการกู้คืนแจ้งผมได้เลยนะครับ
- #19 A-report: first tool 'find_invoices' not in ['generate_report', None] — tools=['find_invoices', 'find_invoices'] — reply: ไม่พบรายการที่ยังไม่ได้เบิกในทุกโปรไฟล์เลยครับ มีอะไรให้ผมช่วยตรวจสอบเพิ่มเติมไห
- #22 A-profile: first tool None != 'manage_profile' — tools=[] — reply: ขณะนี้คุณกำลังใช้โปรไฟล์ บริษัท A อยู่แล้วครับ

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

- turns: 344 · LLM calls: 622 · JSON first-try: **97.3%** · tool calls: 267 (avg 0.78/turn) · tool errors: 29 · loop-cap hits: 3
- per tool: analyze_receipt 57, save_invoice 42, update_invoice 22, check_duplicate 21, summarize_expenses 19, find_invoices 18, manage_profile 14, remember_note 12, mark_reimbursed 11, generate_report 10, delete_invoice 8, analyze_trends 6, restore_invoice 5, get_invoice_image 5, split_bill 5, convert_currency 5, export_csv 4, manage_category 3

### Latency & tokens (เทิร์นที่วัดหลังติดตั้ง instrumentation)

- เวลาต่อเทิร์น: p50 **14.42s** · p90 **77.18s** · สูงสุด 131.69s (n=37) — 99% ของเวลาอยู่ที่การเรียก LLM
- token เฉลี่ยต่อเทิร์น: เข้า 4942 · ออก 198 (รวมทั้งชุด 182,857 / 7,332)

### Agency depth

- tool-chain length distribution: {0: 108, 1: 217, 2: 16, 6: 3} — turns with ≥2 tool calls: **19** (6%)
- ask-back turns (no tool, clarifying question): 22 (6%)
- self-recovery after a tool error (agent tried another call): 1/29
