"""
main.py

FastAPI application entry point for the JIP MF Recommendation Engine.

Responsibilities:
  - Application lifespan management (DB connect/disconnect, scheduler start/stop, logging init)
  - CORS middleware configuration
  - Router registration (health + v1 API)
  - Global exception handlers for AppException hierarchy

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.health import router as health_router
from app.api.v1.router import v1_router
from app.core.config import Settings
from app.core.database import close_db, init_db
from app.core.dependencies import get_settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.jobs.scheduler import start_scheduler, stop_scheduler

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Startup: configure logging, connect to database, start scheduler.
    Shutdown: stop scheduler, close database connections gracefully.
    """
    settings = get_settings()

    # --- Startup ---
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
        debug=settings.app_debug,
    )

    await init_db(settings)
    logger.info("database_connected", database_url=settings.database_url.split("@")[-1])

    # Start the background job scheduler (after DB is ready)
    await start_scheduler(settings)

    yield

    # --- Shutdown ---
    logger.info("application_shutting_down")

    # Stop the scheduler first (may have in-flight DB operations)
    await stop_scheduler()

    await close_db()
    logger.info("database_disconnected")


def create_app() -> FastAPI:
    """
    Application factory. Builds and configures the FastAPI instance.
    Separated from module-level `app` to support testing with overridden settings.
    """
    settings = get_settings()

    application = FastAPI(
        title="JIP MF Recommendation Engine",
        description=(
            "Quantitative fund scoring, FM sector alignment, and composite "
            "recommendation engine for mutual fund advisory."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # --- Rate Limiting ---
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- CORS Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    # --- Global Exception Handler ---
    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Convert AppException subclasses into structured JSON error responses."""
        logger.error(
            "app_exception",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=str(request.url),
            method=request.method,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details if exc.details else None,
                },
            },
        )

    # --- Routers ---
    application.include_router(health_router)
    application.include_router(v1_router)

    return application


app = create_app()
