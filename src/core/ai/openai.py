"""
src/core/ai/openai.py
=====================
OpenAI implementation.
"""

from __future__ import annotations
from openai import AsyncOpenAI
from core.ai.base import BaseAIProvider

class OpenAIProvider(BaseAIProvider):
    """
    Provider for OpenAI (GPT-4, etc.) models.
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o", settings: dict | None = None) -> None:
        super().__init__(api_key, model_name, settings)
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.settings.get("temperature", 0.7),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error with OpenAI: {str(e)}"

    async def test_connection(self) -> bool:
        try:
            await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
