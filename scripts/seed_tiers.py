"""
Seed script — inserts the 3 initial subscription tiers.
Run once after the first migration:

    PYTHONPATH=src uv run python scripts/seed_tiers.py
    # or simply: make db-seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import settings
from core.models import SubscriptionTier, MonitoringFrequency


TIERS = [
    {
        "name": "BASIC",
        "max_competitors": 3,
        "max_monitored_pages": 5,
        "monitoring_frequency": MonitoringFrequency.LOW,
        "history_retention_days": 30,
        "can_track_newsletters": False,
        "can_track_tech_stack": False,
        "can_track_catalog": False,
        "can_use_realtime_alerts": False,
        "can_access_api": False,
        "can_generate_weekly_brief": False,
        "can_use_baseline_comparison": False,
        "price_monthly_usd": 49.0,
    },
    {
        "name": "PROFESSIONAL",
        "max_competitors": 10,
        "max_monitored_pages": 20,
        "monitoring_frequency": MonitoringFrequency.MEDIUM,
        "history_retention_days": 90,
        "can_track_newsletters": True,
        "can_track_tech_stack": True,
        "can_track_catalog": False,
        "can_use_realtime_alerts": True,
        "can_access_api": False,
        "can_generate_weekly_brief": True,
        "can_use_baseline_comparison": False,
        "price_monthly_usd": 149.0,
    },
    {
        "name": "ENTERPRISE",
        "max_competitors": 9999,  # unlimited
        "max_monitored_pages": 9999,  # unlimited
        "monitoring_frequency": MonitoringFrequency.HIGH,
        "history_retention_days": -1,  # unlimited
        "can_track_newsletters": True,
        "can_track_tech_stack": True,
        "can_track_catalog": True,
        "can_use_realtime_alerts": True,
        "can_access_api": True,
        "can_generate_weekly_brief": True,
        "can_use_baseline_comparison": True,
        "price_monthly_usd": 499.0,
    },
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        for tier_data in TIERS:
            existing = await session.execute(
                select(SubscriptionTier).where(SubscriptionTier.name == tier_data["name"])
            )
            if existing.scalar_one_or_none() is not None:
                print(f"  ⚠️  Tier '{tier_data['name']}' already exists — skipping.")
                continue

            tier = SubscriptionTier(**tier_data)
            session.add(tier)
            print(f"  ✅ Tier '{tier_data['name']}' creado — ${tier_data['price_monthly_usd']}/mes")

        await session.commit()
        print("\n🎉 Seed completado.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
