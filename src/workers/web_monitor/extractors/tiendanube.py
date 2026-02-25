"""TiendaNube extractor — reads from window.LS and .price-item DOM."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class TiendanubeExtractor(GenericHtmlExtractor):
    """TiendaNube / Nuvemshop extractor. Reads window.LS boot object."""

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.TIENDANUBE

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.TIENDANUBE
        
        # Tiendanube / Nuvemshop specific
        prices = self.selector.css(".js-price-display, #price_display")
        if prices:
            result.raw_metadata["price_ui"] = prices[0].text
            
        installments = self.selector.css(".js-installments-credit-card, .js-max-installments-container")
        if installments:
             result.raw_metadata["installments_ui"] = installments[0].text

        return result
