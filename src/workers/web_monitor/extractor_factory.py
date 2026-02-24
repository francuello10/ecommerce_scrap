"""
ExtractorFactory: Strategy Pattern router.

Decides which concrete BaseExtractor subclass to instantiate based on
the detected eCommerce platform.

Flow:
  Step 1 → Receive detected platform from PlatformDetector
  Step 2 → Instantiate the correct extractor with (html, headers)
  Step 3 → Return BaseExtractor instance to orchestrator

Usage:
    extractor = ExtractorFactory.create(platform, html, headers)
    result = await extractor.extract_all()
"""

from __future__ import annotations

import logging

from workers.web_monitor.extractors.base import BaseExtractor
from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.extractors.magento import MagentoExtractor
from workers.web_monitor.extractors.prestashop import PrestashopExtractor
from workers.web_monitor.extractors.salesforce import SalesforceExtractor
from workers.web_monitor.extractors.shopify import ShopifyExtractor
from workers.web_monitor.extractors.tiendanube import TiendanubeExtractor
from workers.web_monitor.extractors.vtex import VtexExtractor
from workers.web_monitor.extractors.woocommerce import WooCommerceExtractor
from workers.web_monitor.models import EcommercePlatform

logger = logging.getLogger(__name__)

# ── Registry: maps EcommercePlatform → concrete extractor class ────────

_EXTRACTOR_REGISTRY: dict[EcommercePlatform, type[BaseExtractor]] = {
    EcommercePlatform.VTEX: VtexExtractor,
    EcommercePlatform.SHOPIFY: ShopifyExtractor,
    EcommercePlatform.MAGENTO: MagentoExtractor,
    EcommercePlatform.TIENDANUBE: TiendanubeExtractor,
    EcommercePlatform.WOOCOMMERCE: WooCommerceExtractor,
    EcommercePlatform.PRESTASHOP: PrestashopExtractor,
    EcommercePlatform.SALESFORCE: SalesforceExtractor,
}


class ExtractorFactory:
    """
    Creates the correct BaseExtractor instance for a given platform.

    Usage:
        extractor = ExtractorFactory.create(EcommercePlatform.VTEX, html, headers)
        result = await extractor.extract_all()
    """

    @staticmethod
    def create(
        platform: EcommercePlatform,
        html: str,
        headers: dict[str, str],
        url: str | None = None,
    ) -> BaseExtractor:
        """
        Instantiate the extractor for the given platform.

        Falls back to GenericHtmlExtractor if the platform is UNKNOWN,
        CUSTOM, or not yet specifically implemented.
        """
        extractor_cls = _EXTRACTOR_REGISTRY.get(platform)

        if extractor_cls is None:
            logger.info(
                "No specific extractor for platform=%s, falling back to GenericHtmlExtractor.",
                platform,
            )
            return GenericHtmlExtractor(html, headers, url)

        logger.info("Using %s for platform=%s.", extractor_cls.__name__, platform)
        return extractor_cls(html, headers, url)
