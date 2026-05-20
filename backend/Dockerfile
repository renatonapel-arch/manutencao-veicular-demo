# =========================================================
# Stage 1: build do frontend (React + Vite)
# =========================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# =========================================================
# Stage 2: deps Python
# =========================================================
FROM python:3.11-slim AS backend-builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# =========================================================
# Stage 3: runtime
# =========================================================
FROM python:3.11-slim
WORKDIR /app
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 libpq5 ca-certificates curl tzdata && \
    rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /root/.local /root/.local
COPY backend/ ./backend/
COPY --from=frontend-builder /frontend/dist ./frontend_dist

RUN mkdir -p /app/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
