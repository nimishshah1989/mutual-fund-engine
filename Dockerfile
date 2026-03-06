# =============================================================================
# JIP MF Recommendation Engine — Production Dockerfile
#
# Multi-stage build:
#   Stage 1 (frontend): Build Next.js standalone output
#   Stage 2 (runtime):  Python 3.11 + Node.js 20, runs FastAPI + Next.js
#
# Exposed port: 3000 (Next.js, which proxies /api/* to FastAPI on 127.0.0.1:8000)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build Next.js frontend
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies first (cache layer)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY frontend/ ./

# Empty string so frontend makes relative API calls (proxied by Next.js rewrites)
ENV NEXT_PUBLIC_API_URL=""

RUN pnpm build

# ---------------------------------------------------------------------------
# Stage 2: Production runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Install Node.js 20 for Next.js standalone server
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini

# Copy Next.js standalone output (server.js + node_modules at root of standalone/)
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Copy startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Validate all Python imports resolve at build time (catches missing deps)
RUN python -c "\
from app.main import app; \
from app.api.health import router; \
from app.api.v1.ingestion import router; \
from app.api.v1.scores import router; \
from app.api.v1.scores_read import router; \
from app.api.v1.signals import router; \
from app.api.v1.jobs import router; \
from app.api.v1.pulse import router; \
print('All imports OK')"

# Only port 3000 is exposed (FastAPI is internal on 127.0.0.1:8000)
EXPOSE 3000

# Health check — validates both FastAPI and Next.js are responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" && \
      node -e "const h=require('http');h.get('http://127.0.0.1:3000',r=>{process.exit(r.statusCode===200?0:1)}).on('error',()=>process.exit(1))"

CMD ["./start.sh"]
