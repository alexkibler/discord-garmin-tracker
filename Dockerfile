FROM python:3.12-slim

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY *.py ./

# Runtime data directory (mounted as a volume so config persists)
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

ENV PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/data/config.json

CMD ["python", "main.py"]
