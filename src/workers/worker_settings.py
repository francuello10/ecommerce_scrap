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
    """ARQ job: Fetch new newsletter emails."""
    from core.database import async_session_factory
    from core.models import NewsletterAccount
    from workers.newsletter_monitor.imap_reader import ImapReader
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(NewsletterAccount).where(NewsletterAccount.is_active == True)
        )
        accounts = result.scalars().all()

        for account in accounts:
            reader = ImapReader(account)
            msgs = await reader.fetch_new_messages(session)
            print(f"  📧 {account.email_address}: {len(msgs)} new messages")


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
