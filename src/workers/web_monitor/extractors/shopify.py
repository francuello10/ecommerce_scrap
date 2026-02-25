"""Shopify extractor — reads from window.ShopifyAnalytics and meta JSON-LD."""

from __future__ import annotations

import json
import logging
import re

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, ProductData

logger = logging.getLogger(__name__)

_PRODUCT_JSON = re.compile(r"(?:var|window)\.meta\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.DOTALL)


class ShopifyExtractor(GenericHtmlExtractor):
    """Shopify-specific extractor with JSON-LD and meta product data."""

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.SHOPIFY

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.SHOPIFY

        # Try to parse Shopify meta object
        meta = self._parse_meta()
        if meta:
            logger.debug("Shopify meta found")

        # Use scrapling for structured data extraction
        for script in self.selector.css("script[type='application/ld+json']"):
            try:
                data = script.json
                if isinstance(data, dict) and data.get("@type") == "Product":
                    logger.debug("Shopify Product JSON-LD found")
            except Exception:
                pass

        return result

    async def extract_product(self) -> ProductData | None:
        """
        Extract Shopify product data from meta object or JSON-LD.
        """
        meta = self._parse_meta()
        if meta and meta.get("product"):
            prod = meta["product"]
            variants = prod.get("variants", [{}])
            v0 = variants[0] if variants else {}
            
            return ProductData(
                sku=str(v0.get("sku") or v0.get("id")),
                title=prod.get("type"), # Often 'type' is the main name in meta, or use title
                brand=prod.get("vendor"),
                list_price=float(v0.get("price") or 0) / 100.0 if v0.get("price") else None,
                sale_price=None, # Shopify compare_at_price needs careful parsing
                is_in_stock=not v0.get("public_title") == "Sold Out",
            )

        return await super().extract_product()

    def _parse_meta(self) -> dict | None:
        match = _PRODUCT_JSON.search(self.html)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
