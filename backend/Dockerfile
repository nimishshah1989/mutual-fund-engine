# =============================================================================
# Dockerfile — JIP MF Recommendation Engine
#
# Multi-stage build for Railway deployment.
# Python 3.11 slim base, installs dependencies, runs with uvicorn.
# Port is read from $PORT env var (Railway sets this automatically).
# =============================================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by psycopg2-binary and lxml
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -- Dependency installation layer (cached unless requirements change) --
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -- Application code --
COPY . .

# Default port — Railway overrides this via $PORT env var
ENV PORT=8000

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Run with uvicorn — workers=1 because APScheduler runs in-process
# and must not be duplicated across workers
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --log-level info
