"""
Briefing Engine — Daily/Weekly brief generators.

Consolidates ChangeEvents, NewsletterMessages, and TechProfileChanges
into actionable Markdown + JSON briefs.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    WeeklyBrief,
    AIGeneratorSettings,
)
from core.ai.factory import AIFactory

logger = logging.getLogger(__name__)


async def generate_daily_brief(session: AsyncSession, brief_date: date | None = None) -> DailyBrief:
    """
    Generate a daily brief for the given date.

    Consolidates all ChangeEvents from the past 24 hours into a
    Markdown report and a structured JSON summary.
    """
    if brief_date is None:
        brief_date = date.today()

    # Check if brief already exists
    existing = await session.execute(
        select(DailyBrief).where(DailyBrief.brief_date == brief_date)
    )
    if existing.scalar_one_or_none():
        logger.info("Daily brief for %s already exists, skipping", brief_date)
        return existing.scalar_one_or_none()

    # Fetch changes from the past 24 hours
    start_dt = datetime.combine(brief_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    result = await session.execute(
        select(ChangeEvent)
        .where(
            ChangeEvent.created_at >= start_dt,
            ChangeEvent.created_at < end_dt,
        )
        .order_by(ChangeEvent.severity.desc(), ChangeEvent.created_at)
    )
    events = list(result.scalars().all())

    # Group by competitor
    by_competitor: dict[int, list[ChangeEvent]] = {}
    for evt in events:
        by_competitor.setdefault(evt.competitor_id, []).append(evt)

    # Get competitor names
    comp_ids = list(by_competitor.keys())
    comp_names: dict[int, str] = {}
    if comp_ids:
        result = await session.execute(
            select(Competitor.id, Competitor.name).where(Competitor.id.in_(comp_ids))
        )
        comp_names = {row.id: row.name for row in result.all()}

    # Try AI generation first
    res_ai = await session.execute(
        select(AIGeneratorSettings).where(AIGeneratorSettings.is_active == True).limit(1)
    )
    ai_settings = res_ai.scalar_one_or_none()
    
    md = ""
    if ai_settings:
        logger.info("Using AI (%s) for Daily Brief", ai_settings.model_name)
        try:
            provider = AIFactory.create(
                model_name=ai_settings.model_name,
                temperature=ai_settings.temperature,
            )
            # Build context for LLM
            context_data = {
                "date": brief_date.isoformat(),
                "competitors": {
                    comp_names.get(cid, f"ID:{cid}"): [
                        {
                            "type": e.event_type.value,
                            "severity": e.severity.value,
                            "change": f"{e.old_value} -> {e.new_value}" if e.old_value and e.new_value else (e.new_value or e.old_value)
                        } for e in evts
                    ] for cid, evts in by_competitor.items()
                }
            }
            prompt = f"Analiza las siguientes señales detectadas hoy y genera el reporte:\n\n{json.dumps(context_data, indent=2, ensure_ascii=False)}"
            md = await provider.generate_text(prompt, system_prompt=ai_settings.system_prompt)
        except Exception as e:
            logger.error("AI Briefing failed: %s", e)
            md = _build_markdown(brief_date, by_competitor, comp_names)
    else:
        # Fallback to static Markdown
        md = _build_markdown(brief_date, by_competitor, comp_names)

    # Generate JSON summary
    json_data = _build_json(brief_date, events, by_competitor, comp_names)

    brief = DailyBrief(
        brief_date=brief_date,
        content_markdown=md,
        content_json=json_data,
        status=BriefStatus.PUBLISHED,
    )
    session.add(brief)
    await session.commit()

    logger.info("Generated daily brief for %s: %d events", brief_date, len(events))
    return brief


def _build_markdown(
    brief_date: date,
    by_competitor: dict[int, list[ChangeEvent]],
    comp_names: dict[int, str],
) -> str:
    lines = [
        f"# 📊 Daily Intelligence Brief — {brief_date.strftime('%d/%m/%Y')}",
        "",
    ]

    if not by_competitor:
        lines.append("_Sin cambios detectados en las últimas 24 horas._")
        return "\n".join(lines)

    total = sum(len(evts) for evts in by_competitor.values())
    critical = sum(
        1 for evts in by_competitor.values()
        for e in evts if e.severity == Severity.CRITICAL
    )

    lines.append(f"**{total} cambios detectados** en {len(by_competitor)} competidor(es)")
    if critical:
        lines.append(f"🚨 **{critical} alertas CRITICAL**")
    lines.append("")

    for comp_id, events in by_competitor.items():
        name = comp_names.get(comp_id, f"Competitor #{comp_id}")
        lines.append(f"## {name}")
        lines.append("")
        for evt in events:
            severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                evt.severity.value, "⚪"
            )
            action = evt.new_value or evt.old_value or evt.event_type.value
            lines.append(f"- {severity_emoji} **{evt.event_type.value}**: {action[:100]}")
        lines.append("")

    return "\n".join(lines)


def _build_json(
    brief_date: date,
    events: list[ChangeEvent],
    by_competitor: dict[int, list[ChangeEvent]],
    comp_names: dict[int, str],
) -> dict:
    return {
        "date": brief_date.isoformat(),
        "total_events": len(events),
        "total_competitors": len(by_competitor),
        "critical_count": sum(1 for e in events if e.severity == Severity.CRITICAL),
        "competitors": {
            comp_names.get(cid, str(cid)): {
                "events": [
                    {
                        "type": e.event_type.value,
                        "severity": e.severity.value,
                        "old": e.old_value,
                        "new": e.new_value,
                    }
                    for e in evts
                ]
            }
            for cid, evts in by_competitor.items()
        },
    }


async def generate_weekly_brief(session: AsyncSession, end_date: date | None = None) -> WeeklyBrief:
    """Generate a weekly brief aggregating daily data."""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=7)

    result = await session.execute(
        select(DailyBrief)
        .where(DailyBrief.brief_date >= start_date, DailyBrief.brief_date <= end_date)
        .order_by(DailyBrief.brief_date)
    )
    daily_briefs = list(result.scalars().all())

    md_lines = [
        f"# 📈 Weekly Intelligence Brief",
        f"### {start_date.strftime('%d/%m')} — {end_date.strftime('%d/%m/%Y')}",
        "",
        f"**{len(daily_briefs)} daily briefs** cubiertos en esta semana.",
        "",
    ]

    total_events = 0
    for brief in daily_briefs:
        if brief.content_json:
            total_events += brief.content_json.get("total_events", 0)
        md_lines.append(f"- **{brief.brief_date.strftime('%A %d/%m')}**: {brief.content_json.get('total_events', 0) if brief.content_json else 0} cambios")

    md_lines.insert(4, f"**{total_events} cambios totales** en la semana.")

    weekly = WeeklyBrief(
        start_date=start_date,
        end_date=end_date,
        content_markdown="\n".join(md_lines),
        content_json={"total_events": total_events, "days_covered": len(daily_briefs)},
    )
    session.add(weekly)
    await session.commit()

    logger.info("Generated weekly brief: %s to %s (%d events)", start_date, end_date, total_events)
    return weekly
