"""
setup_overnight_showcase.py
==========================
Creates a real-world monitoring environment for the overnight run.
Adds major Argentine retailers across multiple industries.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from core.database import async_session_factory
from core.models import (
    Client, 
    Competitor, 
    Industry, 
    MonitoredPage, 
    PageType, 
    CompetitorStatus,
    NewsletterStatus,
    NewsletterAccount,
    NewsletterSubscription,
    ClientCompetitor,
    CompetitorIndustry,
    CompetitorLevel
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

COMPETITORS_DATA = [
    # Deportes
    {"name": "Newsport", "domain": "newsport.com.ar", "industry": "Deportes", "homepage": "https://www.newsport.com.ar/", "level": CompetitorLevel.DIRECT_RIVAL},
    {"name": "Adidas AR", "domain": "adidas.com.ar", "industry": "Deportes", "homepage": "https://www.adidas.com.ar/", "level": CompetitorLevel.REGIONAL_RIVAL},
    {"name": "Nike AR", "domain": "nike.com.ar", "industry": "Deportes", "homepage": "https://www.nike.com.ar/", "level": CompetitorLevel.GLOBAL_BENCHMARK},
    
    # Moda
    {"name": "Dafiti", "domain": "dafiti.com.ar", "industry": "Moda", "homepage": "https://www.dafiti.com.ar/", "level": CompetitorLevel.REGIONAL_RIVAL},
    
    # Electrónica
    {"name": "Frávega", "domain": "fravega.com", "industry": "Electrónica", "homepage": "https://www.fravega.com/", "level": CompetitorLevel.DIRECT_RIVAL},
    {"name": "Cetrogar", "domain": "cetrogar.com.ar", "industry": "Electrónica", "homepage": "https://www.cetrogar.com.ar/", "level": CompetitorLevel.DIRECT_RIVAL},
]

async def setup():
    async with async_session_factory() as session:
        # 1. Ensure Showcase Client exists
        res = await session.execute(select(Client).where(Client.contact_email == "showcase@intelligence.ai"))
        client = res.scalar_one_or_none()
        if not client:
            client = Client(
                name="Showcase Admin",
                slug="showcase-admin",
                contact_email="showcase@intelligence.ai",
                tier_id=3, # Enterprise
                is_active=True
            )
            session.add(client)
            await session.flush()
            logger.info("Created Showcase Client")

        # 2. Get Newsletter Account
        res = await session.execute(select(NewsletterAccount).limit(1))
        account = res.scalar_one_or_none()
        if not account:
            logger.error("No NewsletterAccount found. Run seed first.")
            return

        # 3. Add Competitors and Pages
        for comp_data in COMPETITORS_DATA:
            # Get industry
            res = await session.execute(select(Industry).where(Industry.name == comp_data["industry"]))
            industry = res.scalar_one_or_none()
            if not industry:
                industry = Industry(name=comp_data["industry"], slug=comp_data["industry"].lower())
                session.add(industry)
                await session.flush()

            # Create competitor if missing
            res = await session.execute(select(Competitor).where(Competitor.domain == comp_data["domain"]))
            comp = res.scalar_one_or_none()
            if not comp:
                comp = Competitor(
                    name=comp_data["name"],
                    domain=comp_data["domain"],
                    vertical=comp_data["industry"],
                    status=CompetitorStatus.ACTIVE
                )
                session.add(comp)
                await session.flush()
                logger.info(f"Added Competitor: {comp.name}")

            # Link Competitor to Client
            res = await session.execute(
                select(ClientCompetitor).where(
                    ClientCompetitor.client_id == client.id,
                    ClientCompetitor.competitor_id == comp.id
                )
            )
            if not res.scalar_one_or_none():
                session.add(ClientCompetitor(client_id=client.id, competitor_id=comp.id))

            # Link Competitor to Industry
            res = await session.execute(
                select(CompetitorIndustry).where(
                    CompetitorIndustry.competitor_id == comp.id,
                    CompetitorIndustry.industry_id == industry.id
                )
            )
            if not res.scalar_one_or_none():
                session.add(CompetitorIndustry(
                    competitor_id=comp.id, 
                    industry_id=industry.id,
                    level=comp_data["level"]
                ))

            # Subscribe to Newsletter
            res = await session.execute(
                select(NewsletterSubscription).where(
                    NewsletterSubscription.competitor_id == comp.id,
                    NewsletterSubscription.newsletter_account_id == account.id
                )
            )
            if not res.scalar_one_or_none():
                session.add(NewsletterSubscription(
                    competitor_id=comp.id,
                    newsletter_account_id=account.id,
                    status=NewsletterStatus.PENDING_AUTO
                ))

            # Add homepage
            res = await session.execute(
                select(MonitoredPage).where(
                    MonitoredPage.competitor_id == comp.id,
                    MonitoredPage.url == comp_data["homepage"]
                )
            )
            if not res.scalar_one_or_none():
                page = MonitoredPage(
                    competitor_id=comp.id,
                    url=comp_data["homepage"],
                    page_type=PageType.HOMEPAGE,
                    is_active=True
                )
                session.add(page)
                logger.info(f"  + Added MonitoredPage: {page.url}")

        await session.commit()
        logger.info("✅ Showcase setup complete.")

if __name__ == "__main__":
    asyncio.run(setup())
