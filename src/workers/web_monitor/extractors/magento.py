"""Magento 2 extractor — reads from window.checkoutConfig and .price-box DOM."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class MagentoExtractor(GenericHtmlExtractor):
    """Magento 2 extractor. Uses .price-box and installment block selectors."""

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.MAGENTO

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.MAGENTO
        
        # Use scrapling for fast selector-based enrichment
        # Price box
        prices = self.selector.css(".price-box")
        if prices:
            price_text = prices[0].text
            if price_text:
                result.raw_metadata["price_box"] = price_text

        # Installments
        insts = self.selector.css(".installment-block, .product-item-details .installments")
        if insts:
            result.raw_metadata["installments_ui"] = insts[0].text

        return result
