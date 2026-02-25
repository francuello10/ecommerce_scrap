"""
Configuration management with pydantic-settings.

Todas las variables de entorno se validan al iniciar la aplicación.
Si falta una variable requerida, el sistema falla inmediatamente
con un mensaje claro (fail-fast).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────
    database_url: str = Field(
        description="Async connection string (postgresql+asyncpg://...)",
    )
    database_url_sync: str = Field(
        default="",
        description="Sync connection string for Alembic (postgresql://...)",
    )

    # ── Redis / ARQ ───────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for ARQ workers.",
    )

    # ── Notifications ─────────────────────────────────────────────────
    slack_webhook_url: str = Field(
        default="",
        description="Slack incoming webhook URL for real-time alerts.",
    )

    # ── LLM (for brief generation — Phase 5) ──────────────────────────
    llm_api_key: str = Field(
        default="",
        description="API key for the LLM provider (OpenAI, Gemini etc.).",
    )
    llm_model: str = Field(
        default="gemini-1.5-flash",
        description="LLM model identifier.",
    )
    gemini_api_key: str = Field(
        default="",
        description="Gemini Specific API Key.",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI Specific API Key.",
    )

    # ── Google OAuth (for Directus or API) ───────────────────────────
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")

    # ── Directus ──────────────────────────────────────────────────────
    directus_key: str = Field(default="")
    directus_url: str = Field(default="http://localhost:8055")

    # ── Email IMAP ────────────────────────────────────────────────────
    email_server_host: str = Field(default="imap.gmail.com")
    email_server_port: int = Field(default=993)
    email_server_user: str = Field(default="")
    email_server_password: str = Field(default="")
    email_from: str = Field(default="")


# Singleton instance — import this everywhere
settings = Settings()  # type: ignore[call-arg]
