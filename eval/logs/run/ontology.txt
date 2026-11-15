# Ontology vs model — category accuracy (replayed, no new LLM calls)

| set | vendors the ontology knows | rule correct on those | model alone | model + ontology |
|---|---|---|---|---|
| tuning (dataset, 200) | 194/200 | 194/194 | 173/200 | **180/200** |
| held-out (dataset_test, 100) | 92/100 | 92/92 | 82/100 | **85/100** |
| fresh images (dataset_blind, 60) | 58/60 | 58/58 | 50/60 | **53/60** |

- tuning (dataset, 200) fixed: 041_th_photo.jpg: "ซุปเปอร์มาร์เก็ต" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 069_th_photo.jpg: "ตลาดสดตลาดองเชย แถง 12" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 071_th_photo.png: "มินิมาร์ทน้ำอ้วน" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 075_th_clean.png: "ซุปเปอร์มาร์เก็ต" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 077_th_camera.pdf: "ตลาดสดคลองเตย แผง 12" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 103_th_camera.png: "มินิมาร์ทหาลั่น" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 154_th_camera.pdf: "ซูเปอร์มาร์เก็ต" อาหาร→ของใช้
- tuning (dataset, 200) fixed: 167_th_camera.jpg: "ซุปเปอร์มาร์เก็ต" อาหาร→ของใช้
- tuning (dataset, 200) **broke**: 175_th_camera.jpg: "ชำรวยมินิมาร์ท" อาหาร→ของใช้
- held-out (dataset_test, 100) fixed: 027_th_photo.jpg: "ตลาดสดคลองแฮง แถง 12" อาหาร→ของใช้
- held-out (dataset_test, 100) fixed: 039_th_clean.pdf: "ตลาดสดคลองเอย แผง 12" อาหาร→ของใช้
- held-out (dataset_test, 100) fixed: 063_th_photo.png: "ตลาดสดคลองเอย แผง 12" อาหาร→ของใช้
- fresh images (dataset_blind, 60) fixed: 007_th_clean.png: "ซุปเปอร์มาร์เก็ต" อาหาร→ของใช้
- fresh images (dataset_blind, 60) fixed: 017_th_clean.jpg: "ตลาดสดคลองเตย แผง 12" อาหาร→ของใช้
- fresh images (dataset_blind, 60) fixed: 059_th_camera.jpg: "ตลาดสดคลองเตย แผง 12" อาหาร→ของใช้

> Not blind: keywords were written after seeing the tuning-set misses, and the held-out misses were seen while building this check. Keywords are generic Thai expense words/chains (ปั๊ม, บางจาก, สปา, ถ่ายเอกสาร, ร้านทุกอย่าง), not the synthetic vendor names — but treat the gain as indicative until a fresh set confirms it.
