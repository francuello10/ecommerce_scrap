"""
src/core/ai/factory.py
======================
Factory for AI providers.
"""

from __future__ import annotations
from typing import Any
from core.config import settings
from core.ai.base import BaseAIProvider
from core.ai.gemini import GeminiProvider
from core.ai.openai import OpenAIProvider

class AIFactory:
    """
    Static factory to create the correct AI provider.
    """

    @staticmethod
    def create(model_name: str, api_key: str | None = None, **kwargs: Any) -> BaseAIProvider:
        """
        Create a provider based on model name.
        """
        # Determine provider by model prefix or explicit detection
        m = model_name.lower()
        
        # Mapping common prefixes
        if "gemini" in m:
            return GeminiProvider(
                api_key=api_key or settings.gemini_api_key or "",
                model_name=model_name,
                settings=kwargs
            )
        elif "gpt" in m or "o1" in m:
            return OpenAIProvider(
                api_key=api_key or settings.openai_api_key or "",
                model_name=model_name,
                settings=kwargs
            )
        else:
            # Fallback to Gemini if default
            return GeminiProvider(
                api_key=api_key or settings.gemini_api_key or "",
                model_name=model_name,
                settings=kwargs
            )
