"""
FastAPI application entry point.

Minimal app setup for MVP. Endpoints for health check
and manual job triggering.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from api.routes.suggestions import router as suggestions_router
from api.routes.onboarding import router as onboarding_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup/shutdown events."""
    # Startup
    # TODO: Initialize ARQ connection pool here
    yield
    # Shutdown
    # TODO: Cleanup connections


app = FastAPI(
    title="Competitive Intelligence Engine",
    description="Motor de inteligencia competitiva para eCommerce",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Routes ────────────────────────────────────────────────────────────
app.include_router(suggestions_router)
app.include_router(onboarding_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "competitive-intelligence-engine"}
