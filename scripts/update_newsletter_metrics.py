"""
Update Newsletter Metrics

Calculates and updates metrics for each competitor:
- last_newsletter_received_at
- days_since_last_newsletter
- avg_days_between_newsletters

Intended to run daily via cron/arq.
"""
import asyncio
import logging
from datetime import datetime, timezone
import argparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory
from core.models import Competitor, NewsletterMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("metrics_updater")

async def update_competitor_metrics(session: AsyncSession, competitor: Competitor) -> None:
    # Fetch all newsletter messages for this competitor, ordered by date
    stmt = select(NewsletterMessage.received_at).where(
        NewsletterMessage.competitor_id == competitor.id
    ).order_by(NewsletterMessage.received_at.asc())
    
    res = await session.execute(stmt)
    dates = [row[0] for row in res.fetchall()]
    
    if not dates:
        logger.debug("Competitor %s has no newsletters.", competitor.domain)
        return

    # Calculate Last Received
    last_received = dates[-1]
    competitor.last_newsletter_received_at = last_received
    
    # Calculate Days Since Last (relative to now)
    now = datetime.now(timezone.utc)
    # Ensure timezone awareness matches
    if last_received.tzinfo is None:
        last_received = last_received.replace(tzinfo=timezone.utc)
        
    delta = now - last_received
    competitor.days_since_last_newsletter = delta.days
    
    # Calculate Average Days Between
    if len(dates) > 1:
        total_diff_days = 0
        for i in range(1, len(dates)):
            diff = dates[i] - dates[i-1]
            total_diff_days += diff.total_seconds() / 86400.0
        avg_days = total_diff_days / (len(dates) - 1)
        competitor.avg_days_between_newsletters = avg_days
    else:
        competitor.avg_days_between_newsletters = None

    logger.info("Updated %s: Last=%s, DaysSince=%s, AvgBetween=%.2f",
                competitor.domain,
                last_received.date(),
                competitor.days_since_last_newsletter,
                competitor.avg_days_between_newsletters or 0)

async def async_main():
    async with async_session_factory() as session:
        # Fetch all competitors
        stmt = select(Competitor)
        res = await session.execute(stmt)
        competitors = res.scalars().all()
        
        logger.info("Parsing metrics for %d competitors...", len(competitors))
        for comp in competitors:
            await update_competitor_metrics(session, comp)
            
        await session.commit()
        logger.info("Newsletter metrics updated successfully.")

if __name__ == "__main__":
    asyncio.run(async_main())
