FROM python:3.11-slim
WORKDIR /app

# WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements-root.txt
COPY backend/requirements.txt ./requirements-backend.txt
RUN pip install --no-cache-dir -r requirements-root.txt -r requirements-backend.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
