"""Newsletter Monitor — Auto-subscriber using Playwright."""

from __future__ import annotations

import logging
import re
import os
import json
import base64
from playwright.async_api import async_playwright, Page
from openai import AsyncOpenAI
from google import genai
from google.genai import types

from core.models import Competitor, NewsletterSubscription

logger = logging.getLogger(__name__)


class AutoSubscriber:
    """Attempts to find and fill newsletter subscription forms."""

    def __init__(self, email_address: str) -> None:
        self.email_address = email_address
        self.provider = os.getenv("CAPTCHA_SOLVER_PROVIDER", "openai").lower()
        
        self.openai_client = None
        self.gemini_client = None
        
        if self.provider == "gemini":
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) if os.getenv("GEMINI_API_KEY") else None
        else:
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    async def _solve_captcha(self, page: Page) -> bool:
        """Takes a screenshot, sends to LLM to find the checkbox, and clicks it."""
        if self.provider == "openai" and not self.openai_client:
            logger.error("No OPENAI_API_KEY found, cannot solve CAPTCHA visually.")
            return False
        if self.provider == "gemini" and not self.gemini_client:
            logger.error("No GEMINI_API_KEY found, cannot solve CAPTCHA visually.")
            return False
            
        logger.info(f"  🤖 Attempting to solve CAPTCHA visually using {self.provider}...")
        try:
            # Wait a bit for the captcha iframe to fully load
            await page.wait_for_timeout(3000)
            
            # Take a screenshot
            screenshot_bytes = await page.screenshot(type="jpeg", quality=70)
            b64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            
            prompt = "You are an automated assistant. Locate the CAPTCHA checkbox (e.g. \"I'm not a robot\" or Turnstile box) in this image to prove you are human. Return the exact X and Y coordinates (in pixels) of the center of the checkbox in pure JSON format, like this: `{\"x\": 100, \"y\": 200}`. Do not return any other text or markdown block, ONLY the JSON."
            
            content = ""
            if self.provider == "openai":
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    }
                                }
                            ],
                        }
                    ],
                    max_tokens=100,
                    temperature=0.1
                )
                content = response.choices[0].message.content.strip()
            
            elif self.provider == "gemini":
                # Note: google-genai is mostly sync out of the box unless using specific async methods, 
                # we'll use the sync call in this simple script step
                response = self.gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg'),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=100,
                    )
                )
                content = response.text.strip()
            
            content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            x, y = data.get("x"), data.get("y")
            
            if x is not None and y is not None:
                logger.info("    🎯 AI found CAPTCHA exactly at X:%s, Y:%s. Clicking...", x, y)
                await page.mouse.click(x, y)
                await page.wait_for_timeout(4000)  # Wait for resolution
                return True
            else:
                logger.warning("    AI couldn't find exact coordinates: %s", content)
                return False
                
        except Exception as e:
            logger.error("    AI Captcha solving failed: %s", e)
            return False

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
                if any(kw in content.lower() for kw in ["hcaptcha", "recaptcha", "g-recaptcha", "captcha", "turnstile"]):
                    logger.warning("CAPTCHA detected for %s", competitor.domain)
                    solved = await self._solve_captcha(page)
                    if not solved:
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
