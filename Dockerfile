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

# Install Node.js + nginx + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm nginx supervisor curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (skip heavy ML-only packages not needed at runtime)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    $(grep -v -E "^(torch|transformers|ragas|sentence.transformers|#|$)" requirements.txt | tr '\n' ' ')

# Copy backend source
COPY . .

# Copy built Next.js standalone server
COPY --from=frontend-builder /frontend/.next/standalone ./frontend-server
COPY --from=frontend-builder /frontend/.next/static ./frontend-server/.next/static
COPY --from=frontend-builder /frontend/public ./frontend-server/public

# nginx routes port 7860 → Next.js; Next.js rewrites proxy /api/* → FastAPI
RUN printf 'server {\n    listen 7860;\n    location / {\n        proxy_pass http://127.0.0.1:3000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_buffering off;\n    }\n}\n' > /etc/nginx/sites-enabled/default

# supervisor config
RUN printf '[supervisord]\nnodaemon=true\nlogfile=/dev/null\nlogfile_maxbytes=0\n\n[program:api]\ncommand=uvicorn src.api:app --host 0.0.0.0 --port 8000\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n\n[program:frontend]\ncommand=node /app/frontend-server/server.js\nautostart=true\nautorestart=true\nenvironment=PORT="3000",HOSTNAME="127.0.0.1",BACKEND_URL="http://127.0.0.1:8000"\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n\n[program:nginx]\ncommand=nginx -g "daemon off;"\nautostart=true\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n' > /etc/supervisor/conf.d/unmask.conf

RUN mkdir -p /data/survey_results && chmod -R 777 /data
ENV SURVEY_RESULTS_DIR=/data/survey_results

EXPOSE 7860
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
