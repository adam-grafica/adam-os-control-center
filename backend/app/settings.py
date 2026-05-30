"""ADAM OS Dashboard — Application Settings

Reads configuration from environment variables with .env file fallback.
Uses pydantic-settings for validated, typed settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level settings for the ADAM OS Dashboard backend.

    All values are read from environment variables, with `.env` file support.
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Security ──
    AUTH_ENABLED: bool = Field(
        default=True, description="Enable Bearer token authentication"
    )
    API_TOKEN: str = Field(
        default="", validation_alias="API_TOKEN", description="Bearer token for API auth"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["https://adam-os-control-center.app.adamcloud.net"],
        description="Allowed CORS origins",
    )
    FILES_WRITE_ENABLED: bool = Field(
        default=False, description="Allow file write operations via API"
    )

    # ── Paths ──
    ADAM_OS_ROOT: str = Field(
        default_factory=lambda: (
            "/app/data"
            if os.path.exists("/.dockerenv") or os.path.exists("/app/backend")
            else "/home/adamcloud/adam-os-system"
        ),
        description="Root directory of the ADAM OS system",
    )
    STATE_DB_PATH: str = Field(
        default="/app/backend/seed/state.db",
        description="Path to the SQLite state database",
    )
    HERMES_DB_PATH: str = Field(
        default_factory=lambda: (
            "/app/data/hermes_state.db"
            if os.path.exists("/.dockerenv") or os.path.exists("/app/backend")
            else "/home/adamcloud/.hermes/profiles/axon/state.db"
        ),
        description="Path to Hermes Agent's SQLite session state database",
    )

    # ── Server ──
    API_HOST: str = Field(default="0.0.0.0", description="Host to bind the API server")
    API_PORT: int = Field(default=8000, description="Port to bind the API server")

    # ── Caching ──
    SNAPSHOT_CACHE_TTL: int = Field(
        default=5, description="TTL in seconds for snapshot cache"
    )

    # ── Events ──
    EVENTS_HISTORY_LIMIT: int = Field(
        default=100, description="Default limit for event history queries"
    )

    # ── SSE ──
    SSE_HEARTBEAT: int = Field(
        default=30, description="Interval in seconds for SSE heartbeat pings"
    )

    # ── Debug / Logging ──
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    @field_validator("STATE_DB_PATH")
    @classmethod
    def resolve_state_db_path(cls, v: str) -> str:
        """Resolve STATE_DB_PATH, falling back to root-relative if not absolute."""
        p = Path(v)
        if p.is_absolute():
            return str(p.resolve())
        return str(p)

    @property
    def frontend_build_path(self) -> str:
        """Path to the built frontend static files."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "frontend",
            "build",
        )


# Module-level singleton
settings = Settings()
