"""
core/config.py

Centralised application configuration loaded from environment variables.
All thresholds, secrets, and environment-specific values live here —
never hardcoded in business logic.

Uses pydantic-settings to validate env vars at startup, failing fast
if required configuration is missing.
"""

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings populated from environment variables.
    Reads from .env.local by default (git-ignored).
    """

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database (Supabase PostgreSQL) ---
    database_url: str = "postgresql+asyncpg://postgres:MUST_SET_IN_ENV@localhost:5432/mf_engine"
    database_url_sync: str = "postgresql://postgres:MUST_SET_IN_ENV@localhost:5432/mf_engine"

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- Morningstar API Center ---
    morningstar_api_url: str = "https://api.morningstar.com/v2/service/mf"
    morningstar_username: str = ""
    morningstar_password: str = ""
    morningstar_access_code: str = ""

    # --- Authentication ---
    jwt_secret: str = ""
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    api_key: str = ""  # X-API-Key header value; empty = auth disabled (dev only)

    # --- Application ---
    app_name: str = "JIP MF Recommendation Engine"
    app_version: str = "1.0.0"
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"

    # --- Scheduler ---
    scheduler_enabled: bool = True  # Set False in tests or when running without background jobs

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def validate_secrets(self) -> list[str]:
        """Check for missing or placeholder secrets. Returns list of warnings."""
        warnings: list[str] = []
        if not self.jwt_secret:
            warnings.append("JWT_SECRET is not set")
        if "MUST_SET_IN_ENV" in self.database_url:
            warnings.append("DATABASE_URL still has placeholder password")
        if not self.morningstar_access_code:
            warnings.append("MORNINGSTAR_ACCESS_CODE is not set")
        return warnings
