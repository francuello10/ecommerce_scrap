"""PrestaShop extractor — reads from .product-prices and prestashop_ body classes."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class PrestashopExtractor(GenericHtmlExtractor):
    """PrestaShop extractor. Uses .product-prices and js-product-miniature."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.PRESTASHOP

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.PRESTASHOP
        # TODO Phase 3: Extract .regular-price vs .current-price for discount detection
        # TODO Phase 3: Extract installments from .payment-block
        return result
