"""WooCommerce extractor — reads from wc_add_to_cart_params and product JSON."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class WooCommerceExtractor(GenericHtmlExtractor):
    """WooCommerce extractor. Uses .woocommerce-Price-amount and REST API hints."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.WOOCOMMERCE

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.WOOCOMMERCE
        
        # WooCommerce specific selectors
        prices = self.selector.css(".woocommerce-Price-amount, .price ins .amount")
        if prices:
            result.raw_metadata["price_ui"] = prices[0].text
            
        promos = self.selector.css(".onsale, .woo-variation-price")
        if promos:
            result.raw_metadata["promo_ui"] = promos[0].text

        return result
