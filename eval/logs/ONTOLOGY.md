# Ontology vs model — category accuracy (replayed, no new LLM calls)

| set | vendors the ontology knows | rule correct on those | model alone | model + ontology |
|---|---|---|---|---|
| tuning (dataset, 200) | 194/200 | 194/194 | 198/200 | **200/200** |
| held-out (dataset_test, 100) | 92/100 | 92/92 | 96/100 | **98/100** |
| fresh images (dataset_blind, 60) | 58/60 | 58/58 | 58/60 | **58/60** |

- tuning (dataset, 200) fixed: 026_th_camera.jpg: "สปาทำหม่อนคลาย" อาหาร→สุขภาพ
- tuning (dataset, 200) fixed: 083_th_camera.jpg: "ร้านยี่สิบบาทของแท้" อาหาร→ของใช้
- held-out (dataset_test, 100) fixed: 001_th_camera.png: "ปิ่นบางจาก สาขาร่มเกล้า" อาหาร→เดินทาง
- held-out (dataset_test, 100) fixed: 065_th_camera.jpg: "ร้านถ่ายเอกสารหน้ามอ" ของใช้→อุปกรณ์

> Not blind: keywords were written after seeing the tuning-set misses, and the held-out misses were seen while building this check. Keywords are generic Thai expense words/chains (ปั๊ม, บางจาก, สปา, ถ่ายเอกสาร, ร้านทุกอย่าง), not the synthetic vendor names — but treat the gain as indicative until a fresh set confirms it.
