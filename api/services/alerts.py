"""Alert monitoring service.

Checks for significant emission changes and creates alerts.
Can be triggered via API endpoint or scheduled background task.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Alert, EmissionReport, _utcnow

logger = logging.getLogger(__name__)

# ── Thresholds ──────────────────────────────────────────────────────

from api.config import CONFIDENCE_DROP_THRESHOLD, EMISSION_INCREASE_THRESHOLD


async def check_company_alerts(db: AsyncSession, company_id: str) -> list[Alert]:
    """Run all alert checks for a company and return newly created alerts."""
    new_alerts: list[Alert] = []

    # Get last two reports for the company
    result = await db.execute(
        select(EmissionReport)
        .where(
            EmissionReport.company_id == company_id,
            EmissionReport.deleted_at.is_(None),
        )
        .order_by(EmissionReport.created_at.desc())
        .limit(2)
    )
    reports = result.scalars().all()

    if len(reports) < 2:
        return new_alerts

    latest, previous = reports[0], reports[1]

    # Check emission increase
    if previous.total > 0:
        change_pct = (latest.total - previous.total) / previous.total
        if change_pct > EMISSION_INCREASE_THRESHOLD:
            alert = Alert(
                company_id=company_id,
                alert_type="emission_increase",
                severity="warning" if change_pct < 0.25 else "critical",
                title=f"Emissions increased {change_pct:.0%}",
                message=(
                    f"Total emissions increased from {previous.total:.1f} to {latest.total:.1f} tCO₂e "
                    f"({change_pct:.1%} increase) between report {previous.id[:8]} and {latest.id[:8]}."
                ),
                metadata_json={
                    "previous_total": previous.total,
                    "latest_total": latest.total,
                    "change_pct": round(change_pct, 4),
                    "previous_report_id": previous.id,
                    "latest_report_id": latest.id,
                },
            )
            db.add(alert)
            new_alerts.append(alert)

    # Check confidence drop
    confidence_drop = previous.confidence - latest.confidence
    if confidence_drop > CONFIDENCE_DROP_THRESHOLD:
        alert = Alert(
            company_id=company_id,
            alert_type="confidence_drop",
            severity="info",
            title=f"Confidence dropped {confidence_drop:.0%}",
            message=(
                f"Report confidence dropped from {previous.confidence:.0%} to {latest.confidence:.0%} "
                f"({confidence_drop:.0%} decrease). Consider providing more detailed data."
            ),
            metadata_json={
                "previous_confidence": previous.confidence,
                "latest_confidence": latest.confidence,
                "drop": round(confidence_drop, 4),
            },
        )
        db.add(alert)
        new_alerts.append(alert)

    if new_alerts:
        await db.flush()

    return new_alerts


async def list_alerts(
    db: AsyncSession, company_id: str, *, unread_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Alert], int]:
    """List alerts for a company with pagination."""
    query = select(Alert).where(Alert.company_id == company_id)
    count_query = select(func.count()).select_from(Alert).where(Alert.company_id == company_id)

    if unread_only:
        query = query.where(Alert.is_read == False)  # noqa: E712
        count_query = count_query.where(Alert.is_read == False)  # noqa: E712

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all(), total


async def acknowledge_alert(db: AsyncSession, alert_id: str, company_id: str) -> Alert | None:
    """Mark an alert as read/acknowledged."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.company_id == company_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        return None
    alert.is_read = True
    alert.acknowledged_at = _utcnow()
    await db.flush()
    return alert
