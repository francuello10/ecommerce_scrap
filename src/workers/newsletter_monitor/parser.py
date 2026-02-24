"""Newsletter Monitor — Signal Parser."""

from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup

from core.models import NewsletterMessage, DetectedSignal, SignalType

logger = logging.getLogger(__name__)


class NewsletterParser:
    """Extracts signals and prices from newsletter emails."""

    def __init__(self, message: NewsletterMessage, html_content: str) -> None:
        self.message = message
        self.html = html_content
        self.soup = BeautifulSoup(html_content, "html.parser")

    def extract_signals(self) -> list[DetectedSignal]:
        """
        Parse HTML and extract promotions, discounts, and financing.
        
        Uses common newsletter patterns (alt text, headline text, buttons).
        """
        signals: list[DetectedSignal] = []
        
        # 1. Subject line is often the best signal
        subject = self.message.subject or ""
        self._add_signals_from_text(subject, "SUBJECT_LINE", signals)

        # 2. Extract from <img> alt texts (common in retail newsletters)
        imgs = self.soup.find_all("img", alt=True)
        for img in imgs:
            alt = img["alt"].strip()
            if len(alt) > 5:
                self._add_signals_from_text(alt, "IMG_ALT", signals)

        # 3. Extract from CTA buttons/links
        links = self.soup.find_all("a")
        for link in links:
            text = link.get_text().strip()
            if len(text) > 5:
                # Common patterns: "Comprar con 20% OFF", "Ver cuotas"
                self._add_signals_from_text(text, "CTA_LINK", signals)

        # 4. Extract from visible headlines (H1/H2)
        for h in self.soup.find_all(["h1", "h2", "strong", "b"]):
            text = h.get_text().strip()
            if 10 < len(text) < 150:
                self._add_signals_from_text(text, "HEADLINE", signals)

        # Remove duplicates
        seen = set()
        unique_signals = []
        for s in signals:
            if s.raw_text_found not in seen:
                unique_signals.append(s)
                seen.add(s.raw_text_found)

        return unique_signals

    def _add_signals_from_text(self, text: str, source: str, signals: list[DetectedSignal]) -> None:
        """Helper to find promos and financing in a snippet of text."""
        # -- Discount detection --
        # 20% OFF, 2x1, 3x2, hasta 50% desc, etc.
        promo_patterns = [
            r"\d{1,3}%\s*(?:off|desc|descuento|ahorro|dscto)",
            r"\d\s*x\s*\d",
            r"(?:promo|oferta|liquidaci[oó]n|sale|hot\s*sale)",
            r"2do\s+al\s+\d{1,3}%",
            r"llev[at]\s*\d\s*pag[at]\s*\d"
        ]
        for pattern in promo_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                signals.append(DetectedSignal(
                    raw_text_found=text,
                    source_type=SignalType.PROMO,
                    metadata_json={"source_origin": source, "detected_pattern": match.group(0)}
                ))
                break

        # -- Financing detection --
        # 3 cuotas, 6 sin interés, Plan Z, etc.
        fin_patterns = [
            r"\d{1,2}\s*cuotas",
            r"sin\s*inter[eé]s",
            r"(?:visa|mastercard|amex|naranja|cabal)",
            r"ahora\s*\d{1,2}"
        ]
        for pattern in fin_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                signals.append(DetectedSignal(
                    raw_text_found=text,
                    source_type=SignalType.FINANCIACION,
                    metadata_json={"source_origin": source, "detected_pattern": match.group(0)}
                ))
                break

        # -- Shipping detection --
        ship_match = re.search(r"(env[ií]o\s*grat[ií]s|gratis\s*a\s*todo\s*el\s*pa[ií]s|entrega\s*sin\s*cargo)", text, re.I)
        if ship_match:
            signals.append(DetectedSignal(
                raw_text_found=text,
                source_type=SignalType.ENVIO,
                metadata_json={"source_origin": source, "detected_pattern": ship_match.group(0)}
            ))
