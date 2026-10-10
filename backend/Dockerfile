FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LIBREOFFICE_PATH=/usr/bin/soffice

# Install headless LibreOffice Writer and standard fonts for accurate DOCX -> PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-core \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu \
    fontconfig \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Preserve default letterhead images so they can populate a fresh mounted storage volume
RUN mkdir -p /app/default_assets/schools /app/default_assets/companies && \
    cp -f /app/storage/uploads/letterheads/schools/* /app/default_assets/schools/ 2>/dev/null || true && \
    cp -f /app/storage/uploads/letterheads/companies/* /app/default_assets/companies/ 2>/dev/null || true

EXPOSE 8000

CMD ["sh", "-c", "mkdir -p /app/storage/artifacts /app/storage/evidence /app/storage/uploads/letterheads/schools /app/storage/uploads/letterheads/companies && cp -n /app/default_assets/schools/* /app/storage/uploads/letterheads/schools/ 2>/dev/null || true && cp -n /app/default_assets/companies/* /app/storage/uploads/letterheads/companies/ 2>/dev/null || true && python seed_master_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

