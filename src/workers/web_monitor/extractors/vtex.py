"""VTEX IO / VTEX Legacy extractor.

Strategy: Extract from __STATE__ JSON pre-rendered in HTML.
Fallback: Generic HTML regex extraction (inherited from GenericHtmlExtractor).
"""

from __future__ import annotations

import json
import logging
import re

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, PromoSignal

logger = logging.getLogger(__name__)

# VTEX stores page state in a window.__STATE__ JSON object
_STATE_PATTERN = re.compile(r"window\.__STATE__\s*=\s*(\{.*?\})(?:;|\n)", re.DOTALL)


class VtexExtractor(GenericHtmlExtractor):
    """VTEX-specific extractor. Reads window.__STATE__ for pre-rendered data."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.VTEX

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.VTEX

        # Try to enhance with __STATE__ data
        state = self._parse_state()
        if state:
            logger.debug("VTEX __STATE__ found (%d keys)", len(state))
            # TODO Phase 3: Extract promotions/benefitName from __STATE__
            # TODO Phase 3: Extract installmentOptions from __STATE__
        else:
            logger.debug("VTEX __STATE__ not found, using generic extraction only")

        return result

    def _parse_state(self) -> dict | None:
        match = _STATE_PATTERN.search(self.html)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
