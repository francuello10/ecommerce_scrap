"""Suggestion API — Competitor recommendations by industry."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db as get_session
from core.models import (
    CompetitorIndustry,
    CompetitorLevel,
    Industry,
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


# ── Response schemas ──────────────────────────────────────────────────

class CompetitorSuggestion(BaseModel):
    competitor_id: int
    name: str
    domain: str
    level: str

class SuggestionGroup(BaseModel):
    level: str
    label: str
    competitors: list[CompetitorSuggestion]

class IndustryResponse(BaseModel):
    industry_id: int
    name: str
    slug: str
    icon_emoji: str | None
    groups: list[SuggestionGroup]


# ── Level display labels ──────────────────────────────────────────────

_LEVEL_LABELS = {
    CompetitorLevel.GLOBAL_BENCHMARK: "🌍 Global Benchmarks",
    CompetitorLevel.REGIONAL_RIVAL: "🌎 Regional Rivals",
    CompetitorLevel.DIRECT_RIVAL: "🏠 Direct Rivals",
}

_LEVEL_ORDER = [
    CompetitorLevel.GLOBAL_BENCHMARK,
    CompetitorLevel.REGIONAL_RIVAL,
    CompetitorLevel.DIRECT_RIVAL,
]


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/industries", response_model=list[dict])
async def list_industries(session: AsyncSession = Depends(get_session)):
    """List all active industries."""
    result = await session.execute(
        select(Industry).where(Industry.is_active == True).order_by(Industry.name)
    )
    industries = result.scalars().all()
    return [
        {
            "id": ind.id,
            "name": ind.name,
            "slug": ind.slug,
            "icon_emoji": ind.icon_emoji,
            "description": ind.description,
        }
        for ind in industries
    ]


@router.get("/{industry_slug}", response_model=IndustryResponse)
async def get_suggestions(
    industry_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get competitor suggestions for an industry, grouped by level.

    Returns competitors organized as:
    - 🌍 Global Benchmarks (world-class references)
    - 🌎 Regional Rivals (LATAM/regional)
    - 🏠 Direct Rivals (national/local)
    """
    result = await session.execute(
        select(Industry).where(Industry.slug == industry_slug)
    )
    industry = result.scalar_one_or_none()

    if not industry:
        raise HTTPException(status_code=404, detail=f"Industry '{industry_slug}' not found")

    # Fetch all suggestions with competitor data
    result = await session.execute(
        select(CompetitorIndustry)
        .where(
            CompetitorIndustry.industry_id == industry.id,
            CompetitorIndustry.is_suggested == True,
        )
        .options(selectinload(CompetitorIndustry.competitor))
        .order_by(CompetitorIndustry.level)
    )
    links = result.scalars().all()

    # Group by level
    groups_by_level: dict[CompetitorLevel, list[CompetitorSuggestion]] = {
        level: [] for level in _LEVEL_ORDER
    }

    for link in links:
        suggestion = CompetitorSuggestion(
            competitor_id=link.competitor.id,
            name=link.competitor.name,
            domain=link.competitor.domain,
            level=link.level.value,
        )
        groups_by_level[link.level].append(suggestion)

    groups = [
        SuggestionGroup(
            level=level.value,
            label=_LEVEL_LABELS[level],
            competitors=competitors,
        )
        for level, competitors in groups_by_level.items()
        if competitors  # only include non-empty groups
    ]

    return IndustryResponse(
        industry_id=industry.id,
        name=industry.name,
        slug=industry.slug,
        icon_emoji=industry.icon_emoji,
        groups=groups,
    )
