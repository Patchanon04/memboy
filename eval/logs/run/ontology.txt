# Ontology vs model — category accuracy (replayed, no new LLM calls)

| set | vendors the ontology knows | rule correct on those | model alone | model + ontology |
|---|---|---|---|---|
| tuning (dataset, 200) | 194/200 | 194/194 | 188/200 | **188/200** |
| held-out (dataset_test, 100) | 92/100 | 92/92 | 92/100 | **93/100** |
| fresh images (dataset_blind, 60) | 58/60 | 58/58 | 55/60 | **55/60** |

- tuning (dataset, 200) fixed: 080_th_camera.png: "ซุปเปอร์ชุมชนวัดใต้" อาหาร→ของใช้
- tuning (dataset, 200) **broke**: 047_th_camera.png: "ซูเปอร์มาร์เก็ต" อาหาร→ของใช้
- held-out (dataset_test, 100) fixed: 014_th_camera.png: "ปิ่มบางจาก สาขามรมเกล้า" อาหาร→เดินทาง

> Not blind: keywords were written after seeing the tuning-set misses, and the held-out misses were seen while building this check. Keywords are generic Thai expense words/chains (ปั๊ม, บางจาก, สปา, ถ่ายเอกสาร, ร้านทุกอย่าง), not the synthetic vendor names — but treat the gain as indicative until a fresh set confirms it.
