"""
Page Discovery Module — Header/Footer Auto-Discovery
=====================================================
Scans ONLY the <header>, <nav>, and <footer> zones of a page
to discover links to key pages (promos, financing, shipping, etc.).

IMPORTANT: Never scan the full body. Restricting to header/footer
reduces noise dramatically and avoids picking up irrelevant internal links.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from workers.web_monitor.models import EcommercePlatform

logger = logging.getLogger(__name__)

# ── Page type classification rules ────────────────────────────────────

PROMO_PATTERNS = re.compile(
    r"(?:promoci[oó]n|promo|oferta|sale|outlet|descuento|liquidaci[oó]n|mega|"
    r"cyber|hot.?sale|black.?friday|super.?precio|especial|deal)",
    re.IGNORECASE,
)
FINANCING_PATTERNS = re.compile(
    r"(?:financiaci[oó]n|financiamiento|cuotas?|banco|cr[eé]dito|pago|plan)",
    re.IGNORECASE,
)
SHIPPING_PATTERNS = re.compile(
    r"(?:env[íi]o|despacho|entrega|retiro|shipping|delivery)",
    re.IGNORECASE,
)

# ── Platform-specific selectors for header/footer zones ───────────────

PLATFORM_SELECTORS: dict[str, list[str]] = {
    EcommercePlatform.VTEX: [
        ".vtex-menu", ".vtex-header", ".vtex-footer",
        "[class*='vtex-menu']", "[class*='vtex-footer']",
    ],
    EcommercePlatform.SHOPIFY: [
        "#shopify-section-header", "#shopify-section-footer",
        ".site-header", ".site-footer",
    ],
    EcommercePlatform.MAGENTO2: [
        ".nav-sections", ".footer.content", ".page-header",
    ],
    EcommercePlatform.TIENDANUBE: [
        ".js-nav", ".js-footer", ".header-nav",
    ],
    EcommercePlatform.WOOCOMMERCE: [
        ".site-header", ".site-footer", ".main-navigation", ".secondary-navigation",
    ],
    EcommercePlatform.PRESTASHOP: [
        "#header", "#footer", ".header-nav",
    ],
}

# Universal semantic selectors used when platform-specific ones fail
UNIVERSAL_SELECTORS = [
    "header", "nav", "footer",
    "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    ".header", ".footer", ".nav", ".navigation",
    "#header", "#footer", "#nav",
]


@dataclass
class DiscoveredPage:
    url: str
    page_type: str  # PROMO_PAGE, FINANCING_PAGE, SHIPPING_PAGE, CATEGORY, OTHER
    anchor_text: str
    source_zone: str  # 'header', 'nav', 'footer'


def _classify_url(url: str, anchor_text: str) -> str:
    """Classify a URL into a page type based on URL path and anchor text."""
    combined = f"{url} {anchor_text}".lower()
    if PROMO_PATTERNS.search(combined):
        return "PROMO_PAGE"
    if FINANCING_PATTERNS.search(combined):
        return "FINANCING_PAGE"
    if SHIPPING_PATTERNS.search(combined):
        return "SHIPPING_PAGE"
    return "CATEGORY"


def _get_zones(soup: BeautifulSoup, platform: EcommercePlatform) -> list[Tag]:
    """
    Returns a list of HTML zones to scan (header + nav + footer only).
    Tries platform-specific selectors first, falls back to universal ones.
    """
    zones: list[Tag] = []
    seen_ids: set[int] = set()

    selectors = PLATFORM_SELECTORS.get(platform, []) + UNIVERSAL_SELECTORS
    for selector in selectors:
        for tag in soup.select(selector):
            tag_id = id(tag)
            if tag_id not in seen_ids:
                seen_ids.add(tag_id)
                zones.append(tag)

    return zones


def discover_pages(
    html: str,
    base_url: str,
    platform: EcommercePlatform,
    *,
    max_pages: int = 30,
) -> list[DiscoveredPage]:
    """
    Discover key pages linked from the header/footer navigation.

    Args:
        html: Full HTML of the page.
        base_url: Base URL to resolve relative links.
        platform: Detected eCommerce platform.
        max_pages: Max links to return.

    Returns:
        List of DiscoveredPage with classified page types.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    zones = _get_zones(soup, platform)

    if not zones:
        logger.warning("No header/footer zones found for %s", base_url)
        return []

    discovered: list[DiscoveredPage] = []
    seen_urls: set[str] = set()

    for zone in zones:
        zone_name = zone.name or zone.get("class", ["unknown"])[0]

        for a_tag in zone.find_all("a", href=True):
            href = a_tag.get("href", "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve to absolute URL
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            # Only same-domain links
            if parsed.netloc and parsed.netloc != base_domain:
                continue

            # Normalize
            clean_url = absolute_url.split("?")[0].rstrip("/")
            if clean_url in seen_urls or clean_url == base_url.rstrip("/"):
                continue
            seen_urls.add(clean_url)

            anchor_text = a_tag.get_text(separator=" ", strip=True)
            page_type = _classify_url(clean_url, anchor_text)

            discovered.append(
                DiscoveredPage(
                    url=clean_url,
                    page_type=page_type,
                    anchor_text=anchor_text[:200],
                    source_zone=str(zone_name),
                )
            )

            if len(discovered) >= max_pages:
                logger.info("Reached max_pages limit (%d)", max_pages)
                return discovered

    logger.info(
        "Discovered %d pages from %d zones for %s",
        len(discovered), len(zones), base_url,
    )
    return discovered
