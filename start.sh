#!/bin/bash
# =============================================================================
# MF Engine — Production Startup Script
#
# Starts both processes inside the container:
#   1. FastAPI on 127.0.0.1:8000 (internal only, single worker for APScheduler)
#   2. Next.js standalone on 0.0.0.0:3000 (exposed, proxies /api/* to FastAPI)
# =============================================================================

set -e

# Run Alembic migrations before starting the app
echo "[mf-engine] Running database migrations..."
cd /app
python -m alembic upgrade head
echo "[mf-engine] Migrations complete."

echo "[mf-engine] Starting FastAPI backend on 127.0.0.1:8000..."
python -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --log-level info &

FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "[mf-engine] Waiting for FastAPI to start..."
for i in $(seq 1 30); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null; then
    echo "[mf-engine] FastAPI is ready."
    break
  fi
  if [ $i -eq 30 ]; then
    echo "[mf-engine] WARNING: FastAPI did not respond within 30s, starting Next.js anyway."
  fi
  sleep 1
done

echo "[mf-engine] Starting Next.js frontend on 0.0.0.0:3000..."
cd /app/frontend
HOSTNAME="0.0.0.0" PORT=3000 node server.js &

NEXTJS_PID=$!

# Trap signals to shut down both processes
trap "echo '[mf-engine] Shutting down...'; kill $FASTAPI_PID $NEXTJS_PID 2>/dev/null; wait" SIGTERM SIGINT

# Wait for either process to exit
wait -n $FASTAPI_PID $NEXTJS_PID

# If one exits, kill the other
echo "[mf-engine] A process exited. Shutting down..."
kill $FASTAPI_PID $NEXTJS_PID 2>/dev/null
wait
