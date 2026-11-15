# บั๊กเดิม จำลองกับ gemma4:12b

ย้อนการแก้แต่ละจุดในหน่วยความจำ (ไฟล์ไม่เปลี่ยน) แล้วถามคำถามเดิม เทียบกับตอนที่แก้แล้ว

- **delete** ก่อนแก้ #1: tool analyze_receipt({"image_id": "seed7603"}), save_invoice({"draft_id": 7603}), analyze_receipt({"image_id": "seed7604"}), save_invoice({"draft_id": 7604}) → "ต้องการลบใบเสร็จใบไหนครับ? (เช่น บิลล่าสุด หรือระบุชื่อร้านได้ครับ)"
- **delete** ก่อนแก้ #2: tool analyze_receipt({"image_id": "seed7605"}), save_invoice({"draft_id": 7605}), analyze_receipt({"image_id": "seed7606"}), save_invoice({"draft_id": 7606}) → "ต้องการลบใบเสร็จใบไหนครับ? (เช่น บิลล่าสุด หรือระบุชื่อร้านได้ครับ)"
- **delete** ก่อนแก้ #3: tool analyze_receipt({"image_id": "seed7607"}), save_invoice({"draft_id": 7607}), analyze_receipt({"image_id": "seed7608"}), save_invoice({"draft_id": 7608}) → "ต้องการให้ลบใบไหนครับ? (เช่น ล่าสุด หรือระบุชื่อร้าน)"
- **delete** แก้แล้ว #1: tool analyze_receipt({"image_id": "seed7609"}), save_invoice({"draft_id": 7609}), analyze_receipt({"image_id": "seed7610"}), save_invoice({"draft_id": 7610}) → "ต้องการลบใบไหนครับ? (เช่น ล่าสุด หรือระบุชื่อร้าน)"
- **delete** แก้แล้ว #2: tool analyze_receipt({"image_id": "seed7611"}), save_invoice({"draft_id": 7611}), analyze_receipt({"image_id": "seed7612"}), save_invoice({"draft_id": 7612}) → "ต้องการลบใบไหนครับ? (เช่น บิลล่าสุด หรือระบุชื่อร้านได้ครับ)"
- **delete** แก้แล้ว #3: tool analyze_receipt({"image_id": "seed7613"}), save_invoice({"draft_id": 7613}), analyze_receipt({"image_id": "seed7614"}), save_invoice({"draft_id": 7614}) → "ต้องการลบใบไหนครับ? (เช่น บิลล่าสุด หรือระบุชื่อร้านได้ครับ)"
- **args** ก่อนแก้ #1: tool summarize_expenses({"category": "เรียกรถ"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **args** ก่อนแก้ #2: tool summarize_expenses({"category": "เรียกรถ"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **args** ก่อนแก้ #3: tool summarize_expenses({"category": "เรียกรถ"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **args** แก้แล้ว #1: tool summarize_expenses({"category": "เรียกรถ", "profile": "all"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **args** แก้แล้ว #2: tool summarize_expenses({"category": "เรียกรถ", "profile": "all"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **args** แก้แล้ว #3: tool summarize_expenses({"category": "เรียกรถ", "profile": "all"}) → "ยอดรวมค่า Grab (เรียกรถ) ทั้งหมดคือ 396 บาทครับ"
- **sum** ก่อนแก้ #1: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดที่จ่ายให้ร้านกาแฟสามแยกมี 2 รายการ คือ 145 บาท และ 130 บาทครับ" · context มี total: False
- **sum** ก่อนแก้ #2: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดที่จ่ายให้ร้านกาแฟสามแยกมี 2 รายการ คือ 145 บาท และ 130 บาทครับ" · context มี total: False
- **sum** ก่อนแก้ #3: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดที่จ่ายให้ร้านกาแฟสามแยกมี 2 รายการ คือ 145 บาท และ 130 บาทครับ" · context มี total: False
- **sum** แก้แล้ว #1: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดรวมที่จ่ายให้ร้านกาแฟสามแยกทั้งหมดคือ 275 บาทครับ (จากทั้งหมด 2 รายการ)" · context มี total: True
- **sum** แก้แล้ว #2: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดรวมที่จ่ายให้ร้านกาแฟสามแยกทั้งหมดคือ 275 บาทครับ (จากทั้งหมด 2 รายการ)" · context มี total: True
- **sum** แก้แล้ว #3: tool find_invoices({"vendor": "ร้านกาแฟสามแยก"}) → "ยอดรวมที่จ่ายให้ร้านกาแฟสามแยกทั้งหมดคือ 275 บาทครับ (จากทั้งหมด 2 รายการ)" · context มี total: True
