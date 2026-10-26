FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data

# Rasm kartochkalari uchun shriftlar
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Baza va saqlangan fayllar shu papkada turadi (Railway'da volume ulanadi)
RUN mkdir -p /data /app/downloads

CMD ["python", "bot.py"]
