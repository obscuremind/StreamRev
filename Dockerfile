FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nginx \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY install.py .
COPY .env.example .env

RUN mkdir -p src/content/archive src/content/epg src/content/playlists \
    src/content/streams src/content/vod src/backups src/signals src/tmp src/logs

ENV PYTHONPATH=/app
ENV IPTV_SERVER_HOST=0.0.0.0
ENV IPTV_SERVER_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
