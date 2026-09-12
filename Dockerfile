# Adaptive Game Model - Streamlit deployment container
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps required by some scientific wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# Copy application + source + processed data
COPY app ./app
COPY src ./src
COPY data ./data
COPY reports ./reports
COPY pyproject.toml .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["sh", "-c", "streamlit run app/Home.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
