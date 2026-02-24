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
        # TODO Phase 3: Extract .woocommerce-Price-amount for prices
        # TODO Phase 3: Extract .woo-variation-price for promos
        return result
