# Keyword vs embedding vs Gemma — vendor name → category

120 names, invented by gemma4:12b (never saw the keywords). Category only (6 classes), name only (no image).

| method | coverage | correct |
|---|---|---|
| keyword ontology (current) | 68/120 | 68/68 of those it claims |
| embedding kNN (bge-m3) | 120/120 | 100/120 |
| Gemma picks the category | 120/120 | 119/120 |
| **keyword → Gemma (what runs now)** | 120/120 | **119/120** |
| **keyword → embedding** | 120/120 | **101/120** |

On the 52 names the keywords don't know: Gemma 51/52 · embedding 33/52

Embedding with a similarity threshold (claim only when sure):

| threshold | claimed | correct |
|---|---|---|
| 0.60 | 83/120 | 78/83 |
| 0.65 | 64/120 | 62/64 |
| 0.70 | 45/120 | 45/45 |
| 0.75 | 21/120 | 21/21 |
| 0.80 | 13/120 | 13/13 |

Wrong answers (name: gold | keyword | embedding | gemma):
- After You: อาหาร | - | ของใช้ (0.45) | อาหาร
- Subway Thailand: อาหาร | - | เดินทาง (0.64) | อาหาร
- Circle K Convenience: เดินทาง | - | อาหาร (0.56) | ของใช้
- City Shuttle: เดินทาง | - | อุปกรณ์ (0.61) | เดินทาง
- Siam Intercontinental: ที่พัก | - | เดินทาง (0.52) | ที่พัก
- The Standard, Bangkok: ที่พัก | - | อาหาร (0.58) | ที่พัก
- Riverside Boutique: ที่พัก | - | ของใช้ (0.49) | ที่พัก
- Stay_Easy_Inn: ที่พัก | - | เดินทาง (0.66) | ที่พัก
- HopInn: ที่พัก | - | อาหาร (0.55) | ที่พัก
- Mahanakhon Hill: ที่พัก | - | เดินทาง (0.42) | ที่พัก
- Little Garden Boutique: ที่พัก | - | ของใช้ (0.60) | ที่พัก
- Mega Construction Supply: อุปกรณ์ | - | ของใช้ (0.51) | อุปกรณ์
- FitZone Studio: สุขภาพ | - | อาหาร (0.49) | สุขภาพ
- Mega Health Care: สุขภาพ | - | ของใช้ (0.57) | สุขภาพ
- ฟิตเนสไทยแลนด์: สุขภาพ | - | อาหาร (0.53) | สุขภาพ
- Medipro Pharmacy: สุขภาพ | สุขภาพ | อุปกรณ์ (0.57) | สุขภาพ
- Harmony Wellness Hub: สุขภาพ | - | ที่พัก (0.51) | สุขภาพ
- ร้านขายของชำป้าแดง: ของใช้ | - | สุขภาพ (0.55) | ของใช้
- บ้านสวน ของใช้ในบ้าน: ของใช้ | - | อุปกรณ์ (0.65) | ของใช้
- Modern Trade Express: ของใช้ | - | อาหาร (0.57) | ของใช้
