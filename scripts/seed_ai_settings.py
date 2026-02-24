"""
seed_ai_settings.py
===================
Populates the database with default AI generator configurations.
Allows the user to customize the "Voice and Tone" of the Briefing Engine.
"""

import asyncio
import logging
from sqlalchemy import select
from core.database import async_session_factory
from core.models import AIGeneratorSettings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_SYSTEM_PROMPT = """
Eres un Analista de Inteligencia Comercial Senior experto en e-commerce.
Tu tarea es convertir un conjunto de señales técnicas y cambios detectados en un competidor en un reporte accionable, profesional y conciso.

INSTRUCCIONES:
1. Usa Markdown para el formato (headers, listas, bold).
2. Agrupa los hallazgos por relevancia (Críticos primero).
3. Si hay cambios de precios, calcula el % de variación si es posible.
4. Si hay nuevas promociones, descríbelas claramente (ej: 'Nuevas 12 cuotas sin interés en calzado').
5. Mantén un tono ejecutivo, directo y en español neutro/argentino (acorde al mercado).
6. Identifica oportunidades o amenazas (ej: 'El competidor X bajó precios antes del Hot Sale, posible estrategia agresiva').

DATOS DISPONIBLES:
- Cambios de señales web (promos, cuotas, banners).
- Cambios en el stack tecnológico.
- Nuevos newsletters recibidos.
- Cambios en catálogo (precios y stock).

El reporte final debe ser la sección principal del dashboard del cliente.
""".strip()

async def seed():
    async with async_session_factory() as session:
        # 1. Default Daily Brief Settings
        res = await session.execute(
            select(AIGeneratorSettings).where(AIGeneratorSettings.name == "DEFAULT_DAILY_BRIEF")
        )
        settings = res.scalar_one_or_none()
        
        if not settings:
            settings = AIGeneratorSettings(
                name="DEFAULT_DAILY_BRIEF",
                model_name="gemini-1.5-pro",
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                temperature=0.7,
                is_active=True
            )
            session.add(settings)
            logger.info("Added default AI Daily Brief settings")
        else:
            logger.info("AI Daily Brief settings already exist")

        await session.commit()
        logger.info("✅ AI Settings seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())
