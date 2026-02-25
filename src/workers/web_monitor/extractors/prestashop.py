"""PrestaShop extractor — reads from .product-prices and prestashop_ body classes."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class PrestashopExtractor(GenericHtmlExtractor):
    """PrestaShop extractor. Uses .product-prices and js-product-miniature."""

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.PRESTASHOP

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.PRESTASHOP
        
        # PrestaShop selectors
        current_price = self.selector.css(".current-price, .product-price")
        regular_price = self.selector.css(".regular-price")
        
        if current_price:
            result.raw_metadata["price_current"] = current_price[0].text
        if regular_price:
            result.raw_metadata["price_regular"] = regular_price[0].text

        return result
