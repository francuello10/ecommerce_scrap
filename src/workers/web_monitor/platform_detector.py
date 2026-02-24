"""
Capa 1: Heurísticas rápidas para detectar la plataforma eCommerce.

Este módulo analiza el HTML y los headers HTTP de una página para
determinar la plataforma subyacente SIN depender de servicios externos.
Corre en milisegundos y se usa para enrutar al extractor correcto.

La "Capa 2" (wappalyzer-next) corre en background para un perfil
tecnológico completo (analytics, payments, CDN, etc.).
"""

from __future__ import annotations

import re

from workers.web_monitor.models import EcommercePlatform


# ──────────────────────────────────────────────────────────────────────
# Firmas conocidas por plataforma
# Cada entrada es una tupla (fuente, patrón regex)
# fuente: "html" | "header_key" | "header_value"
# ──────────────────────────────────────────────────────────────────────

_PLATFORM_SIGNATURES: dict[EcommercePlatform, list[tuple[str, str]]] = {
    EcommercePlatform.VTEX: [
        ("html", r"__STATE__"),
        ("html", r"vtex\.render-server"),
        ("html", r"vteximg\.com\.br"),
        ("header_key", r"x-vtex-"),
    ],
    EcommercePlatform.SHOPIFY: [
        ("html", r"window\.Shopify"),
        ("html", r"cdn\.shopify\.com"),
        ("header_key", r"x-shopify"),
        ("html", r"Shopify\.theme"),
    ],
    EcommercePlatform.MAGENTO: [
        ("html", r"Magento/"),
        ("html", r"mage-cache-storage"),
        ("html", r"requirejs/require"),
        ("html", r"catalog/product/view"),
    ],
    EcommercePlatform.TIENDANUBE: [
        ("html", r"tiendanube\.com/scripts"),
        ("html", r"window\.LS\.store"),
        ("html", r"nuvemshop"),
    ],
    EcommercePlatform.WOOCOMMERCE: [
        ("html", r"wp-content/plugins/woocommerce"),
        ("html", r"woocommerce"),
        ("html", r"wc-block-"),
    ],
    EcommercePlatform.PRESTASHOP: [
        ("html", r"var prestashop"),
        ("html", r"PrestaShop"),
        ("html", r"prestashop/js"),
    ],
}


class PlatformDetector:
    """
    Detects the eCommerce platform from raw HTML and HTTP headers.

    Usage:
        platform = PlatformDetector.detect(html=page_html, headers=response_headers)
    """

    @staticmethod
    def detect(
        html: str,
        headers: dict[str, str] | None = None,
    ) -> EcommercePlatform:
        """
        Capa 1: Heurísticas rápidas de detección.

        Busca firmas conocidas en el HTML y en los headers HTTP.
        Retorna la primera plataforma que matchea con al menos 1 firma.
        Si ninguna matchea, retorna EcommercePlatform.UNKNOWN.

        Args:
            html: Contenido HTML crudo de la página.
            headers: Headers HTTP de la respuesta (keys en lowercase).

        Returns:
            EcommercePlatform detectada o UNKNOWN.
        """
        if headers is None:
            headers = {}

        # Normalizar header keys a lowercase
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        for platform, signatures in _PLATFORM_SIGNATURES.items():
            for source, pattern in signatures:
                if source == "html" and re.search(pattern, html, re.IGNORECASE):
                    return platform
                elif source == "header_key":
                    if any(
                        re.search(pattern, key, re.IGNORECASE)
                        for key in normalized_headers
                    ):
                        return platform
                elif source == "header_value":
                    if any(
                        re.search(pattern, val, re.IGNORECASE)
                        for val in normalized_headers.values()
                    ):
                        return platform

        return EcommercePlatform.UNKNOWN
