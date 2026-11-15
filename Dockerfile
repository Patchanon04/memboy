FROM python:3.11-slim
# WeasyPrint system deps + Thai fonts (fonts-thai-tlwg: Laksaman/Loma/Garuda)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info fonts-thai-tlwg libzbar0 poppler-utils tesseract-ocr tesseract-ocr-tha \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries 5 -r requirements.txt
COPY app /srv/app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
