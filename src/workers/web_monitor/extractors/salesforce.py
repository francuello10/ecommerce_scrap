"""Salesforce Commerce Cloud (SFCC) / Demandware extractor.

Strategy: Target Demandware-specific meta tags and global JS objects (dw.ac, dw.product).
Fallback: Generic HTML regex extraction.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.models import ExtractionResult, EcommercePlatform, ProductData, VariantData

logger = logging.getLogger(__name__)

class SalesforceExtractor(GenericHtmlExtractor):
    """
    Salesforce Commerce Cloud (Demandware) specific extractor.
    """

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self._platform = EcommercePlatform.SALESFORCE

    async def extract_all(self) -> ExtractionResult:
        result = await super().extract_all()
        result.platform_detected = EcommercePlatform.SALESFORCE
        return result

    async def extract_product(self) -> ProductData | None:
        """Compatibility wrapper for main product."""
        products = await self.extract_products()
        return products[0] if products else await super().extract_product()

    async def extract_products(self) -> list[ProductData]:
        """
        Extract ALL products from the page (Grid or PDP).
        """
        products = []
        
        # 1. Look for Grid / List items
        tiles = self.soup.select(".product-tile, .product-grid-item, .card-product")
        if tiles:
            for tile in tiles:
                sku = tile.get("data-itemid") or tile.get("data-pid")
                title = tile.select_one(".product-name-link, .link-tile")
                price = tile.select_one(".price .value, .sales .value")
                
                if sku:
                    products.append(ProductData(
                        sku=str(sku),
                        title=title.get_text(strip=True) if title else None,
                        list_price=self._clean_price(price.get_text(strip=True)) if price else None,
                        is_in_stock=True
                    ))
            if products:
                return products

        # 2. Look for single PDP
        main_prod_container = self.soup.select_one(".product-detail, .product-wrapper, [data-pid]")
        if main_prod_container:
            sku = main_prod_container.get("data-pid")
            title = self.soup.select_one(".product-name, .pdp-title, .product-detail .name")
            price = self.soup.select_one(".product-detail .price .value, .sales .value, .product-detail .price .sales, meta[property='product:price:amount']")
            
            p_val = None
            if price:
                if price.name == "meta":
                    p_val = self._clean_price(price.get("content", ""))
                else:
                    p_val = self._clean_price(price.get_text(strip=True))

            brand_tag = self.soup.select_one("meta[property='product:brand'], meta[name='brand']")
            
            # Premium Data Extraction
            description_tag = self.soup.select_one("#collapsible-description-1, .product-detail .description, .product-detail .details")
            all_images = []
            from urllib.parse import urljoin
            img_els = self.soup.select(".image-grid-container img, .product-image-container-grid img, .product-carousel img, .primary-image img")
            for img in img_els:
                src = img.get("src") or img.get("data-src") or img.get("srcset")
                if src:
                    src = src.split(" ")[0].split("?")[0]
                    # Absolute URL resolution
                    src = urljoin(self.url, src)
                    if src not in all_images:
                        all_images.append(src)

            # Social Proof & Badges (CRO)
            badges = []
            badge_els = self.soup.select(".product-badge, .badge-label, .promo-tag, .label-new")
            for b in badge_els:
                bt = b.get_text(strip=True)
                if bt and bt not in badges: badges.append(bt)
            
            rating_tag = self.soup.select_one(".rating-stars, .pdp-rating, [class*='rating']")
            rating_val = None
            if rating_tag:
                # Handle class as list or string
                cls_str = " ".join(rating_tag.get("class", [])) if isinstance(rating_tag.get("class"), list) else rating_tag.get("class", "")
                match = re.search(r"(\d(?:[\.,]\d)?)", rating_tag.get("aria-label", "") or cls_str)
                if match: rating_val = float(match.group(1).replace(",", "."))

            # Variants extraction
            variants = []
            size_list = self.soup.select(".size-attribute .select-size, .attribute-values .swatch-anchor, .size-swatches .swatch-anchor")
            for size in size_list:
                variants.append(VariantData(
                    sku=f"{sku}-{size.get('data-attr-value') or size.get_text(strip=True)}",
                    title=size.get_text(strip=True),
                    is_in_stock=not "disabled" in (size.get("class") or [])
                ))

            if sku:
                products.append(ProductData(
                    sku=str(sku),
                    title=title.get_text(strip=True) if title else None,
                    brand=brand_tag.get("content") if brand_tag else None,
                    description=description_tag.get_text(strip=True) if description_tag else None,
                    image_url=all_images[0] if all_images else None,
                    images=all_images,
                    category_tree=self._extract_breadcrumb_categories(),
                    list_price=p_val,
                    sale_price=p_val,
                    variants=variants,
                    rating=rating_val,
                    badges=badges,
                    source_url=self.url,
                    is_in_stock=True,
                ))

        return products if products else [p for p in [await super().extract_product()] if p]
