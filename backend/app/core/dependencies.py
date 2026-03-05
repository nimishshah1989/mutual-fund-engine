"""
core/dependencies.py

Shared FastAPI dependencies injected via Depends().
Centralised here so that routes import from one place,
and swapping implementations (e.g., for testing) is straightforward.
"""

from functools import lru_cache

from app.core.config import Settings
from app.core.database import get_db  # noqa: F401 — re-exported for convenience


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    lru_cache ensures the .env file is read only once per process.
    """
    return Settings()
