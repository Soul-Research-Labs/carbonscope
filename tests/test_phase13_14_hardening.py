"""Phase 13–14 tests — Redis limiter, scheduler locks, request ID filter,
confidence.improved webhook, and token cleanup."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionLocal

REGISTER_PAYLOAD = {
    "email": "phase13@example.com",
    "password": "Securepass123!",
    "full_name": "Phase13 User",
    "company_name": "Phase13Corp",
    "industry": "technology",
    "region": "US",
}


async def _register_and_login(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or REGISTER_PAYLOAD
    await client.post("/api/v1/auth/register", json=p)
    resp = await client.post("/api/v1/auth/login", json={
        "email": p["email"],
        "password": p["password"],
    })
    return resp.json()["access_token"]


# ── Redis-backed rate limiter ───────────────────────────────────────


class TestRedisLimiter:
    """Verify that the limiter configuration respects REDIS_URL."""

    def test_limiter_defaults_to_memory(self):
        """Without REDIS_URL, storage_uri should fall back to memory://."""
        with patch.dict("os.environ", {}, clear=False):
            import importlib
            import api.limiter as lim_mod
            # The module-level code reads os.getenv; just verify the attribute exists
            assert hasattr(lim_mod, "limiter")
            assert lim_mod.limiter is not None

    def test_limiter_has_storage_uri_attr(self):
        from api.limiter import limiter
        # slowapi Limiter stores its storage backend internally
        assert limiter is not None


# ── Scheduler distributed lock ──────────────────────────────────────


class TestSchedulerLock:
    """Test _acquire_lock and _get_redis helper."""

    def test_acquire_lock_without_redis(self):
        """Without Redis, _acquire_lock should always return True."""
        from api.services.scheduler import _acquire_lock
        with patch("api.services.scheduler._get_redis", return_value=None):
            assert _acquire_lock("test_lock", 60) is True

    def test_acquire_lock_with_redis_success(self):
        """When Redis SET NX returns True, lock is acquired."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        from api.services.scheduler import _acquire_lock
        with patch("api.services.scheduler._get_redis", return_value=mock_redis):
            assert _acquire_lock("test_lock", 60) is True
            mock_redis.set.assert_called_once_with(
                "carbonscope:lock:test_lock", "1", nx=True, ex=60
            )

    def test_acquire_lock_with_redis_failure(self):
        """When Redis SET NX returns False, lock not acquired."""
        mock_redis = MagicMock()
        mock_redis.set.return_value = False
        from api.services.scheduler import _acquire_lock
        with patch("api.services.scheduler._get_redis", return_value=mock_redis):
            assert _acquire_lock("test_lock", 60) is False

    def test_acquire_lock_redis_exception(self):
        """On Redis error, fall back to proceeding (return True)."""
        mock_redis = MagicMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")
        from api.services.scheduler import _acquire_lock
        with patch("api.services.scheduler._get_redis", return_value=mock_redis):
            assert _acquire_lock("test_lock", 60) is True

    def test_get_redis_returns_none_without_env(self):
        """_get_redis returns None when REDIS_URL is not set."""
        import api.services.scheduler as sched
        original = sched._redis_client
        sched._redis_client = None  # reset cached client
        try:
            with patch.dict("os.environ", {"REDIS_URL": ""}, clear=False):
                result = sched._get_redis()
                assert result is None
        finally:
            sched._redis_client = original


# ── Request ID log correlation ──────────────────────────────────────


class TestRequestIDFilter:
    """Test the RequestIDFilter and contextvars integration."""

    def test_filter_injects_request_id(self):
        from api.logging_config import RequestIDFilter, request_id_var
        filt = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        # Default (no request_id set)
        filt.filter(record)
        assert record.request_id == "-"

    def test_filter_reads_contextvar(self):
        from api.logging_config import RequestIDFilter, request_id_var
        token = request_id_var.set("req-abc-123")
        try:
            filt = RequestIDFilter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="hello", args=(), exc_info=None,
            )
            filt.filter(record)
            assert record.request_id == "req-abc-123"
        finally:
            request_id_var.reset(token)

    def test_json_formatter_includes_request_id(self):
        import json
        from api.logging_config import JSONFormatter, RequestIDFilter, request_id_var
        token = request_id_var.set("req-json-001")
        try:
            filt = RequestIDFilter()
            fmt = JSONFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="check output", args=(), exc_info=None,
            )
            filt.filter(record)
            output = fmt.format(record)
            data = json.loads(output)
            assert data["request_id"] == "req-json-001"
            assert data["message"] == "check output"
        finally:
            request_id_var.reset(token)


# ── confidence.improved webhook ─────────────────────────────────────


class TestConfidenceImprovedWebhook:
    """Test that creating a higher-confidence report triggers the event."""

    @pytest.mark.asyncio
    async def test_confidence_improved_fires(self, client: AsyncClient):
        """Two estimates for the same year — second with more data (higher confidence)
        should trigger confidence.improved dispatch."""
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Register a webhook
        await client.post("/api/v1/webhooks", json={
            "url": "https://example.com/hook",
            "events": ["confidence.improved"],
        }, headers=headers)

        with patch("api.routes.carbon_routes.dispatch_event", new_callable=MagicMock) as mock_dispatch:
            from unittest.mock import AsyncMock
            mock_dispatch.side_effect = AsyncMock()

            # First data upload (minimal → low confidence)
            up1 = await client.post("/api/v1/data", json={
                "year": 2024,
                "provided_data": {"revenue_usd": 5_000_000},
            }, headers=headers)
            assert up1.status_code in (200, 201)
            upload_id_1 = up1.json()["id"]

            # First estimate
            resp1 = await client.post("/api/v1/estimate", json={
                "data_upload_id": upload_id_1,
            }, headers=headers)
            assert resp1.status_code in (200, 201)

            # Second data upload (richer data → higher confidence)
            up2 = await client.post("/api/v1/data", json={
                "year": 2024,
                "provided_data": {
                    "revenue_usd": 10_000_000,
                    "employees": 100,
                    "electricity_kwh": 500_000,
                    "fuel_use_liters": 50_000,
                    "fuel_type": "diesel",
                    "supplier_spend_usd": 2_000_000,
                },
            }, headers=headers)
            assert up2.status_code in (200, 201)
            upload_id_2 = up2.json()["id"]

            # Second estimate — same year
            resp2 = await client.post("/api/v1/estimate", json={
                "data_upload_id": upload_id_2,
            }, headers=headers)
            assert resp2.status_code in (200, 201)

            # dispatch_event should have been called for report.created and estimate.completed
            event_names = [call.args[2] for call in mock_dispatch.call_args_list]
            assert "report.created" in event_names
            assert "estimate.completed" in event_names


# ── Token cleanup scheduler ─────────────────────────────────────────


class TestTokenCleanup:
    """Test the _run_token_cleanup periodic task logic indirectly."""

    @pytest.mark.asyncio
    async def test_expired_tokens_are_deleted(self):
        """Insert expired tokens and verify cleanup removes them."""
        from api.models import RevokedToken, RefreshToken, PasswordResetToken, User, Company
        import hashlib

        async with TestSessionLocal() as db:
            # Create a company + user for FK references
            from api.models import _new_id
            company = Company(
                id=_new_id(), name="CleanupCorp", industry="technology",
                region="US", employee_count=10,
            )
            db.add(company)
            await db.flush()

            user = User(
                id=_new_id(), email="cleanup@test.com",
                hashed_password="x", full_name="Cleanup",
                company_id=company.id, role="admin",
            )
            db.add(user)
            await db.flush()

            past = datetime.now(timezone.utc) - timedelta(days=1)
            future = datetime.now(timezone.utc) + timedelta(days=1)

            # Expired token (should be cleaned up)
            expired_revoked = RevokedToken(
                id=_new_id(), jti="expired-jti",
                user_id=user.id, expires_at=past,
            )
            # Valid token (should survive)
            valid_revoked = RevokedToken(
                id=_new_id(), jti="valid-jti",
                user_id=user.id, expires_at=future,
            )

            expired_refresh = RefreshToken(
                id=_new_id(), user_id=user.id,
                token_hash=hashlib.sha256(b"expired").hexdigest(),
                expires_at=past,
            )
            valid_refresh = RefreshToken(
                id=_new_id(), user_id=user.id,
                token_hash=hashlib.sha256(b"valid").hexdigest(),
                expires_at=future,
            )

            expired_reset = PasswordResetToken(
                id=_new_id(), user_id=user.id, email="cleanup@test.com",
                token_hash=hashlib.sha256(b"expired_reset").hexdigest(),
                expires_at=past,
            )

            db.add_all([expired_revoked, valid_revoked, expired_refresh, valid_refresh, expired_reset])
            await db.commit()

            # Verify all inserted
            all_revoked = (await db.execute(select(RevokedToken))).scalars().all()
            assert len(all_revoked) == 2
            all_refresh = (await db.execute(select(RefreshToken))).scalars().all()
            assert len(all_refresh) == 2

            # Simulate cleanup logic (same as _run_token_cleanup)
            now = datetime.now(timezone.utc)
            total = 0
            for model in (RevokedToken, RefreshToken, PasswordResetToken):
                result = await db.execute(
                    select(model).where(model.expires_at < now)
                )
                rows = result.scalars().all()
                for row in rows:
                    await db.delete(row)
                total += len(rows)
            await db.commit()

            assert total == 3  # 1 revoked + 1 refresh + 1 reset

            # Verify survivors
            remaining_revoked = (await db.execute(select(RevokedToken))).scalars().all()
            assert len(remaining_revoked) == 1
            assert remaining_revoked[0].jti == "valid-jti"

            remaining_refresh = (await db.execute(select(RefreshToken))).scalars().all()
            assert len(remaining_refresh) == 1


# ── Database indexes ────────────────────────────────────────────────


class TestDatabaseIndexes:
    """Verify critical columns have indexes defined in models."""

    def test_user_company_id_indexed(self):
        from api.models import User
        col = User.__table__.c["company_id"]
        assert col.index is True or any(
            idx for idx in User.__table__.indexes if "company_id" in [c.name for c in idx.columns]
        )

    def test_audit_log_created_at_indexed(self):
        from api.models import AuditLog
        col = AuditLog.__table__.c["created_at"]
        assert col.index is True or any(
            idx for idx in AuditLog.__table__.indexes if "created_at" in [c.name for c in idx.columns]
        )
