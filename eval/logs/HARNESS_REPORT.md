# Harness conformance — ผลทดสอบรายข้อ

รันด้วย `docker compose run --rm app python -m tests.test_harness` · ผ่าน 16/16 ข้อที่วัดได้ในเครื่อง

| # | รายการ | วิธีพิสูจน์ | ผล | ค่าที่วัดได้ |
|---|---|---|---|---|
| G1 | User scoping ที่ระดับ tool | unit test | ✅ ผ่าน | user B ถูกปฏิเสธ 4/4 tools ด้วยข้อความเดียวกับ 'บิลไม่มีจริง' |
| G2 | Loop cap ต่อเทิร์น | agent loop (LLM จำลอง) | ✅ ผ่าน | โมเดลเรียก tool ไม่หยุด → ตัดที่ 6 ครั้ง แล้วตอบ user |
| G3 | Validate args ที่ปาก tool | unit test | ✅ ผ่าน | ปฏิเสธทั้งหมด: total=-5, total=abc, status=confirmed, category=ไม่มีหมวดนี้ |
| G4 | ลบ = soft delete (กู้คืนได้) | unit test | ✅ ผ่าน | หลังลบ: แถวยังอยู่ใน DB, ไม่โผล่ใน query, restore กลับมาได้ |
| G5 | Prompt injection ในรูปบิล | ระบบภายนอก | ✅ ผ่าน | Eval D adversarial 6/6 ผ่าน (รวมบิลที่ฝังคำสั่ง SYSTEM OVERRIDE) + live probe บันทึกใน eval/logs/ |
| G6 | Error ไม่รั่วถึง user และไม่ถึงโมเดล | agent loop (LLM จำลอง) | ✅ ผ่าน | ข้อความ exception ไม่ปรากฏทั้งในคำตอบ user และใน context ที่ป้อนกลับโมเดล |
| G7 | Rate limit ต่อ user (LINE + เว็บ) | unit test | ✅ ผ่าน | 10 ครั้งแรกผ่าน / ครั้งที่ 11-12 บล็อก; ใช้ทั้ง events.py และ web.py |
| G8 | ย่อรูปก่อนส่ง LLM | unit test | ✅ ผ่าน | 4000x3000 184KB → 1280x960 19KB |
| D1 | temperature = 0 ทุก call | unit test | ✅ ผ่าน | payload ที่ส่งจริงมี generationConfig.temperature = 0.0 |
| D2 | เลขเงินมาจาก SQL + เช็ค subtotal+vat≈total | unit test | ✅ ผ่าน | ยอดรวมจาก SQL = 441.5 (ตรงกับผลบวกจริง); บิลที่ 100+7≠500 ถูกติด warning อัตโนมัติ |
| D3 | Webhook idempotency | agent loop (LLM จำลอง) | ✅ ผ่าน | event h-eb61739d ส่งซ้ำ → ไม่เข้า agent loop รอบสอง (ถูก dedupe จากตาราง processed_events) |
| D4 | State machine ของบิล (draft → confirmed) | unit test | ✅ ผ่าน | บันทึกซ้ำถูกปฏิเสธที่ tool: บิล 501 ไม่ใช่ draft (status=confirmed) — บันทึกไปแล้ว |
| D5 | Turn log ครบทุกเทิร์น (JSONL) | agent loop (LLM จำลอง) | ✅ ผ่าน | เทิร์นล่าสุดถูกบันทึกครบ: user/in/steps/out (1 step) |
| D6 | Pin รุ่นโมเดล (ไม่ใช้ alias ลอยๆ) | unit test | ✅ ผ่าน | MODEL=gemma-4-26b-a4b-it · FALLBACK=gemma-4-31b-it (ระบุรุ่นเต็ม ไม่ใช่ alias) |
| D7 | Inject วันที่ปัจจุบัน (Asia/Bangkok) | unit test | ✅ ผ่าน | system prompt มีวันที่ 2026-09-05 (เวลาไทย) → 'เดือนนี้/เมื่อวาน' คำนวณจากโค้ด ไม่ใช่ความจำโมเดล |
| D8 | Serialize ต่อ user (ขนานข้าม user) | agent loop (LLM จำลอง) | ✅ ผ่าน | user เดียวกัน: sesese (s→e เรียงคู่ = ไม่ทับกัน) · คนละ user: ssseee (เริ่มซ้อนกันได้ = ขนาน) |
| X1 | LINE transport (reply/push/quick reply/Flex/rich menu) | ระบบภายนอก | ⏳ ยังไม่วัด | ยังไม่ได้วัด — ต้องมี LINE channel credentials (โค้ดพร้อม: scripts/setup_line.py) |
| X2 | LIFF dashboard บนแอป LINE | ระบบภายนอก | ⏳ ยังไม่วัด | ยังไม่ได้วัด — ต้องมี LIFF ID จาก LINE Login channel |
