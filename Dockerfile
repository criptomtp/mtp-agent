FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements-root.txt
COPY backend/requirements.txt ./requirements-backend.txt
RUN pip install --no-cache-dir -r requirements-root.txt -r requirements-backend.txt
COPY . .
EXPOSE 8000
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
