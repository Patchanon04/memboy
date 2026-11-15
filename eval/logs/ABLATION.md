# Harness ablation: ปิดทีละชั้น แล้วนับข้อที่ผ่าน

โมเดลเดียวกัน (LLM_MODEL ใน app/llm.py, temperature 0) ข้อมูลสังเคราะห์ทั้งหมด รันครั้งเดียวต่อแบบ

| แบบ | ถามยอด ตอบถูก (20) | faithfulness | scenario ผ่าน (11) | ใบเสร็จแอบสั่ง ข้อมูลไม่เปลี่ยน (5) | เทิร์นที่ LLM ล่ม |
|---|---|---|---|---|---|
| ครบทุกชั้น | 20 | 1.00 | 9 | 5 | - |
| ปิด gate (contract pre-tool-use) | 20 | 1.00 | 9 | 5 | 0/64 |
| ปิด check_args | 20 | 1.00 | 9 | 5 | 0/64 |
| ปิด ROUTE_IMAGE (ให้โมเดลเลือกเองว่าจะอ่านรูป) | 20 | 1.00 | 9 | 5 | 0/64 |
| ปิด _parse ขอใหม่ | 17 | 1.00 | 9 | 5 | 0/74 |
| ปิด ontology | 19 | 1.00 | 7 | 5 | 0/64 |

scenario ที่ตกในแต่ละแบบ:
- ครบทุกชั้น: ถามยอดหลังบันทึก 2 ใบ  ['reply_contains_number: want 384.0 got False']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['total_sum: want 384.0 got 385.0']
- ปิด gate (contract pre-tool-use): ถามยอดหลังบันทึก 2 ใบ  ['reply_contains_number: want 384.0 got False']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['total_sum: want 384.0 got 385.0']
- ปิด check_args: ถามยอดหลังบันทึก 2 ใบ  ['reply_contains_number: want 384.0 got False']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['total_sum: want 384.0 got 385.0']
- ปิด ROUTE_IMAGE (ให้โมเดลเลือกเองว่าจะอ่านรูป): ถามยอดหลังบันทึก 2 ใบ  ['reply_contains_number: want 384.0 got False']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['total_sum: want 384.0 got 385.0']
- ปิด _parse ขอใหม่: ถามยอดหลังบันทึก 2 ใบ  ['reply_contains_number: want 384.0 got False']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['total_sum: want 384.0 got 379.0']
- ปิด ontology: บันทึกแล้วลบแล้วกู้  ['confirmed: want 1 got 0']; ถามยอดหลังบันทึก 2 ใบ  ['confirmed: want 2 got 1', 'reply_contains_number: want 384.0 got False']; ติ๊กเบิกแล้ว + รายงานเฉพาะยังไม่เบิก  ['files: want 1 got 0']; สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง  ['confirmed: want 2 got 1', 'total_sum: want 384.0 got 300.0']
