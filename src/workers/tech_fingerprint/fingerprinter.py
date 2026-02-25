"""
Tech Fingerprinting — Detects eCommerce platforms and technologies.

Uses pywappalyzer for JS/Analytics and custom checks for eCommerce platforms
to avoid freezing on Cloudflare/bot protections.
"""

from __future__ import annotations

import logging
from datetime import datetime
import re

from pywappalyzer.wappalyzer import Pywappalyzer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from curl_cffi.requests import AsyncSession as CurlSession

from core.models import (
    CompetitorTechProfile,
    TechProfileChange,
    TechProfileHistory,
)

logger = logging.getLogger(__name__)


class TechFingerprinter:
    """Detects and tracks technology changes in competitors."""

    def __init__(self) -> None:
        self.wappalyzer = Pywappalyzer()

    def _sanitize_html(self, html: str) -> str:
        """Limit total size to 250KB for safety."""
        return html[:250 * 1024]

    async def _fetch_url(self, url: str) -> tuple[str, dict[str, str]]:
        """Fetch URL using curl_cffi to bypass protections and get raw headers."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        }
        async with CurlSession(impersonate="chrome120", timeout=15.0) as client:
            try:
                response = await client.get(url, headers=headers)
                return response.text, dict(response.headers)
            except Exception as e:
                logger.warning("Failed to fetch %s for fingerprinting: %s", url, e)
                return "", {}

    def _detect_ecommerce_platform(self, html: str, headers: dict[str, str]) -> str | None:
        """Custom aggressive detection for LATAM ecosystem platforms."""
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        
        # 1. Check HTTP Headers
        if "x-vtex-root" in headers_lower or "x-vtex-meta" in headers_lower or "vtex" in headers_lower.get("server", ""):
            return "VTEX"
        if "shopify" in headers_lower.get("server", "") or "x-shopid" in headers_lower:
            return "Shopify"
        if "prestashop" in headers_lower.get("x-powered-by", ""):
            return "PrestaShop"

        # 2. Check HTML Footprints
        html_lower = html.lower()
        if "vtex" in html_lower or "vtexassets.com" in html_lower or "__state__" in html_lower:
            return "VTEX"
        if "shopify.com" in html_lower or "cdn.shopify.com" in html_lower:
            return "Shopify"
        if "wp-content/plugins/woocommerce" in html_lower or "woocommerce-" in html_lower:
            return "WooCommerce"
        if "tiendanube.com" in html_lower or "d26lpennugtm8s.cloudfront.net" in html_lower:
            return "TiendaNube"
        if "magento" in html_lower or "mage/cookies.js" in html_lower:
            return "Magento"
        
        return None

    async def fingerprint_competitor(
        self,
        session: AsyncSession,
        competitor_id: int,
        url: str,
        html: str | None = None,
    ) -> CompetitorTechProfile | None:
        """
        Analyze a URL/HTML to detect technologies and update the profile.
        """
        try:
            logger.info("  Fingerprinting tech for competitor %d (URL: %s)", competitor_id, url)
            
            headers = {}
            if not html:
                logger.info("    Fetching URL internally...")
                html, headers = await self._fetch_url(url)
            
            if not html:
                logger.warning("    No HTML available to fingerprint.")
                return None

            # Detect platform via custom fast paths
            platform = self._detect_ecommerce_platform(html, headers)
            if platform:
                logger.info("    Aggressive detection matched: %s", platform)

            # Analyze other scripts using Wappalyzer
            sanitized = self._sanitize_html(html)
            results = self.wappalyzer.analyze_html(html=sanitized.encode("utf-8"))
            
            # Map Wappalyzer categories
            cat_map = {
                "eCommerce": "ecommerce_platform",
                "Analytics": "analytics_tools",
                "Marketing automation": "marketing_automation",
                "Tag managers": "tag_managers",
                "Payment processors": "payment_gateways",
                "Live chat": "live_chat",
                "CDN": "cdn_provider",
                "JavaScript frameworks": "js_frameworks",
            }
            
            extracted = {
                "ecommerce_platform": platform, # Prioritize custom override
                "analytics_tools": [],
                "marketing_automation": [],
                "tag_managers": [],
                "payment_gateways": [],
                "live_chat": [],
                "cdn_provider": None,
                "js_frameworks": [],
            }

            for category, techs in results.items():
                field = cat_map.get(category)
                if field:
                    if isinstance(extracted[field], list):
                        extracted[field].extend(techs)
                    else:
                        # Only overwrite ecommerce_platform if custom detection failed
                        if field == "ecommerce_platform" and extracted["ecommerce_platform"]:
                            continue
                        extracted[field] = techs[0] if techs else None

            # Fetch or create profile
            result = await session.execute(
                select(CompetitorTechProfile).where(CompetitorTechProfile.competitor_id == competitor_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                profile = CompetitorTechProfile(
                    competitor_id=competitor_id,
                    **extracted,
                    full_fingerprint_json=results,
                    last_fingerprinted_at=datetime.utcnow()
                )
                session.add(profile)
            else:
                for field, new_val in extracted.items():
                    old_val = getattr(profile, field)
                    if old_val != new_val:
                        session.add(TechProfileChange(
                            competitor_id=competitor_id,
                            change_type="CHANGED",
                            category=field,
                            tool_name=str(new_val),
                            previous_value=str(old_val),
                            new_value=str(new_val),
                        ))
                        setattr(profile, field, new_val)
                
                profile.full_fingerprint_json = results
                profile.last_fingerprinted_at = datetime.utcnow()

            # Add to history
            session.add(TechProfileHistory(
                competitor_id=competitor_id,
                snapshot_date=datetime.utcnow().date(),
                ecommerce_platform=extracted["ecommerce_platform"],
                full_fingerprint_json=results,
            ))
            
            await session.commit()
            return profile

        except Exception as e:
            logger.error("    Tech fingerprinting failed: %s", e)
            return None

