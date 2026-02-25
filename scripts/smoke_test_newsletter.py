"""Smoke test: Trigger Newsletter Monitor."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workers.worker_settings import run_newsletter_reader

async def main():
    print("🚀 Starting Smoke Test: Newsletter Monitor")
    ctx = {}
    await run_newsletter_reader(ctx)
    print("🏁 Finished Newsletter Monitor")
    print("Próximos pasos: Revisar la tabla newsletter_message en Directus.")

if __name__ == "__main__":
    asyncio.run(main())
