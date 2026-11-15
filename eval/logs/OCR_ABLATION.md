# OCR ablation · `gemma4:12b` · 60 files (tesseract 5 tha+eng, psm 6; OCR mean 0.27s/file)

| condition | vendor | date | total | vat | category | all-5 | LLM p50 | LLM p90 | LLM mean | +OCR mean | prompt tok mean | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| image | 77% | 73% | 92% | 80% | 80% | **33/60** | 2.0s | 24.5s | 5.7s | 5.7s | 260 | 0 |
| image+ocr | 87% | 77% | 92% | 88% | 90% | **44/60** | 2.1s | 22.7s | 5.5s | 5.8s | 391 | 0 |
| ocr | 87% | 50% | 68% | 75% | 92% | **26/60** | 1.9s | 23.4s | 5.6s | 5.9s | 296 | 0 |

files where conditions disagree (image / image+ocr / ocr, fields correct of 5): 37

- 001_th_clean.png: 5 / 5 / 4
- 002_th_photo.jpg: 5 / 5 / 3
- 004_en_camera.png: 3 / 3 / 2
- 005_en_camera.png: 5 / 5 / 3
- 007_th_clean.png: 5 / 5 / 4
- 009_th_camera.png: 1 / 1 / 0
- 010_en_photo.png: 4 / 5 / 5
- 012_th_clean.png: 5 / 5 / 4
- 013_th_camera.png: 1 / 1 / 0
- 014_th_photo.pdf: 4 / 5 / 5
- 015_th_photo.jpg: 3 / 5 / 5
- 017_th_clean.jpg: 5 / 4 / 4
- 018_th_camera.jpg: 5 / 5 / 2
- 019_th_photo.jpg: 4 / 5 / 3
- 020_th_photo.png: 5 / 5 / 4
- 021_en_camera.png: 5 / 5 / 3
- 022_th_photo.jpg: 5 / 5 / 4
- 024_th_camera.jpg: 1 / 3 / 2
- 025_th_photo.jpg: 4 / 5 / 3
- 026_th_camera.jpg: 2 / 1 / 1
- 028_th_camera.pdf: 3 / 5 / 1
- 029_en_clean.jpg: 4 / 5 / 5
- 033_th_clean.png: 3 / 5 / 5
- 036_th_clean.png: 5 / 5 / 4
- 039_en_photo.jpg: 4 / 5 / 5
- 040_th_photo.png: 5 / 5 / 4
- 041_th_photo.jpg: 3 / 5 / 4
- 042_en_photo.png: 4 / 5 / 5
- 043_th_camera.png: 1 / 0 / 0
- 045_th_camera.jpg: 4 / 5 / 4
- 047_th_camera.png: 3 / 4 / 3
- 049_en_camera.jpg: 5 / 5 / 4
- 051_th_photo.jpg: 5 / 5 / 4
- 052_en_camera.pdf: 5 / 5 / 3
- 053_th_photo.jpg: 4 / 4 / 2
- 057_en_photo.png: 0 / 4 / 5
- 058_th_camera.png: 4 / 3 / 2
