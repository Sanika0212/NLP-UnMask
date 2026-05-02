# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm nginx supervisor curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir \
    $(grep -v -E "^(torch|transformers|ragas|sentence.transformers|#|$)" requirements.txt | tr '\n' ' ')

COPY . .

# Built Next.js standalone server
COPY --from=frontend-builder /frontend/.next/standalone ./frontend-server
COPY --from=frontend-builder /frontend/.next/static     ./frontend-server/.next/static
COPY --from=frontend-builder /frontend/public           ./frontend-server/public

# Config files
COPY docker/nginx.conf       /etc/nginx/sites-enabled/default
COPY docker/supervisord.conf /etc/supervisor/conf.d/unmask.conf

RUN mkdir -p /data/survey_results && chmod -R 777 /data
ENV SURVEY_RESULTS_DIR=/data/survey_results

EXPOSE 7860
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
