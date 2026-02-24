"""
verify_ai_briefing.py
=====================
Verifies the AI generation logic with mock data.
"""

import asyncio
import os
import json
from core.ai.factory import AIFactory

DEFAULT_SYSTEM_PROMPT = """
Eres un Analista de Inteligencia Comercial Senior experto en e-commerce.
Tu tarea es convertir un conjunto de señales técnicas y cambios detectados en un competidor en un reporte accionable, profesional y conciso.
""".strip()

async def test():
    print("--- Testing AI Briefing Generation ---")
    
    # Check for API keys
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        print("❌ Skip: No GEMINI_API_KEY found in env.")
        return

    # Mock Context Data
    context_data = {
        "date": "2026-02-24",
        "competitors": {
            "Newsport": [
                {"type": "PROMO", "severity": "HIGH", "change": "10% OFF -> 30% OFF en todo el sitio"},
                {"type": "FINANCE", "severity": "MEDIUM", "change": "Agregaron 6 cuotas sin interés con Galicia"}
            ],
            "Moov": [
                {"type": "TECH", "severity": "CRITICAL", "change": "Cambiaron de Vtex a Shopify"},
                {"type": "PROMO", "severity": "LOW", "change": "Nueva promo 'Back to School'"}
            ]
        }
    }

    prompt = f"Analiza las siguientes señales detectadas hoy y genera el reporte:\n\n{json.dumps(context_data, indent=2, ensure_ascii=False)}"
    
    print(f"Using Model: gemini-1.5-flash")
    provider = AIFactory.create(model_name="gemini-1.5-flash", api_key=api_key)
    
    print("Generating brief...")
    try:
        response = await provider.generate_text(prompt, system_prompt=DEFAULT_SYSTEM_PROMPT)
        print("\n--- GENERATED REPORT ---\n")
        print(response)
        print("\n------------------------\n")
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
