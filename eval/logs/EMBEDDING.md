# Keyword vs embedding vs Gemma — vendor name → category

120 names, invented by Gemma (never saw the keywords). Category only (6 classes), name only (no image).

| method | coverage | correct |
|---|---|---|
| keyword ontology (current) | 77/120 | 77/77 of those it claims |
| embedding kNN (gemini-embedding-001) | 120/120 | 108/120 |
| Gemma picks the category | 120/120 | 106/120 |
| **keyword → Gemma (what runs now)** | 120/120 | **112/120** |
| **keyword → embedding** | 120/120 | **109/120** |

On the 43 names the keywords don't know: Gemma 35/43 · embedding 32/43

Embedding with a similarity threshold (claim only when sure):

| threshold | claimed | correct |
|---|---|---|
| 0.60 | 120/120 | 108/120 |
| 0.65 | 120/120 | 108/120 |
| 0.70 | 120/120 | 108/120 |
| 0.75 | 119/120 | 108/119 |
| 0.80 | 108/120 | 101/108 |

Wrong answers (name: gold | keyword | embedding | gemma):
- After You: อาหาร | - | อุปกรณ์ (0.72) | อาหาร
- Swensen's: อาหาร | - | ของใช้ (0.82) | อาหาร
- Marriott International (แมริออท อินเตอร์เนชั่นแนล): ที่พัก | - | เดินทาง (0.83) | ที่พัก
- The Standard (เดอะ สแตนดาร์ด): ที่พัก | - | ของใช้ (0.80) | ที่พัก
- Local Soul Home (โลคอล โซล โฮม): ที่พัก | - | อุปกรณ์ (0.80) | ที่พัก
- Minor Hotels (ไมเนอร์ โฮเทลส์): ที่พัก | - | เดินทาง (0.84) | ที่พัก
- B-Quik: อุปกรณ์ | - | เดินทาง (0.77) | เดินทาง
- Boots Thailand: สุขภาพ | สุขภาพ | ของใช้ (0.83) | สุขภาพ
- Fitness First: สุขภาพ | - | อาหาร (0.77) | สุขภาพ
- Virgin Active: สุขภาพ | - | อาหาร (0.76) | สุขภาพ
- 7-Eleven (เซเว่น อีเลฟเว่น): ของใช้ | ของใช้ | ของใช้ (0.93) | อาหาร
- Tops Supermarket (ท็อปส์ ซูเปอร์มาร์เก็ต): ของใช้ | ของใช้ | ของใช้ (0.86) | อาหาร
- Makro (แม็คโคร): ของใช้ | ของใช้ | ของใช้ (0.87) | อาหาร
- Gourmet Market (กูร์เมต์ มาร์เก็ต): ของใช้ | - | ของใช้ (0.85) | อาหาร
- Villa Market (วิลล่า มาร์เก็ต): ของใช้ | - | ของใช้ (0.86) | อาหาร
- Lawson 108 (ลอว์สัน 108): ของใช้ | - | ของใช้ (0.82) | อาหาร
- FamilyMart (แฟมิลี่มาร์ท): ของใช้ | - | ของใช้ (0.88) | อาหาร
- Jay Muay Minimart (เจ๊หมวย มินิมาร์ท): ของใช้ | ของใช้ | ของใช้ (0.85) | อาหาร
- Uncle Chai Store (ร้านลุงชัย): ของใช้ | - | อาหาร (0.80) | ของใช้
- Somjai Mart (สมใจ มาร์ท): ของใช้ | - | ของใช้ (0.84) | อาหาร
- Municipal Fresh Market (ตลาดสดเทศบาล): ของใช้ | ของใช้ | ของใช้ (0.90) | อาหาร
- Siam Superstore (สยาม ซูเปอร์สโตร์): ของใช้ | ของใช้ | ของใช้ (0.84) | อาหาร
- Happy Home Goods (แฮปปี้ โฮม กู๊ดส์): ของใช้ | - | อุปกรณ์ (0.85) | ของใช้
- Bangkok Mart (บางกอก มาร์ท): ของใช้ | - | ของใช้ (0.85) | อาหาร
- Mae Klong Market (ตลาดแม่กลอง): ของใช้ | - | ของใช้ (0.87) | อาหาร
