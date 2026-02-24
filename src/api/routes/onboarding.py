"""Onboarding API — Client and Competitor identification."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Client, Competitor, Industry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


# ── Request/Response Schemas ──────────────────────────────────────────

class IdentifyRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_slug: str
    company_name: str
    company_domain: str
    industry_slug: str
    custom_industry_name: Optional[str] = None


class IdentifyResponse(BaseModel):
    client_id: int
    competitor_id: int
    industry_id: int
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/identify", response_model=IdentifyResponse)
async def identify_client_and_company(
    req: IdentifyRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Onboarding Phase 1: Identify the client and their company.

    Steps:
    1. Resolve Industry (by slug or create new if requested).
    2. Resolve Competitor (by domain or create new).
    3. Resolve/Create Client.
    4. Link Client to Industry.
    """
    # 1. Resolve Industry
    industry_result = await session.execute(
        select(Industry).where(Industry.slug == req.industry_slug)
    )
    industry = industry_result.scalar_one_or_none()

    if not industry:
        if req.industry_slug == "other" and req.custom_industry_name:
            # Create a new industry placeholder for "other"
            # In a real app, this might go to a moderation queue
            industry = Industry(
                name=req.custom_industry_name,
                slug=req.custom_industry_name.lower().replace(" ", "-"),
                description="Custom industry created during onboarding",
                is_active=False,  # Needs approval
            )
            session.add(industry)
            await session.flush()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Industry '{req.industry_slug}' not found and no custom name provided"
            )

    # 2. Resolve Competitor (the client's own company is treated as a competitor in our system)
    domain = req.company_domain.lower().strip()
    competitor_result = await session.execute(
        select(Competitor).where(Competitor.domain == domain)
    )
    competitor = competitor_result.scalar_one_or_none()

    if not competitor:
        competitor = Competitor(
            name=req.company_name,
            domain=domain,
            country="AR", # Default
        )
        session.add(competitor)
        await session.flush()
        logger.info("Created new competitor during onboarding: %s", domain)

    # 3. Resolve/Create Client
    client_result = await session.execute(
        select(Client).where(Client.slug == req.client_slug)
    )
    client = client_result.scalar_one_or_none()

    if not client:
        client = Client(
            name=req.client_name,
            slug=req.client_slug,
            contact_email=req.client_email,
            industry_id=industry.id,
        )
        session.add(client)
        await session.flush()
        logger.info("Created new client: %s", req.client_slug)
    else:
        # Update existing client's industry if changed
        client.industry_id = industry.id

    await session.commit()

    return IdentifyResponse(
        client_id=client.id,
        competitor_id=competitor.id,
        industry_id=industry.id,
        message="Identification successful. Proceed to competitor selection."
    )
