"""
api/v1/router.py

Main v1 API router that aggregates all domain-specific sub-routers.
New feature routers are registered here as they are built.
"""

from fastapi import APIRouter

from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.scores import router as scores_router
from app.api.v1.scores_read import router as scores_read_router
from app.api.v1.signals import router as signals_router

v1_router = APIRouter(prefix="/api/v1")

# --- Register sub-routers below as features are built ---

v1_router.include_router(
    ingestion_router, prefix="/ingest", tags=["Data Ingestion"]
)
v1_router.include_router(
    signals_router, prefix="/signals", tags=["Sector Signals"]
)
v1_router.include_router(
    scores_router, prefix="/scores", tags=["Scores"]
)
v1_router.include_router(
    scores_read_router, prefix="/scores", tags=["Scores"]
)
v1_router.include_router(
    jobs_router, prefix="/jobs", tags=["Background Jobs"]
)
