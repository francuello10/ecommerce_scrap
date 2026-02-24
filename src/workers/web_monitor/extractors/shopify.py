"""Shopify extractor — reads from window.ShopifyAnalytics and meta JSON-LD."""

from __future__ import annotations

import json
import logging
import re

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)

_PRODUCT_JSON = re.compile(r"var\s+meta\s*=\s*(\{.*?\});", re.DOTALL)


class ShopifyExtractor(GenericHtmlExtractor):
    """Shopify-specific extractor with JSON-LD and meta product data."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.SHOPIFY

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.SHOPIFY

        # Try to parse Shopify meta object
        meta = self._parse_meta()
        if meta:
            logger.debug("Shopify meta found")
            # TODO Phase 3: Extract product variants, compare_at_price for promos

        # Try JSON-LD structured data
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") == "Product":
                    logger.debug("Shopify Product JSON-LD found")
                    # TODO Phase 3: Extract structured price data
            except (json.JSONDecodeError, AttributeError):
                pass

        return result

    def _parse_meta(self) -> dict | None:
        match = _PRODUCT_JSON.search(self.html)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
