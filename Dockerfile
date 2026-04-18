FROM python:3.12-slim

# Install system deps needed by Pillow / qrcode
RUN apt-get update && apt-get install -y --no-install-recommends \
        libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Port Fly.io will route to
EXPOSE 8080

# 2 workers is fine for a shared-cpu-1x with 256 MB RAM
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "run:app"]
