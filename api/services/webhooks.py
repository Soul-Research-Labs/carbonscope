"""Webhook and continuous monitoring service.

Manages webhook subscriptions and dispatches notifications when
emission-related events occur (report created, data uploaded, etc.).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

# Supported event types
EVENT_TYPES = [
    "report.created",
    "data.uploaded",
    "estimate.completed",
    "supply_chain.link_created",
    "supply_chain.link_verified",
    "confidence.improved",
]


async def create_webhook(
    db: AsyncSession,
    company_id: str,
    url: str,
    event_types: list[str],
) -> Webhook:
    """Register a new webhook endpoint for a company."""
    # Validate event types
    invalid = [e for e in event_types if e not in EVENT_TYPES]
    if invalid:
        raise ValueError(f"Invalid event types: {invalid}. Valid: {EVENT_TYPES}")

    secret = secrets.token_urlsafe(32)
    webhook = Webhook(
        company_id=company_id,
        url=url,
        event_types=event_types,
        secret=secret,
        active=1,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


async def list_webhooks(
    db: AsyncSession,
    company_id: str,
) -> list[Webhook]:
    """List all webhooks for a company."""
    result = await db.execute(
        select(Webhook).where(Webhook.company_id == company_id)
    )
    return list(result.scalars().all())


async def delete_webhook(
    db: AsyncSession,
    webhook_id: str,
    company_id: str,
) -> bool:
    """Delete a webhook (scoped to company)."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.company_id == company_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        return False
    await db.delete(webhook)
    await db.commit()
    return True


async def toggle_webhook(
    db: AsyncSession,
    webhook_id: str,
    company_id: str,
    active: bool,
) -> Webhook | None:
    """Enable or disable a webhook."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.company_id == company_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        return None
    webhook.active = 1 if active else 0
    await db.commit()
    await db.refresh(webhook)
    return webhook


def _sign_payload(secret: str, payload: bytes) -> str:
    """Create HMAC-SHA256 signature for the webhook payload."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_event(
    db: AsyncSession,
    company_id: str,
    event_type: str,
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Dispatch an event to all matching active webhooks for a company.

    Performs real HTTP POST requests and logs delivery results.
    Returns a list of dispatch results (webhook_id, status, error).
    """
    webhooks = await list_webhooks(db, company_id)
    results = []

    for wh in webhooks:
        if not wh.active:
            continue
        if event_type not in (wh.event_types or []):
            continue

        payload_dict = {
            "event": event_type,
            "company_id": company_id,
            "data": data,
        }
        payload = json.dumps(payload_dict, default=str).encode()
        signature = _sign_payload(wh.secret, payload)

        headers = {
            "Content-Type": "application/json",
            "X-CarbonScope-Signature": f"sha256={signature}",
            "X-CarbonScope-Event": event_type,
        }

        delivery = WebhookDelivery(
            webhook_id=wh.id,
            event_type=event_type,
            payload=payload_dict,
        )

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(wh.url, content=payload, headers=headers)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            delivery.status_code = resp.status_code
            delivery.response_body = resp.text[:2048]
            delivery.success = 1 if resp.status_code < 400 else 0
            delivery.duration_ms = elapsed_ms

            results.append({
                "webhook_id": wh.id,
                "url": wh.url,
                "event": event_type,
                "status": "success" if delivery.success else "failed",
                "status_code": resp.status_code,
            })
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            delivery.success = 0
            delivery.error = str(exc)[:2048]
            delivery.duration_ms = elapsed_ms

            logger.warning(
                "Webhook delivery failed: webhook=%s url=%s error=%s",
                wh.id, wh.url, exc,
            )
            results.append({
                "webhook_id": wh.id,
                "url": wh.url,
                "event": event_type,
                "status": "error",
                "error": str(exc),
            })

        db.add(delivery)

    await db.commit()
    return results


async def list_deliveries(
    db: AsyncSession,
    webhook_id: str,
    company_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WebhookDelivery], int]:
    """List delivery logs for a webhook (scoped to company)."""
    from sqlalchemy import func

    # Verify webhook belongs to the company
    wh_result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.company_id == company_id,
        )
    )
    if wh_result.scalar_one_or_none() is None:
        return [], 0

    base = select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(
        base.order_by(WebhookDelivery.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total
