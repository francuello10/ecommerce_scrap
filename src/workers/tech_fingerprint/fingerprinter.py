"""
Tech Fingerprinting — Detects eCommerce platforms and technologies.

Uses pywappalyzer (Wappalyzer wrapper) to identify the tech stack
and saves results to CompetitorTechProfile.
"""

from __future__ import annotations

import logging
from datetime import datetime

from pywappalyzer.wappalyzer import Pywappalyzer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


import re

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
        """
        Strip inner content of <script> and <style> blocks to prevent ReDoS in Wappalyzer,
        but preserve the tag attributes (src, etc.) for detection.
        """
        # Remove inner content but keep tag attributes
        html = re.sub(
            r"<(script|style)\b([^>]*)>.*?</\1>",
            r"<\1\2></\1>",
            html,
            flags=re.DOTALL | re.IGNORECASE
        )
        # Limit total size to 512KB for safety
        return html[:512 * 1024]

    async def fingerprint_competitor(
        self,
        session: AsyncSession,
        competitor_id: int,
        url: str,
        html: str | None = None,
    ) -> CompetitorTechProfile:
        """
        Analyze a URL/HTML to detect technologies and update the profile.
        If html is provided, it uses it to avoid redundant fetches.
        """
        try:
            logger.info("  Fingerprinting tech for competitor %d (URL: %s)", competitor_id, url)
            
            if html:
                # Use analyze_html (requires bytes) after sanitization
                logger.info("    Using sanitized HTML for faster analysis")
                sanitized = self._sanitize_html(html)
                results = self.wappalyzer.analyze_html(html=sanitized.encode("utf-8"))
            else:
                logger.info("    No HTML provided, fetching URL...")
                results = self.wappalyzer.analyze(url)
            
            logger.info("    Detection complete. Found %d categories", len(results))
            
            # Map Wappalyzer categories to our DB fields
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
                "ecommerce_platform": None,
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
                        extracted[field] = techs[0] if techs else None

            # Fetch or create profile
            result = await session.execute(
                select(CompetitorTechProfile).where(CompetitorTechProfile.competitor_id == competitor_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                logger.info("    Creating new tech profile")
                profile = CompetitorTechProfile(
                    competitor_id=competitor_id,
                    **extracted,
                    full_fingerprint_json=results,
                    last_fingerprinted_at=datetime.utcnow()
                )
                session.add(profile)
            else:
                logger.info("    Updating existing tech profile")
                # Update fields and track changes
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
            
            return profile

        except Exception as e:
            logger.error("    Tech fingerprinting failed: %s", e)
            return None

