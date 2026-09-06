# OCR ablation · `gemma-4-26b-a4b-it` · 3 files (tesseract 5 tha+eng, psm 6; OCR mean 0.51s/file)

| condition | vendor | date | total | vat | category | all-5 | LLM p50 | LLM p90 | LLM mean | +OCR mean | prompt tok mean | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| image | 100% | 100% | 100% | 100% | 100% | **3/3** | 19.0s | 22.6s | 19.1s | 19.1s | 479 | 0 |
| image+ocr | 100% | 100% | 100% | 100% | 100% | **3/3** | 23.0s | 25.7s | 22.4s | 22.9s | 640 | 0 |
| ocr | 100% | 67% | 100% | 100% | 100% | **2/3** | 58.6s | 132.7s | 69.5s | 70.0s | 383 | 0 |

files where conditions disagree (image / image+ocr / ocr, fields correct of 5): 1

- 001_th_clean.png: 5 / 5 / 4
