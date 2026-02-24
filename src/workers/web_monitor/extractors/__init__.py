"""Extractors package for platform-specific web scraping."""

from workers.web_monitor.extractors.base import BaseExtractor
from workers.web_monitor.extractors.generic_html import GenericHtmlExtractor
from workers.web_monitor.extractors.magento import MagentoExtractor
from workers.web_monitor.extractors.prestashop import PrestashopExtractor
from workers.web_monitor.extractors.shopify import ShopifyExtractor
from workers.web_monitor.extractors.tiendanube import TiendanubeExtractor
from workers.web_monitor.extractors.vtex import VtexExtractor
from workers.web_monitor.extractors.woocommerce import WooCommerceExtractor

__all__ = [
    "BaseExtractor",
    "GenericHtmlExtractor",
    "MagentoExtractor",
    "PrestashopExtractor",
    "ShopifyExtractor",
    "TiendanubeExtractor",
    "VtexExtractor",
    "WooCommerceExtractor",
]
