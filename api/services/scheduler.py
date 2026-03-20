"""Background task scheduler for periodic monitoring.

Uses asyncio tasks running within the FastAPI lifespan.
Checks alerts (with dedup), sends email notifications, and resets monthly credits.
Supports distributed locking via Redis to prevent duplicate execution across replicas.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models import Alert, Company, EmissionReport, RefreshToken, RevokedToken, PasswordResetToken
from api.services.alerts import check_company_alerts
from api.services.event_bus import publish as publish_event

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None
_credit_reset_task: asyncio.Task | None = None
_webhook_retry_task: asyncio.Task | None = None
_token_cleanup_task: asyncio.Task | None = None

# Check interval in seconds (default: 1 hour)
CHECK_INTERVAL_SECONDS = 3600
# Credit reset interval (default: 24 hours — checks daily, resets monthly)
CREDIT_RESET_INTERVAL_SECONDS = 86400
# Webhook retry interval (default: 30 seconds)
WEBHOOK_RETRY_INTERVAL_SECONDS = 30
# Token cleanup interval (default: 24 hours)
TOKEN_CLEANUP_INTERVAL_SECONDS = 86400

# Redis distributed lock TTL (seconds) — prevents duplicate scheduler runs across replicas
_LOCK_TTL_ALERTS = CHECK_INTERVAL_SECONDS - 60  # slightly shorter than interval
_LOCK_TTL_CREDIT = 3600  # 1 hour — credit reset should finish well within this
_LOCK_TTL_WEBHOOK = WEBHOOK_RETRY_INTERVAL_SECONDS - 5
_LOCK_TTL_TOKEN_CLEANUP = 3600

_redis_client = None


def _get_redis():
    """Lazily init a Redis client for distributed locking. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis
    except ImportError:
        logger.warning("Redis package unavailable for scheduler lock; distributed lock disabled")
        _redis_client = None
        return None

    try:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Scheduler distributed lock: Redis connected")
        return _redis_client
    except (redis.RedisError, OSError) as exc:
        logger.warning("Redis unavailable for scheduler lock: %s", exc)
        _redis_client = None
        return None


def _acquire_lock(lock_name: str, ttl: int) -> bool:
    """Try to acquire a distributed lock.

    Returns True when lock acquired. In single-instance mode (no Redis URL),
    returns True. On Redis lock errors, returns True to fail open so
    background maintenance tasks are not skipped during transient outages.
    """
    r = _get_redis()
    if r is None:
        return True  # no Redis = single-instance mode, always proceed
    try:
        return bool(r.set(f"carbonscope:lock:{lock_name}", "1", nx=True, ex=ttl))
    except OSError as exc:
        logger.warning("Redis lock acquire failed for %s: %s", lock_name, exc)
        return True


async def _get_latest_alert_report_ids(db: AsyncSession, company_id: str) -> set[str]:
    """Get report IDs already referenced in recent alerts to prevent duplicates."""
    result = await db.execute(
        select(Alert.metadata_json)
        .where(Alert.company_id == company_id)
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    report_ids = set()
    for row in result.scalars().all():
        if row and isinstance(row, dict):
            if "latest_report_id" in row:
                report_ids.add(row["latest_report_id"])
    return report_ids


async def _run_periodic_checks() -> None:
    """Background loop that checks all companies for alerts (with dedup)."""
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            if not _acquire_lock("alert_check", _LOCK_TTL_ALERTS):
                logger.debug("Alert check skipped — another instance holds the lock")
                continue
            logger.info("Running periodic alert checks...")

            async with async_session() as db:
                total_alerts = 0
                offset = 0
                _BATCH = 100
                while True:
                    result = await db.execute(
                        select(Company.id).order_by(Company.id).limit(_BATCH).offset(offset)
                    )
                    company_ids = [row[0] for row in result.all()]
                    if not company_ids:
                        break

                    for company_id in company_ids:
                        try:
                            existing_ids = await _get_latest_alert_report_ids(db, company_id)
                            new_alerts = await check_company_alerts(db, company_id)

                            kept = 0
                            for alert in new_alerts:
                                meta = alert.metadata_json or {}
                                if meta.get("latest_report_id") in existing_ids:
                                    await db.delete(alert)
                                else:
                                    total_alerts += 1
                                    kept += 1

                            if kept > 0:
                                publish_event(company_id, "alert.created", {"count": kept})
                        except Exception:
                            logger.exception("Alert check failed for company %s", company_id)

                    offset += _BATCH

                await db.commit()
                if total_alerts > 0:
                    logger.info("Created %d new alerts", total_alerts)
                else:
                    logger.debug("No new alerts")

        except asyncio.CancelledError:
            logger.info("Scheduler shutting down")
            break
        except Exception as exc:
            logger.exception("Scheduler error (%s) — will retry next cycle", type(exc).__name__)


async def _run_monthly_credit_reset() -> None:
    """Background loop that resets credits on the 1st of each month."""
    last_reset_month: int | None = None
    while True:
        try:
            await asyncio.sleep(CREDIT_RESET_INTERVAL_SECONDS)
            now = datetime.now(timezone.utc)

            # Only reset on the 1st of the month, once per month
            if now.day == 1 and last_reset_month != now.month:
                if not _acquire_lock("credit_reset", _LOCK_TTL_CREDIT):
                    logger.debug("Credit reset skipped — another instance holds the lock")
                    continue
                logger.info("Running monthly credit reset...")
                from api.services.subscriptions import (
                    PLAN_LIMITS,
                    get_or_create_subscription,
                    grant_credits,
                    get_credit_balance,
                )

                async with async_session() as db:
                    offset = 0
                    _BATCH = 100
                    total_reset = 0
                    while True:
                        result = await db.execute(
                            select(Company.id).order_by(Company.id).limit(_BATCH).offset(offset)
                        )
                        company_ids = [row[0] for row in result.all()]
                        if not company_ids:
                            break

                        for company_id in company_ids:
                            try:
                                sub = await get_or_create_subscription(db, company_id)
                                monthly = PLAN_LIMITS.get(sub.plan, PLAN_LIMITS["free"])["monthly_credits"]
                                current = await get_credit_balance(db, company_id)
                                top_up = max(0, monthly - current)
                                if top_up > 0:
                                    await grant_credits(db, company_id, top_up, "monthly_reset")
                                total_reset += 1
                            except Exception:
                                logger.exception("Credit reset failed for company %s", company_id)

                        offset += _BATCH

                    await db.commit()
                    last_reset_month = now.month
                    logger.info("Monthly credit reset complete for %d companies", total_reset)

        except asyncio.CancelledError:
            logger.info("Credit reset scheduler shutting down")
            break
        except Exception as exc:
            logger.exception("Credit reset error (%s) — will retry next cycle", type(exc).__name__)


async def _run_webhook_retries() -> None:
    """Background loop that processes pending webhook delivery retries."""
    from api.services.webhooks import process_pending_retries

    while True:
        try:
            await asyncio.sleep(WEBHOOK_RETRY_INTERVAL_SECONDS)
            if not _acquire_lock("webhook_retry", _LOCK_TTL_WEBHOOK):
                continue
            async with async_session() as db:
                processed = await process_pending_retries(db)
                if processed > 0:
                    logger.info("Processed %d webhook retries", processed)
        except asyncio.CancelledError:
            logger.info("Webhook retry scheduler shutting down")
            break
        except Exception as exc:
            logger.exception("Webhook retry error (%s) — will retry next cycle", type(exc).__name__)


async def _run_token_cleanup() -> None:
    """Background loop that purges expired tokens daily."""
    while True:
        try:
            await asyncio.sleep(TOKEN_CLEANUP_INTERVAL_SECONDS)
            if not _acquire_lock("token_cleanup", _LOCK_TTL_TOKEN_CLEANUP):
                logger.debug("Token cleanup skipped — another instance holds the lock")
                continue
            logger.info("Running expired token cleanup...")
            now = datetime.now(timezone.utc)
            async with async_session() as db:
                total = 0
                for model in (RevokedToken, RefreshToken, PasswordResetToken):
                    _BATCH = 1000
                    while True:
                        result = await db.execute(
                            select(model).where(model.expires_at < now).limit(_BATCH)
                        )
                        rows = result.scalars().all()
                        if not rows:
                            break
                        for row in rows:
                            await db.delete(row)
                        total += len(rows)
                        await db.flush()
                await db.commit()
                if total > 0:
                    logger.info("Cleaned up %d expired tokens", total)
                else:
                    logger.debug("No expired tokens to clean up")
        except asyncio.CancelledError:
            logger.info("Token cleanup scheduler shutting down")
            break
        except Exception as exc:
            logger.exception("Token cleanup error (%s) — will retry next cycle", type(exc).__name__)


def start_scheduler() -> None:
    """Start the background scheduler tasks."""
    global _scheduler_task, _credit_reset_task, _webhook_retry_task, _token_cleanup_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_run_periodic_checks())
        logger.info("Background alert scheduler started (interval=%ds)", CHECK_INTERVAL_SECONDS)
    if _credit_reset_task is None or _credit_reset_task.done():
        _credit_reset_task = asyncio.create_task(_run_monthly_credit_reset())
        logger.info("Monthly credit reset scheduler started")
    if _webhook_retry_task is None or _webhook_retry_task.done():
        _webhook_retry_task = asyncio.create_task(_run_webhook_retries())
        logger.info("Webhook retry scheduler started (interval=%ds)", WEBHOOK_RETRY_INTERVAL_SECONDS)
    if _token_cleanup_task is None or _token_cleanup_task.done():
        _token_cleanup_task = asyncio.create_task(_run_token_cleanup())
        logger.info("Token cleanup scheduler started (interval=%ds)", TOKEN_CLEANUP_INTERVAL_SECONDS)


async def stop_scheduler() -> None:
    """Stop the background scheduler tasks."""
    global _scheduler_task, _credit_reset_task, _webhook_retry_task, _token_cleanup_task
    for task in [_scheduler_task, _credit_reset_task, _webhook_retry_task, _token_cleanup_task]:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    _scheduler_task = None
    _credit_reset_task = None
    _webhook_retry_task = None
    _token_cleanup_task = None
    logger.info("Background schedulers stopped")
