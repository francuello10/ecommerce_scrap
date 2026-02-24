"""
ARQ Worker Settings — Registers all background jobs.

Usage:
    arq src.workers.worker_settings.WorkerSettings
"""

from __future__ import annotations

from arq.connections import RedisSettings

from core.config import settings


async def run_web_monitor(ctx: dict) -> None:
    """ARQ job: Run the web monitor pipeline."""
    from workers.web_monitor.orchestrator import run_web_monitor as _run
    await _run(ctx)


async def run_newsletter_reader(ctx: dict) -> None:
    """ARQ job: Full Newsletter Monitor pipeline."""
    from core.database import async_session_factory
    from core.models import NewsletterAccount, Competitor, NewsletterStatus, SignalSource
    from workers.newsletter_monitor.imap_reader import ImapReader
    from workers.newsletter_monitor.parser import NewsletterParser
    from workers.newsletter_monitor.auto_subscriber import AutoSubscriber
    from sqlalchemy import select

    async with async_session_factory() as session:
        # 1. Fetch accounts
        result = await session.execute(
            select(NewsletterAccount).where(NewsletterAccount.is_active == True)
        )
        accounts = result.scalars().all()

        for account in accounts:
            reader = ImapReader(account)
            # Fetch last 24h
            msgs = await reader.fetch_new_messages(session)
            
            for msg in msgs:
                # If it's opt-in, we should handle it (simplified: just log for now)
                if msg.is_optin_confirmation:
                    logger.info("  📩 Opt-in detected in %s", msg.subject)
                    # TODO: Extract link and visit with Playwright
                
                # Parse signals if we have HTML (ImapReader should save it)
                # For MVP, we'll assume HTML is available in msg.raw_html_path or just pass body
                # Simplified: skip for now as ImapReader needs to save the raw body
                
        # 2. Check for PENDING_AUTO competitors to subscribe
        result = await session.execute(
            select(Competitor).where(Competitor.newsletter_status == NewsletterStatus.PENDING_AUTO)
        )
        to_subscribe = result.scalars().all()
        
        if to_subscribe:
            for account in accounts:
                subscriber = AutoSubscriber(account.email_address)
                for comp in to_subscribe:
                    status = await subscriber.subscribe(comp)
                    logger.info("  📫 Auto-sub for %s: %s", comp.domain, status)
                    if status == "SUCCESS":
                        comp.newsletter_status = NewsletterStatus.PENDING_OPTIN
                    elif status == "FAILED_CAPTCHA":
                        comp.newsletter_status = NewsletterStatus.PENDING_MANUAL
                    
        await session.commit()



async def run_daily_brief(ctx: dict) -> None:
    """ARQ job: Generate the daily intelligence brief."""
    from core.database import async_session_factory
    from workers.briefing.generator import generate_daily_brief

    async with async_session_factory() as session:
        brief = await generate_daily_brief(session)
        print(f"  📊 Daily brief generated: {brief.brief_date}")


async def startup(ctx: dict) -> None:
    """Called on worker startup."""
    pass


async def shutdown(ctx: dict) -> None:
    """Called on worker shutdown."""
    pass


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [
        run_web_monitor,
        run_newsletter_reader,
        run_daily_brief,
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # Cron schedule
    cron_jobs = [
        # Web monitor: every 4 hours
        # cron(run_web_monitor, hour={0, 4, 8, 12, 16, 20}),
        # Newsletter: every 6 hours
        # cron(run_newsletter_reader, hour={6, 12, 18, 0}),
        # Daily brief: every day at 7 AM
        # cron(run_daily_brief, hour={7}, minute={0}),
    ]
