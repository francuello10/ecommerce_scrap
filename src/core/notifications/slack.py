"""
Slack webhook notification sender.

Sends formatted messages to a Slack channel via incoming webhooks
for real-time competitive intelligence alerts.
"""

from __future__ import annotations

import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


async def send_slack_alert(
    text: str,
    *,
    blocks: list[dict] | None = None,
) -> bool:
    """
    Send a message to the configured Slack webhook.

    Args:
        text: Fallback text for notifications.
        blocks: Optional Slack Block Kit blocks for rich formatting.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.slack_webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured. Alert skipped.")
        return False

    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload,
            )
            response.raise_for_status()
            logger.info("Slack alert sent successfully.")
            return True
    except httpx.HTTPError as exc:
        logger.error("Failed to send Slack alert: %s", exc)
        return False
