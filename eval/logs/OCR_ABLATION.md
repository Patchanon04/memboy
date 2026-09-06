# OCR ablation · `gemma-4-26b-a4b-it` · 60 files (tesseract 5 tha+eng, psm 6; OCR mean 0.32s/file)

| condition | vendor | date | total | vat | category | all-5 | LLM p50 | LLM p90 | LLM mean | +OCR mean | prompt tok mean | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| image | 95% | 93% | 97% | 97% | 97% | **56/60** | 25.9s | 146.2s | 46.0s | 46.0s | 463 | 12 |
| image+ocr | 93% | 92% | 95% | 95% | 93% | **55/60** | 26.4s | 116.8s | 52.6s | 52.9s | 579 | 15 |
| ocr | 82% | 53% | 72% | 75% | 85% | **30/60** | 31.7s | 243.2s | 74.2s | 74.5s | 323 | 19 |

files where conditions disagree (image / image+ocr / ocr, fields correct of 5): 31

- 001_th_clean.png: 5 / 5 / 4
- 004_en_camera.png: 5 / 5 / 3
- 005_en_camera.png: 5 / 5 / 3
- 009_th_camera.png: 5 / 5 / 0
- 012_th_clean.png: 5 / 5 / 4
- 013_th_camera.png: 3 / 3 / 0
- 016_en_camera.jpg: 5 / 5 / 2
- 017_th_clean.jpg: 5 / 5 / 4
- 018_th_camera.jpg: 5 / 5 / 2
- 019_th_photo.jpg: 5 / 5 / 0
- 020_th_photo.png: 5 / 0 / 0
- 021_en_camera.png: 0 / 0 / 3
- 022_th_photo.jpg: 0 / 5 / 4
- 024_th_camera.jpg: 5 / 5 / 2
- 025_th_photo.jpg: 5 / 5 / 0
- 026_th_camera.jpg: 4 / 3 / 0
- 027_en_photo.pdf: 5 / 0 / 5
- 028_th_camera.pdf: 5 / 5 / 3
- 031_th_camera.jpg: 5 / 5 / 3
- 035_th_camera.png: 5 / 5 / 0
- 038_th_camera.pdf: 5 / 5 / 4
- 040_th_photo.png: 5 / 5 / 4
- 041_th_photo.jpg: 5 / 5 / 4
- 043_th_camera.png: 5 / 5 / 0
- 047_th_camera.png: 5 / 5 / 3
- 049_en_camera.jpg: 5 / 5 / 4
- 050_th_clean.jpg: 5 / 5 / 4
- 051_th_photo.jpg: 5 / 5 / 4
- 052_en_camera.pdf: 5 / 5 / 3
- 053_th_photo.jpg: 5 / 5 / 2
- 058_th_camera.png: 5 / 5 / 1
