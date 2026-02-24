"""
src/core/ai/base.py
===================
Abstract base class for all AI providers.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseAIProvider(ABC):
    """
    Standard interface for generating content via LLMs.
    """

    def __init__(self, api_key: str, model_name: str, settings: dict[str, Any] | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.settings = settings or {}

    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Generate a text response given a prompt and optional system prompt.
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Verify if the API key and model are valid with a minimal request.
        """
        pass
