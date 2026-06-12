# --- etapa 1: build del frontend ---
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# vite escribe en ../src/sharedbrain/static → redirigimos dentro del contenedor
RUN mkdir -p /build/src/sharedbrain && npm run build -- --outDir /out/static --emptyOutDir

# --- etapa 2: runtime python ---
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY --from=frontend /out/static src/sharedbrain/static
RUN pip install --no-cache-dir .

# config y BD viven en /data; el vault se monta en /vault
ENV SHAREDBRAIN_CONFIG=/data/sharedbrain.config.yaml
WORKDIR /data
EXPOSE 8765
CMD ["sharedbrain", "serve", "--web", "--host", "0.0.0.0", "--port", "8765"]
