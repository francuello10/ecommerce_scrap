"""
Diff Engine — Detects changes between consecutive page snapshots.

Compares the most recent DetectedSignal set against the previous one
and generates ChangeEvent records with severity levels.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    ChangeEvent,
    DetectedSignal,
    EventType,
    MonitoredPage,
    PageSnapshot,
    Severity,
)

logger = logging.getLogger(__name__)

# ── Severity mapping ──────────────────────────────────────────────────

_EVENT_SEVERITY: dict[EventType, Severity] = {
    EventType.NEW_PROMO: Severity.HIGH,
    EventType.REMOVED_PROMO: Severity.MEDIUM,
    EventType.CHANGED_FINANCING: Severity.HIGH,
    EventType.CHANGED_HERO: Severity.LOW,
    EventType.FLASH_SALE: Severity.CRITICAL,
}


async def analyze_changes(
    session: AsyncSession,
    page: MonitoredPage,
) -> list[ChangeEvent]:
    """
    Compare signals from the latest snapshot against the previous one.

    Returns a list of ChangeEvent records (already added to session).
    """
    # Get the two most recent snapshots for this page
    result = await session.execute(
        select(PageSnapshot.id)
        .where(PageSnapshot.monitored_page_id == page.id)
        .order_by(desc(PageSnapshot.created_at))
        .limit(2)
    )
    snapshot_ids = [row[0] for row in result.all()]

    if len(snapshot_ids) < 2:
        logger.debug("Page %s has < 2 snapshots, skipping diff", page.url)
        return []

    current_id, previous_id = snapshot_ids[0], snapshot_ids[1]

    # Fetch signals for both snapshots
    current_texts = await _get_signal_texts(session, current_id)
    previous_texts = await _get_signal_texts(session, previous_id)

    events: list[ChangeEvent] = []
    competitor_id = page.competitor_id

    # New promos
    for text in current_texts - previous_texts:
        evt_type = EventType.FLASH_SALE if _is_flash_sale(text) else EventType.NEW_PROMO
        event = ChangeEvent(
            competitor_id=competitor_id,
            event_type=evt_type,
            severity=_EVENT_SEVERITY[evt_type],
            new_value=text,
        )
        session.add(event)
        events.append(event)

    # Removed promos
    for text in previous_texts - current_texts:
        event = ChangeEvent(
            competitor_id=competitor_id,
            event_type=EventType.REMOVED_PROMO,
            severity=Severity.MEDIUM,
            old_value=text,
        )
        session.add(event)
        events.append(event)

    if events:
        logger.info(
            "Detected %d changes for %s (competitor_id=%d)",
            len(events), page.url, competitor_id,
        )

    return events


async def _get_signal_texts(session: AsyncSession, snapshot_id: int) -> set[str]:
    result = await session.execute(
        select(DetectedSignal.raw_text_found)
        .where(DetectedSignal.snapshot_id == snapshot_id)
    )
    return {row[0].strip() for row in result.all() if row[0]}


def _is_flash_sale(text: str) -> bool:
    """Detect flash sales (>= 40% off or time-limited language)."""
    match = re.search(r"(\d{1,3})\s*%", text)
    if match and int(match.group(1)) >= 40:
        return True
    flash_kw = ["flash", "relámpago", "últimas", "solo hoy", "24h", "48h"]
    return any(kw in text.lower() for kw in flash_kw)
