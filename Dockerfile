FROM python:3.11-slim

# Reduce memory: no .pyc files, unbuffered output, malloc optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_TRIM_THRESHOLD_=65536

WORKDIR /app
COPY requirements.txt ./requirements-root.txt
COPY backend/requirements.txt ./requirements-backend.txt
RUN pip install --no-cache-dir -r requirements-root.txt -r requirements-backend.txt && \
    find /usr/local/lib/python3.11 -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
COPY . .
EXPOSE 8000

# --workers 1: single worker for Railway free tier (~512MB RAM)
# --limit-max-requests 1000: auto-restart worker after 1000 requests to reclaim leaked memory
# --timeout-keep-alive 30: close idle connections sooner
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-max-requests 1000 --timeout-keep-alive 30"]
