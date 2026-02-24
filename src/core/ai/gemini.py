"""
src/core/ai/gemini.py
=====================
Google Gemini implementation.
"""

from __future__ import annotations
import google.generativeai as genai
from core.ai.base import BaseAIProvider

class GeminiProvider(BaseAIProvider):
    """
    Provider for Google Gemini models.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro", settings: dict | None = None) -> None:
        super().__init__(api_key, model_name, settings)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={"temperature": self.settings.get("temperature", 0.7)},
        )

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        # Gemini 1.5 allows system_instruction in the constructor, 
        # but for simplicity we'll prepend it to the prompt if not configured at model level.
        try:
            full_prompt = prompt
            if system_prompt:
                # Re-instantiate if system prompt provided (best for 1.5 instructions)
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_prompt,
                    generation_config={"temperature": self.settings.get("temperature", 0.7)},
                )
            else:
                model = self.model

            response = await model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            return f"Error with Gemini: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            # Minimal request to test key
            await self.model.generate_content_async("Hi", generation_config={"max_output_tokens": 1})
            return True
        except Exception:
            return False
