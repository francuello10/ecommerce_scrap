"""Data models for the extraction pipeline (signals, promos, financing, etc.)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EcommercePlatform(StrEnum):
    """Known eCommerce platforms we can fingerprint."""

    VTEX = "VTEX"
    SHOPIFY = "SHOPIFY"
    MAGENTO = "MAGENTO"
    MAGENTO2 = "MAGENTO"  # alias — Magento 2.x uses same value
    SALESFORCE = "SALESFORCE"
    TIENDANUBE = "TIENDANUBE"
    WOOCOMMERCE = "WOOCOMMERCE"
    PRESTASHOP = "PRESTASHOP"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


class SignalType(StrEnum):
    """Unified taxonomy of commercial signals (RB-01 from SRS)."""

    PROMO = "PROMO"               # % OFF, 2x1, combos
    FINANCING = "FINANCING"       # cuotas, banco/tarjeta
    SHIPPING = "SHIPPING"         # envío gratis, umbral
    URGENCY = "URGENCY"           # "último día", "flash", countdown
    CTA = "CTA"                   # call-to-action principal
    BRAND_HIGHLIGHT = "BRAND_HIGHLIGHT"  # marca/categoría destacada


@dataclass(frozen=True, slots=True)
class PromoSignal:
    """A promotion detected on a page or email."""

    raw_text: str                      # ej: "30% OFF en Running"
    discount_type: str | None = None   # PERCENTAGE, FIXED, COMBO, 2X1
    discount_value: float | None = None
    brand: str | None = None
    category: str | None = None
    confidence: float = 0.0            # 0.0 – 1.0


@dataclass(frozen=True, slots=True)
class FinancingSignal:
    """A financing offer detected on a page or email."""

    raw_text: str                      # ej: "12 cuotas sin interés con Visa"
    installments: int | None = None
    bank: str | None = None
    card_brand: str | None = None      # Visa, Mastercard, AMEX
    interest_free: bool = False
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class HeroBanner:
    """The main hero/banner section of a page."""

    image_url: str | None = None
    alt_text: str | None = None
    headline: str | None = None
    link_url: str | None = None
    semantic_focus: str | None = None   # ej: "Lifestyle", "Liquidación", "Sale"


@dataclass(frozen=True, slots=True)
class CallToAction:
    """A call-to-action button or link detected."""

    text: str                           # ej: "COMPRAR AHORA", "VER OFERTAS"
    url: str | None = None
    position: str | None = None         # hero, sidebar, footer, popup


@dataclass(frozen=True, slots=True)
class ProductData:
    """Structured product data for Catalog Intelligence."""

    sku: str | None = None
    title: str | None = None
    url: str | None = None
    brand: str | None = None
    category_path: str | None = None
    list_price: float | None = None
    sale_price: float | None = None
    currency: str = "ARS"
    image_url: str | None = None
    is_in_stock: bool = True
    raw_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractionResult:
    """Consolidated result from a single extraction run."""

    platform_detected: EcommercePlatform = EcommercePlatform.UNKNOWN
    promos: list[PromoSignal] = field(default_factory=list)
    financing: list[FinancingSignal] = field(default_factory=list)
    hero_banner: HeroBanner | None = None
    ctas: list[CallToAction] = field(default_factory=list)
    product_data: ProductData | None = None
    raw_metadata: dict[str, str] = field(default_factory=dict)
