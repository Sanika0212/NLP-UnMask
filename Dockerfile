FROM python:3.11-slim

WORKDIR /app

# Install deps — skip torch/transformers (not used at runtime)
COPY requirements.txt .
RUN pip install --no-cache-dir $(grep -v -E "^(torch|transformers|ragas|#|$)" requirements.txt | tr '\n' ' ')

COPY . .

# HF Spaces runs as non-root; pre-create writable dirs
RUN mkdir -p /data/survey_results && chmod -R 777 /data

ENV SURVEY_RESULTS_DIR=/data/survey_results
ENV CHAINLIT_AUTH_SECRET=unmask-pilot-2025

EXPOSE 7860
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "7860"]
