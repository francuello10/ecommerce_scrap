"""Abstract base class for all platform-specific extractors (Strategy Pattern)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from workers.web_monitor.models import ExtractionResult


class BaseExtractor(ABC):
    """
    Contract for all commercial signal extractors.

    HTML and headers are injected via __init__. Subclasses parse
    their target platform and return typed signals — never raw dicts.

    Principles:
    - Return empty lists / None on extraction failure (never raise).
    - Log warnings for unexpected content.
    - All methods are async for Playwright compatibility.
    """

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        self.html = html
        self.headers = headers

    @abstractmethod
    async def extract_all(self) -> ExtractionResult:
        """
        Main entry point. Runs all sub-extractors and returns
        a consolidated ExtractionResult.
        """
        ...
