"""
Generic HTML Extractor — Regex-based signal extraction
=======================================================
Fallback extractor for any eCommerce platform.
Uses regex patterns calibrated for Spanish-language Argentine eCommerce.

Extracts:
  - PromoSignal: discount %, 2x1, combos
  - FinancingSignal: cuotas sin/con interés, banco/tarjeta
  - CallToAction: main buttons
  - HeroBanner: first hero image + headline

Used when platform is UNKNOWN / CUSTOM, and as a base for platform-specific extractors.
"""

from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup
from scrapling import Selector

from workers.web_monitor.extractors.base import BaseExtractor
from workers.web_monitor.models import (
    CallToAction,
    ExtractionResult,
    FinancingSignal,
    HeroBanner,
    PromoSignal,
    EcommercePlatform,
    ProductData,
)

logger = logging.getLogger(__name__)

# ── Regex Patterns ─────────────────────────────────────────────────────

# Promo: "30% OFF", "30% de descuento", "2x1", "2 x 1", "combo"
_PROMO_PERCENTAGE = re.compile(
    r"(\d{1,3})\s*%\s*(?:de\s+)?(?:off|descuento|ahorro|dscto\.?)",
    re.IGNORECASE,
)
_PROMO_2X1 = re.compile(
    r"\b(2\s*[xX×]\s*1|dos\s+por\s+uno|2do\s+(?:al\s+)?(?:\d+|gratis))\b",
    re.IGNORECASE,
)
_PROMO_COMBO = re.compile(
    r"\b(combo|pack|kit|bundle|llev[aá]\s*\d+)\b",
    re.IGNORECASE,
)
_PROMO_FIXED_AR = re.compile(
    r"\$\s*(\d[\d.,]+)\s*(?:de\s+)?(?:descuento|ahorro|off)\b",
    re.IGNORECASE,
)

# Financing: "12 cuotas sin interés", "6 cuotas con Visa"
_FIN_INSTALLMENTS = re.compile(
    r"(\d{1,2})\s*(?:cuotas?|pagos?|meses?)\s*"
    r"(?:(sin|con)\s+inter[eé]s)?"
    r"(?:\s+(?:con|en)\s+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)?))?",
    re.IGNORECASE,
)

# Common Argentine banks
_BANKS = re.compile(
    r"\b(Visa|Mastercard|AMEX|American\s+Express|Naranja|Cabal|Galicia|"
    r"Santander|BBVA|HSBC|Itaú|Banco\s+Naci[oó]n|BNA|Macro|Patagonia|"
    r"Mercado\s*Pago|MercadoPago|MP\b|Uala|Ual[aá])\b",
    re.IGNORECASE,
)

# CTA buttons: "Comprar", "Ver oferta", "Aprovechá", etc.
_CTA_PATTERNS = re.compile(
    r"\b(comprar?|ver\s+oferta|ver\s+m[aá]s|aprovech[aá]|quiero|lo\s+quiero|"
    r"agregar|a[ñn]adir|saber\s+m[aá]s|pedir|solicitar|descubr[íi]|"
    r"explorar|ir\s+a\s+tienda|shop\s+now|buy\s+now|order\s+now)\b",
    re.IGNORECASE,
)

# Shipping
_SHIPPING = re.compile(
    r"\b(env[íi]o\s+gratis|env[íi]o\s+(?:sin\s+cargo|incluido|express|"
    r"r[aá]pido|same.?day)|despacho\s+gratis|retiro\s+gratis)\b",
    re.IGNORECASE,
)


def _extract_text_chunks(soup: BeautifulSoup) -> list[str]:
    """Extract meaningful text blocks from the page body, skipping scripts/styles."""
    # Focus on promo-rich zones
    promo_zones = soup.select(
        "main, section, article, .banner, .promo, .offer, .hero, "
        "[class*='offer'], [class*='promo'], [class*='banner'], [class*='slider']"
    )
    if not promo_zones:
        promo_zones = [soup.body] if soup.body else [soup]

    chunks = []
    for zone in promo_zones:
        for element in zone.find_all(
            ["h1", "h2", "h3", "h4", "p", "span", "div", "a", "li"],
            recursive=False,
        ):
            text = element.get_text(separator=" ", strip=True)
            if 5 < len(text) < 500:
                chunks.append(text)

    return chunks[:200]  # Cap to avoid processing huge pages


class GenericHtmlExtractor(BaseExtractor):
    """
    Regex-based signal extractor for generic / unknown eCommerce platforms.
    Production-ready with Argentine eCommerce patterns.
    """

    def __init__(self, html: str, headers: dict[str, str], url: str | None = None) -> None:
        super().__init__(html, headers, url)
        self.soup = BeautifulSoup(html, "html.parser")
        self.selector = Selector(html)
        self._platform = EcommercePlatform.UNKNOWN

    # ── Public interface (required by BaseExtractor) ───────────────────

    async def extract_all(self) -> ExtractionResult:
        result = ExtractionResult(platform_detected=self._platform)

        if not self.soup.body:
            logger.warning("GenericExtractor: no <body> found, returning empty result")
            return result

        chunks = _extract_text_chunks(self.soup)
        full_text = " ".join(chunks)

        result.promos = self._extract_promos(chunks, full_text)
        result.financing = self._extract_financing(chunks, full_text)
        result.ctas = self._extract_ctas()
        result.hero_banner = self._extract_hero()
        result.products = await self.extract_products()
        
        # Post-process products with page context
        from urllib.parse import urljoin
        for p in result.products:
            if not p.source_url:
                p.source_url = self.url
            if p.images:
                # Fix relative URLs
                p.images = [urljoin(self.url, img) for img in p.images]
                p.image_url = p.images[0] if p.images else p.image_url
            
            # Absolute URL for main image if not in gallery
            if p.image_url and not p.image_url.startswith(("http://", "https://")):
                p.image_url = urljoin(self.url, p.image_url)

            if not p.installments and result.financing:
                best_fin = sorted(result.financing, key=lambda x: x.installments or 0, reverse=True)[0]
                p.installments = best_fin.raw_text

            # Generic Badge Parse
            if not p.badges:
                p.badges = self._extract_generic_badges()

        return result

    async def extract_product(self) -> ProductData | None:
        """Compatibility wrapper for main product."""
        products = await self.extract_products()
        return products[0] if products else None

    async def extract_products(self) -> list[ProductData]:
        """
        Generic product extraction using OpenGraph and Schema.org.
        Supports multiple products if found in JSON-LD @graph or lists.
        """
        return await self._extract_products_internal()

    async def _extract_products_internal(self) -> list[ProductData]:
        """Core generic extraction logic, safe for subclass fallback."""
        products = []
        # 1. Try JSON-LD (Schema.org)
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                
                # Handle both object and list of objects
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                else:
                    items = [data]

                for item in items:
                    if item.get("@type") == "Product":
                        p = self._parse_schema_product(item)
                        if p: products.append(p)
            except Exception:
                continue

        if products:
            return products

        # 2. Try OpenGraph / Meta tags
        og_data = self._extract_og_product()
        if og_data:
            return [og_data]

        return []

    # ── Private extraction methods ─────────────────────────────────────

    def _extract_promos(self, chunks: list[str], full_text: str) -> list[PromoSignal]:
        promos: list[PromoSignal] = []
        seen: set[str] = set()

        for chunk in chunks:
            # Percentage discount
            for match in _PROMO_PERCENTAGE.finditer(chunk):
                raw = chunk[:200]
                if raw in seen:
                    continue
                seen.add(raw)
                promos.append(PromoSignal(
                    raw_text=raw,
                    discount_type="PERCENTAGE",
                    discount_value=float(match.group(1)),
                    confidence=0.90,
                ))

            # Fixed amount discount
            for match in _PROMO_FIXED_AR.finditer(chunk):
                raw = chunk[:200]
                if raw in seen:
                    continue
                seen.add(raw)
                promos.append(PromoSignal(
                    raw_text=raw,
                    discount_type="FIXED",
                    discount_value=float(match.group(1).replace(".", "").replace(",", ".")),
                    confidence=0.85,
                ))

            # 2x1 / combo
            if _PROMO_2X1.search(chunk):
                raw = chunk[:200]
                if raw not in seen:
                    seen.add(raw)
                    promos.append(PromoSignal(raw_text=raw, discount_type="2X1", confidence=0.88))

            if _PROMO_COMBO.search(chunk) and not _PROMO_PERCENTAGE.search(chunk):
                raw = chunk[:200]
                if raw not in seen:
                    seen.add(raw)
                    promos.append(PromoSignal(raw_text=raw, discount_type="COMBO", confidence=0.70))

        return promos[:20]  # Cap

    def _extract_financing(self, chunks: list[str], full_text: str) -> list[FinancingSignal]:
        financing: list[FinancingSignal] = []
        seen: set[str] = set()

        for chunk in chunks:
            for match in _FIN_INSTALLMENTS.finditer(chunk):
                raw = chunk[:200]
                if raw in seen:
                    continue
                seen.add(raw)

                installments_str = match.group(1)
                interest_str = match.group(2)  # 'sin' or 'con'
                bank_str = match.group(3)

                # Check for bank mentions in the same chunk
                bank_match = _BANKS.search(chunk)
                bank_name = bank_match.group(0) if bank_match else bank_str

                financing.append(FinancingSignal(
                    raw_text=raw,
                    installments=int(installments_str) if installments_str else None,
                    bank=bank_name,
                    interest_free=(interest_str or "").lower() == "sin",
                    confidence=0.85,
                ))

        return financing[:10]

    def _extract_ctas(self) -> list[CallToAction]:
        ctas: list[CallToAction] = []
        seen_texts: set[str] = set()

        for element in self.soup.find_all(["a", "button"], limit=100):
            text = element.get_text(separator=" ", strip=True)
            if not text or len(text) > 100:
                continue
            if not _CTA_PATTERNS.search(text):
                continue

            normalized = text.lower().strip()
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)

            url = element.get("href") if element.name == "a" else None
            ctas.append(CallToAction(text=text, url=url))

        return ctas[:10]

    def _extract_hero(self) -> HeroBanner | None:
        """Extract the first prominent hero/banner image and headline."""
        # Try common hero selectors
        hero_selectors = [
            ".hero", ".banner", ".slider", "[class*='hero']", "[class*='banner']",
            "section:first-of-type", "main > div:first-child",
        ]
        hero_zone = None
        for sel in hero_selectors:
            hero_zone = self.soup.select_one(sel)
            if hero_zone:
                break

        if not hero_zone:
            return None

        # Find first image
        img = hero_zone.find("img")
        image_url = None
        alt_text = None
        if img:
            image_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            alt_text = img.get("alt", "")

        # Find first heading as headline
        headline_tag = hero_zone.find(["h1", "h2", "h3"])
        headline = headline_tag.get_text(strip=True) if headline_tag else None

        # Find first link
        link_tag = hero_zone.find("a", href=True)
        link_url = link_tag.get("href") if link_tag else None

        if not any([image_url, headline]):
            return None

        return HeroBanner(
            image_url=str(image_url) if image_url else None,
            alt_text=alt_text,
            headline=headline,
            link_url=link_url,
        )

    def _parse_schema_product(self, data: dict) -> ProductData:
        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        # Multiple images
        all_imgs = data.get("image")
        if isinstance(all_imgs, str): all_imgs = [all_imgs]
        elif not isinstance(all_imgs, list): all_imgs = []

        # Social Proof (CRO)
        rating_data = data.get("aggregateRating", {})
        rating = None
        review_count = None
        if isinstance(rating_data, dict):
            rating = rating_data.get("ratingValue")
            review_count = rating_data.get("reviewCount")

        return ProductData(
            sku=data.get("sku") or data.get("mpn"),
            title=data.get("name"),
            brand=data.get("brand", {}).get("name") if isinstance(data.get("brand"), dict) else data.get("brand"),
            category_path=data.get("category"),
            category_tree=self._extract_breadcrumb_categories(),
            description=data.get("description"),
            list_price=float(offers.get("price", 0)) if offers.get("price") else None,
            currency=offers.get("priceCurrency", "ARS"),
            is_in_stock="InStock" in str(offers.get("availability", "")),
            image_url=all_imgs[0] if all_imgs else None,
            images=all_imgs,
            rating=float(rating) if rating else None,
            review_count=int(review_count) if review_count else None,
        )

    def _extract_og_product(self) -> ProductData | None:
        def get_meta(prop):
            tag = self.soup.find("meta", property=prop) or self.soup.find("meta", attrs={"name": prop})
            return tag.get("content") if tag else None

        title = get_meta("og:title") or self.soup.title.string if self.soup.title else None
        if not title:
            return None

        price = get_meta("product:price:amount") or get_meta("og:price:amount")
        currency = get_meta("product:price:currency") or get_meta("og:price:currency") or "ARS"
        image = get_meta("og:image")
        description = get_meta("og:description") or get_meta("description")
        
        # Check if it looks like a product page
        if not get_meta("og:type") == "product" and not price:
            return None

        return ProductData(
            title=title,
            description=description,
            list_price=float(price) if price else None,
            currency=currency,
            image_url=image,
            images=[image] if image else [],
            category_tree=self._extract_breadcrumb_categories(),
            is_in_stock=True, # Default if meta present
        )

    def _extract_breadcrumb_categories(self) -> list[str]:
        """Attempt to extract the category tree from breadcrumbs."""
        # Common breadcrumb selectors
        bc_selectors = [".breadcrumb", ".breadcrumbs", "[class*='breadcrumb']", "nav[aria-label='Breadcrumb']"]
        for sel in bc_selectors:
            bc_container = self.soup.select_one(sel)
            if bc_container:
                # Find all links or spans in order
                items = bc_container.select("a, span, li")
                tree = []
                for item in items:
                    txt = item.get_text(strip=True)
                    # Filter out noise like "Home", "Inicio", "Resultados"
                    if txt and len(txt) > 2 and txt.lower() not in ["home", "inicio", "inicio /"]:
                        if txt not in tree:
                            tree.append(txt)
                if tree: return tree
        return []

    def _extract_generic_badges(self) -> list[str]:
        """Look for common e-commerce labels/badges in HTML."""
        badges = []
        badge_selectors = [
            ".badge", ".tag", ".label-product", ".product-label",
            "[class*='badge']", "[class*='label']"
        ]
        for sel in badge_selectors:
            els = self.soup.select(sel)
            for el in els:
                txt = el.get_text(strip=True)
                if txt and 2 < len(txt) < 20:
                    if txt not in badges:
                        badges.append(txt)
        return badges[:5]

    def _clean_price(self, price_str: str) -> float | None:
        """
        Clean price string and convert to float.
        Intelligently handles AR ($ 1.234,56) and US (1,234.56) formats.
        """
        if not price_str:
            return None
        try:
            # Remove symbols but keep numbers and separators
            clean = re.sub(r'[^\d,.]', '', price_str)
            
            # Case 1: Both separators exist
            if ',' in clean and '.' in clean:
                if clean.find('.') < clean.find(','): # 1.234,56
                    clean = clean.replace('.', '').replace(',', '.')
                else: # 1,234.56
                    clean = clean.replace(',', '')
            # Case 2: Only comma exists (likely 1234,56)
            elif ',' in clean:
                # If comma is used like 1.000 (thousands), it's rare but possible. 
                # Usually comma in AR is decimal.
                clean = clean.replace(',', '.')
            # Case 3: Only dot exists (1.234 or 1234.56)
            elif '.' in clean:
                # Heuristic: if there are 3 digits after the last dot, it's likely thousands
                parts = clean.split('.')
                if len(parts[-1]) == 3:
                    clean = clean.replace('.', '')
            
            return float(clean)
        except (ValueError, TypeError):
            return None
