"""
Seed script — Populates Directus-visible initial data.
Inserts: newsletter_account, signal_taxonomy entries, first test competitor.

Run:  PYTHONPATH=src uv run python scripts/seed_initial_data.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import settings
from core.models import (
    Competitor, CompetitorStatus,
    NewsletterAccount,
    SignalTaxonomy, SignalType,
)


TAXONOMIES = [
    {"name": "Descuento porcentual",     "type": SignalType.PROMO,          "description": "Ej: '30% OFF', '2x1'"},
    {"name": "Precio tachado",           "type": SignalType.PROMO,          "description": "Precio original visible con precio promo"},
    {"name": "Cuotas sin interés",       "type": SignalType.FINANCIACION,   "description": "Ej: '12 cuotas sin interés con Visa'"},
    {"name": "Cuotas con interés",       "type": SignalType.FINANCIACION,   "description": "Ej: '18 cuotas con interés'"},
    {"name": "Envío gratis",             "type": SignalType.ENVIO,          "description": "Ej: 'Envío gratis a todo el país'"},
    {"name": "Envío express",            "type": SignalType.ENVIO,          "description": "Ej: 'Llega hoy', 'Envío rápido'"},
    {"name": "Urgencia temporal",        "type": SignalType.URGENCIA,       "description": "Ej: 'Hoy hasta las 23:59', 'Solo por hoy'"},
    {"name": "Urgencia stock",           "type": SignalType.URGENCIA,       "description": "Ej: 'Últimas unidades', 'Quedan 3'"},
    {"name": "CTA principal",            "type": SignalType.CTA,            "description": "Botón o texto de llamada a la acción principal"},
    {"name": "Hero banner message",      "type": SignalType.BRAND_HIGHLIGHT, "description": "Mensaje principal del banner hero"},
    {"name": "Producto destacado",       "type": SignalType.BRAND_HIGHLIGHT, "description": "Producto o categoría destacada en la home"},
    {"name": "Descuento absoluto",       "type": SignalType.PROMO,          "description": "Ej: '$500 de descuento', 'Ahorrá $2000'"},
    {"name": "Flash Sale",               "type": SignalType.URGENCIA,       "description": "Evento de venta relámpago con tiempo limitado"},
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as session:
        # ── Newsletter Account ─────────────────────────────────────────
        existing_account = await session.scalar(
            select(NewsletterAccount).where(
                NewsletterAccount.email_address == settings.email_server_user
            )
        )
        if existing_account:
            print(f"  ⚠️  Newsletter account '{settings.email_server_user}' ya existe — skipping.")
        else:
            account = NewsletterAccount(
                email_address=settings.email_server_user or "newsbriefai.dev@gmail.com",
                imap_host=settings.email_server_host or "imap.gmail.com",
                imap_port=settings.email_server_port or 993,
                is_active=True,
            )
            session.add(account)
            print(f"  ✅ Newsletter account '{account.email_address}' creada.")

        # ── Signal Taxonomy ────────────────────────────────────────────
        for t in TAXONOMIES:
            existing = await session.scalar(
                select(SignalTaxonomy).where(SignalTaxonomy.name == t["name"])
            )
            if existing:
                continue
            session.add(SignalTaxonomy(**t))
            print(f"  ✅ Taxonomía: [{t['type'].value}] {t['name']}")

        # ── First Test Competitor (Newsport) ───────────────────────────
        existing_comp = await session.scalar(
            select(Competitor).where(Competitor.domain == "newsport.com.ar")
        )
        if existing_comp:
            print("  ⚠️  Competitor 'newsport.com.ar' ya existe — skipping.")
        else:
            comp = Competitor(
                name="Newsport",
                domain="newsport.com.ar",
                vertical="DEPORTES",
                country="AR",
                status=CompetitorStatus.PENDING_ONBOARDING,
            )
            session.add(comp)
            print("  ✅ Competitor 'Newsport' (newsport.com.ar) creado.")

        await session.commit()
        print("\n🎉 Seed inicial completado. ¡Ya podés ver los datos en Directus!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
