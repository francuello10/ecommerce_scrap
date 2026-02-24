"""Salesforce Commerce Cloud (SFCC) / Demandware extractor.

Strategy: Target Demandware-specific meta tags and global JS objects (dw.ac, dw.product).
Fallback: Generic HTML regex extraction.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, ProductData

logger = logging.getLogger(__name__)

class SalesforceExtractor(GenericHtmlExtractor):
    """
    Salesforce Commerce Cloud (Demandware) specific extractor.
    """

    def __init__(self, html: str, headers: dict[str, str]) -> None:
        super().__init__(html, headers)
        self._platform = EcommercePlatform.SALESFORCE

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.SALESFORCE
        return result

    async def extract_product(self) -> ProductData | None:
        """
        Extract SFCC product data.
        SFCC often uses JSON-LD or specific meta tags like 'brand'.
        """
        # Try JSON-LD first (inherited)
        decoded = await super().extract_product()
        if decoded and decoded.sku:
            return decoded

        # Try SFCC specific data-attributes or JS objects (best-effort)
        # SFCC sites often have a 'product-id' or similar in the main container
        main_prod_container = self.soup.select_one(".product-detail, .product-wrapper, [data-pid]")
        if main_prod_container:
            sku = main_prod_container.get("data-pid")
            title = self.soup.select_one(".product-name, .pdp-title")
            price = self.soup.select_one(".price .value, .sales .value")
            
            if sku:
                return ProductData(
                    sku=str(sku),
                    title=title.get_text(strip=True) if title else None,
                    list_price=self._clean_price(price.get_text(strip=True)) if price else None,
                    is_in_stock=True, # SFCC usually hides 'Add to Cart' if out of stock
                )

        return decoded

    def _clean_price(self, price_str: str) -> float | None:
        try:
            # Remove symbols and handle AR currency format
            clean = re.sub(r'[^\d,.]', '', price_str)
            if ',' in clean and '.' in clean:
                clean = clean.replace('.', '').replace(',', '.')
            elif ',' in clean:
                clean = clean.replace(',', '.')
            return float(clean)
        except (ValueError, TypeError):
            return None
