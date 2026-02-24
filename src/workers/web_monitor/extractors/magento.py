"""Magento 2 extractor — reads from window.checkoutConfig and .price-box DOM."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class MagentoExtractor(GenericHtmlExtractor):
    """Magento 2 extractor. Uses .price-box and installment block selectors."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.MAGENTO

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.MAGENTO
        # TODO Phase 3: Extract from .price-box, .price--special
        # TODO Phase 3: Extract installments from .installment-block
        return result
