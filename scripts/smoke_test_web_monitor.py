"""Smoke test: Trigger a Web Monitor run for Newsport."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from core.database import async_session_factory
from core.models import Competitor, MonitoredPage, PageType, CompetitorStatus
from workers.web_monitor.orchestrator import run_web_monitor

async def main():
    print("🚀 Starting Smoke Test: Web Monitor Pipeline")
    
    async with async_session_factory() as session:
        # 1. Ensure Newsport exists and has a homepage to monitor
        result = await session.execute(
            select(Competitor).where(Competitor.domain == "newsport.com.ar")
        )
        newsport = result.scalar_one_or_none()
        
        if not newsport:
            print("  ➕ Creating Newsport competitor...")
            newsport = Competitor(
                name="Newsport",
                domain="newsport.com.ar",
                country="AR",
                status=CompetitorStatus.ACTIVE
            )
            session.add(newsport)
            await session.flush()
        
        # 2. Ensure MonitoredPage exists
        result = await session.execute(
            select(MonitoredPage).where(
                MonitoredPage.competitor_id == newsport.id,
                MonitoredPage.page_type == PageType.HOMEPAGE
            )
        )
        page = result.scalar_one_or_none()
        
        if not page:
            print("  ➕ Creating Homepage monitored page...")
            page = MonitoredPage(
                competitor_id=newsport.id,
                url="https://www.newsport.com.ar/",
                page_type=PageType.HOMEPAGE,
                is_active=True
            )
            session.add(page)
        
        await session.commit()
        print(f"  ✅ Newsport set up (ID: {newsport.id}, Page ID: {page.id})")

        # 3. Trigger Orchestrator
        print("\n🔍 Running Orchestrator...")
        ctx = {"session": session}
        result = await run_web_monitor(ctx)
        
        print(f"\n🏁 Finished: {result}")
        print("\nPróximos pasos: Revisar las tablas page_snapshot, detected_signal y competitor_tech_profile.")

if __name__ == "__main__":
    asyncio.run(main())
