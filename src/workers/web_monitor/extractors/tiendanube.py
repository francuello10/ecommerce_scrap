"""TiendaNube extractor — reads from window.LS and .price-item DOM."""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform

logger = logging.getLogger(__name__)


class TiendanubeExtractor(GenericHtmlExtractor):
    """TiendaNube / Nuvemshop extractor. Reads window.LS boot object."""

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.TIENDANUBE

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.TIENDANUBE
        # TODO Phase 3: Extract from window.LS.product / window.LS.cart
        # TODO Phase 3: Extract installments from .js-installments
        return result
