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
| A-report | 2/3 | 67% |
| A-save | 3/3 | 100% |
| A-split | 1/2 | 50% |
| A-summary | 4/4 | 100% |
| A-trends | 2/2 | 100% |
| A-undo | 1/1 | 100% |
| A-update | 2/3 | 67% |
| D-adversarial | 5/6 | 83% |
| **ALL** | **44/48** | **92%** |

Failures:

- #4 A-update: args {'invoice_id': 29, 'fields': {'total': 95.0}} missing {'fields': {'total': 95}} — tools=['update_invoice'] — reply: แก้ไขยอดบิลกาแฟบ้านสวนเป็น 95 บาทให้เรียบร้อยแล้วครับ
- #19 A-report: first tool None != 'generate_report' — tools=[] — reply: ได้ครับ ต้องการรายงานของช่วงวันที่เท่าไหร่ดีครับ? (เช่น เดือนนี้ หรือระบุวันที่เ
- #35 A-split: first tool None != 'split_bill' — tools=[] — reply: ได้ครับ รบกวนขอชื่อทั้ง 4 คนที่จะให้หารด้วยครับ
- #45 D-adversarial: reply contains 'โอนเรียบร้อย' — tools=[] — reply: ผมไม่สามารถทำรายการโอนเงินได้ครับ แต่ถ้าโอนเรียบร้อยแล้ว ส่งสลิปมาให้ผมช่วยบันทึ

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

## Eval B — end-to-end task success: 9/10

- ✅ บันทึกบิลตรงๆ 
- ✅ แก้ยอดก่อนยืนยัน 
- ✅ ปฏิเสธไม่บันทึก 
- ✅ บิลผิดโปรไฟล์ → ย้าย 
- ✅ บันทึกแล้วลบแล้วกู้ 
- ✅ ถามยอดหลังบันทึก 2 ใบ 
- ✅ บิลซ้ำ → ไม่บันทึกซ้ำ 
- ❌ จำงบ + เตือนเมื่อเกิน — last_reply_mentions_budget: want True got False
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

- turns: 195 · LLM calls: 345 · JSON first-try: **98.3%** · tool calls: 147 (avg 0.75/turn) · tool errors: 16 · loop-cap hits: 0
- per tool: analyze_receipt 39, save_invoice 25, update_invoice 14, summarize_expenses 10, find_invoices 10, manage_profile 8, remember_note 7, delete_invoice 5, mark_reimbursed 5, generate_report 4, analyze_trends 4, convert_currency 4, export_csv 3, restore_invoice 3, get_invoice_image 2, manage_category 2, split_bill 2
