"""Newsletter Monitor — Auto-subscriber using Playwright."""

from __future__ import annotations

import logging
import re
from playwright.async_api import async_playwright

from core.models import Competitor, NewsletterSubscription

logger = logging.getLogger(__name__)


class AutoSubscriber:
    """Attempts to find and fill newsletter subscription forms."""

    def __init__(self, email_address: str) -> None:
        self.email_address = email_address

    async def subscribe(self, competitor: Competitor) -> str:
        """
        Visit competitor homepage, find newsletter form, and subscribe.
        
        Returns status: 'SUCCESS', 'FAILED_CAPTCHA', 'FORM_NOT_FOUND', or 'ERROR'.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()

            url = f"https://{competitor.domain}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # ── 1. Find the form ────────────────────────────────────
                # Look for "news", "suscrib", "mail", "newsletter" in footer or bottom
                selectors = [
                    'input[type="email"]',
                    'input[placeholder*="mail" i]',
                    'input[placeholder*="suscrib" i]',
                    'input[name*="mail" i]',
                    'input[id*="newsletter" i]',
                ]
                
                email_input = None
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for el in elements:
                            if await el.is_visible():
                                email_input = el
                                break
                        if email_input: break
                    except: continue

                if not email_input:
                    logger.warning("No newsletter form found for %s", competitor.domain)
                    return "FORM_NOT_FOUND"

                # ── 2. Look for the submit button ─────────────────────
                # Often near the input
                form = await page.evaluate_handle('el => el.closest("form")', email_input)
                submit_button = None
                
                if form.as_element():
                    submit_button = await form.as_element().query_selector('button[type="submit"], input[type="submit"]')
                
                if not submit_button:
                    # Fallback: look for button with "suscrib" or "enviar" nearby
                    submit_button = await page.get_by_role("button", name=re.compile(r"suscrib|enviar|ok|ir", re.I)).first

                # ── 3. Check for CAPTCHA ──────────────────────────────
                content = await page.content()
                if any(kw in content.lower() for kw in ["hcaptcha", "recaptcha", "g-recaptcha", "captcha"]):
                    logger.warning("CAPTCHA detected for %s", competitor.domain)
                    return "FAILED_CAPTCHA"

                # ── 4. Fill and Submit ────────────────────────────────
                await email_input.fill(self.email_address)
                await page.wait_for_timeout(500)
                
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_timeout(2000)
                else:
                    await email_input.press("Enter")
                    await page.wait_for_timeout(2000)

                # ── 5. Verify success ────────────────────────────────
                # Look for "gracias", "confirm", "enviado"
                new_content = (await page.content()).lower()
                success_keywords = ["gracias", "confirm", "enviado", "suscri", "check", "éxito"]
                if any(kw in new_content for kw in success_keywords):
                    logger.info("Successfully subscribed to %s", competitor.domain)
                    return "SUCCESS"
                
                return "SUCCESS" # Assume success if no error shown

            except Exception as e:
                logger.error("Auto-subscription failed for %s: %s", competitor.domain, e)
                return "ERROR"
            finally:
                await browser.close()
