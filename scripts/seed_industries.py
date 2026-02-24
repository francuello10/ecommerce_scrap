"""
Seed script: Populate industries and assign competitors to them.

Creates ~10 initial industries and links existing competitors to
their industry with a CompetitorLevel (GLOBAL/REGIONAL/DIRECT).

Usage:
    PYTHONPATH=src uv run python scripts/seed_industries.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.config import settings
from core.models import (
    Competitor,
    CompetitorIndustry,
    CompetitorLevel,
    Industry,
)

# ── Industry definitions ────────────────────────────────────────────

INDUSTRIES = [
    {"name": "Deportes", "slug": "deportes", "icon_emoji": "⚽", "description": "Indumentaria y equipamiento deportivo"},
    {"name": "Electrónica", "slug": "electronica", "icon_emoji": "📱", "description": "Tecnología, gadgets, computación"},
    {"name": "Moda", "slug": "moda", "icon_emoji": "👗", "description": "Ropa, calzado, accesorios de moda"},
    {"name": "Hogar", "slug": "hogar", "icon_emoji": "🏠", "description": "Muebles, decoración, electrodomésticos"},
    {"name": "Farma & Belleza", "slug": "farma-belleza", "icon_emoji": "💊", "description": "Farmacia, cosmética, cuidado personal"},
    {"name": "Alimentos & Bebidas", "slug": "alimentos-bebidas", "icon_emoji": "🍷", "description": "Supermercados, bebidas, gourmet"},
    {"name": "Automotriz", "slug": "automotriz", "icon_emoji": "🚗", "description": "Repuestos, accesorios, neumáticos"},
    {"name": "Mascotas", "slug": "mascotas", "icon_emoji": "🐾", "description": "Alimento, accesorios para mascotas"},
    {"name": "Juguetes & Niños", "slug": "juguetes-ninos", "icon_emoji": "🧸", "description": "Juguetería, ropa infantil"},
    {"name": "Construcción & Ferretería", "slug": "construccion-ferreteria", "icon_emoji": "🔨", "description": "Materiales, herramientas, ferretería"},
]

# ── Competitor suggestions per industry ─────────────────────────────
# These are pre-loaded when the industry is created.
# Format: (domain, name, level)

COMPETITOR_SUGGESTIONS: dict[str, list[tuple[str, str, CompetitorLevel]]] = {
    "deportes": [
        # Global Benchmarks
        ("nike.com", "Nike", CompetitorLevel.GLOBAL_BENCHMARK),
        ("adidas.com", "Adidas", CompetitorLevel.GLOBAL_BENCHMARK),
        ("underarmour.com", "Under Armour", CompetitorLevel.GLOBAL_BENCHMARK),
        # Regional Rivals
        ("dafiti.com.ar", "Dafiti", CompetitorLevel.REGIONAL_RIVAL),
        ("netshoes.com.ar", "Netshoes", CompetitorLevel.REGIONAL_RIVAL),
        # Direct Rivals
        ("newsport.com.ar", "Newsport", CompetitorLevel.DIRECT_RIVAL),
        ("dexter.com.ar", "Dexter", CompetitorLevel.DIRECT_RIVAL),
        ("moov.com.ar", "Moov", CompetitorLevel.DIRECT_RIVAL),
        ("sportline.com.ar", "Sportline", CompetitorLevel.DIRECT_RIVAL),
    ],
    "electronica": [
        ("amazon.com", "Amazon", CompetitorLevel.GLOBAL_BENCHMARK),
        ("bestbuy.com", "Best Buy", CompetitorLevel.GLOBAL_BENCHMARK),
        ("mercadolibre.com.ar", "MercadoLibre", CompetitorLevel.REGIONAL_RIVAL),
        ("fravega.com", "Frávega", CompetitorLevel.DIRECT_RIVAL),
        ("garbarino.com", "Garbarino", CompetitorLevel.DIRECT_RIVAL),
        ("musimundo.com", "Musimundo", CompetitorLevel.DIRECT_RIVAL),
        ("megatone.net", "Megatone", CompetitorLevel.DIRECT_RIVAL),
    ],
    "moda": [
        ("zara.com", "Zara", CompetitorLevel.GLOBAL_BENCHMARK),
        ("hm.com", "H&M", CompetitorLevel.GLOBAL_BENCHMARK),
        ("shein.com", "Shein", CompetitorLevel.REGIONAL_RIVAL),
        ("dafiti.com.ar", "Dafiti", CompetitorLevel.REGIONAL_RIVAL),
        ("rapsodia.com.ar", "Rapsodia", CompetitorLevel.DIRECT_RIVAL),
        ("kosiuko.com.ar", "Kosiuko", CompetitorLevel.DIRECT_RIVAL),
        ("akiabara.com.ar", "Akiabara", CompetitorLevel.DIRECT_RIVAL),
    ],
}


def main() -> None:
    engine = create_engine(
        settings.database_url_sync or settings.database_url.replace("+asyncpg", "")
    )

    with Session(engine) as session:
        created_industries = 0
        created_competitors = 0
        created_links = 0

        # Upsert industries
        for ind_data in INDUSTRIES:
            existing = session.execute(
                select(Industry).where(Industry.slug == ind_data["slug"])
            ).scalar_one_or_none()

            if existing:
                print(f"  ⏭️  Industry '{ind_data['name']}' already exists")
                continue

            industry = Industry(**ind_data)
            session.add(industry)
            session.flush()
            created_industries += 1
            print(f"  ✅ Created industry: {ind_data['icon_emoji']} {ind_data['name']}")

        session.commit()

        # Upsert competitor suggestions
        for industry_slug, suggestions in COMPETITOR_SUGGESTIONS.items():
            industry = session.execute(
                select(Industry).where(Industry.slug == industry_slug)
            ).scalar_one_or_none()

            if not industry:
                print(f"  ⚠️  Industry '{industry_slug}' not found, skipping")
                continue

            for domain, name, level in suggestions:
                # Find or create competitor
                competitor = session.execute(
                    select(Competitor).where(Competitor.domain == domain)
                ).scalar_one_or_none()

                if not competitor:
                    competitor = Competitor(name=name, domain=domain, country="AR")
                    session.add(competitor)
                    session.flush()
                    created_competitors += 1

                # Check if link exists
                link = session.execute(
                    select(CompetitorIndustry).where(
                        CompetitorIndustry.competitor_id == competitor.id,
                        CompetitorIndustry.industry_id == industry.id,
                    )
                ).scalar_one_or_none()

                if not link:
                    link = CompetitorIndustry(
                        competitor_id=competitor.id,
                        industry_id=industry.id,
                        level=level,
                        is_suggested=True,
                    )
                    session.add(link)
                    created_links += 1
                    print(f"    [{level.value:18s}] {name:20s} → {industry.name}")

        session.commit()

        print(f"\n🏁 Done: {created_industries} industries, {created_competitors} competitors, {created_links} links")


if __name__ == "__main__":
    main()
