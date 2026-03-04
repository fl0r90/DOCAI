FROM python:3.11-slim

# Evităm mizeriile de fișiere .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalăm dependențele de sistem corecte pentru Debian Trixie/Testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    postgresql-client \
    pv \
    && rm -rf /var/lib/apt/lists/*

# Copiem requirements și instalăm
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiem restul codului
COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "core_engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
