# ── Stage 1: build Next.js ───────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python runtime with Node.js for serving both ────────────────────
FROM python:3.12-slim

# Install Node.js so we can run `next start`
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download BGE-M3 at build time so startup is immediate.
RUN python -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)"

# Backend source
COPY app/ ./app/
COPY ingestion/ ./ingestion/

# Frontend build artifacts (no source files needed at runtime)
COPY --from=frontend-builder /frontend/.next        ./frontend/.next
COPY --from=frontend-builder /frontend/public       ./frontend/public
COPY --from=frontend-builder /frontend/node_modules ./frontend/node_modules
COPY frontend/package.json    ./frontend/package.json
COPY frontend/next.config.ts  ./frontend/next.config.ts

COPY start.sh .
RUN chmod +x start.sh

# Render injects $PORT; Next.js listens there and proxies /api/* to FastAPI.
CMD ["./start.sh"]
