"""VTEX IO / VTEX Legacy extractor.

Strategy: Extract from __STATE__ JSON pre-rendered in HTML.
Fallback: Generic HTML regex extraction (inherited from GenericHtmlExtractor).
"""

from __future__ import annotations

import json
import logging
import re

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, PromoSignal, ProductData

logger = logging.getLogger(__name__)

# VTEX stores page state in a window.__STATE__ JSON object
_STATE_PATTERN = re.compile(r"window\.__STATE__\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.DOTALL)


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
            # Enhance signals if needed...
        else:
            logger.debug("VTEX __STATE__ not found, using generic extraction only")

        return result

    async def extract_product(self) -> ProductData | None:
        """
        Extract VTEX product data from __STATE__.
        """
        state = self._parse_state()
        if not state:
            return await super().extract_product()

        # Find the first Product object in VTEX STATE
        for key, value in state.items():
            if ":" in key and value.get("__typename") == "Product":
                return self._parse_vtex_product(value)

        return await super().extract_product()

    def _parse_vtex_product(self, data: dict) -> ProductData:
        price_range = data.get("priceRange", {})
        selling_price = price_range.get("sellingPrice", {})
        list_price = price_range.get("listPrice", {})

        return ProductData(
            sku=data.get("productId") or data.get("productReference"),
            title=data.get("productName") or data.get("productTitle"),
            brand=data.get("brand"),
            category_path=data.get("categoryTree", [{}])[0].get("name") if data.get("categoryTree") else None,
            list_price=float(list_price.get("highPrice", 0)) if list_price else None,
            sale_price=float(selling_price.get("lowPrice", 0)) if selling_price else None,
            currency="ARS",
            is_in_stock=bool(data.get("items", [{}])[0].get("sellers", [{}])[0].get("commertialOffer", {}).get("AvailableQuantity", 1) > 0) if data.get("items") else True,
            image_url=data.get("items", [{}])[0].get("images", [{}])[0].get("imageUrl") if data.get("items") else None,
        )

    def _parse_state(self) -> dict | None:
        match = _STATE_PATTERN.search(self.html)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
