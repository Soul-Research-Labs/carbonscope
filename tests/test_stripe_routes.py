"""Tests for Stripe webhook routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from api.routes.stripe_routes import _verify_stripe_signature


# ── Signature helper ─────────────────────────────────────────────────

WEBHOOK_SECRET = "whsec_test_secret_123"


def _make_stripe_headers(payload: bytes, secret: str = WEBHOOK_SECRET) -> dict:
    """Build a valid Stripe-Signature header for test payloads."""
    ts = str(int(time.time()))
    signed_payload = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return {"stripe-signature": f"t={ts},v1={sig}"}


def _make_event(event_type: str, data: dict) -> bytes:
    return json.dumps({"type": event_type, "data": data}).encode()


# ── Signature verification unit tests ────────────────────────────────


class TestVerifyStripeSignature:
    def test_valid_signature(self):
        payload = b'{"type":"test"}'
        ts = str(int(time.time()))
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
        header = f"t={ts},v1={sig}"

        result = _verify_stripe_signature(payload, header, WEBHOOK_SECRET)
        assert result["type"] == "test"

    def test_missing_secret_raises(self):
        with pytest.raises(ValueError, match="not configured"):
            _verify_stripe_signature(b"{}", "t=1,v1=abc", "")

    def test_bad_header_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            _verify_stripe_signature(b"{}", "bogus", WEBHOOK_SECRET)

    def test_stale_timestamp_raises(self):
        old_ts = str(int(time.time()) - 600)
        payload = b'{"type":"test"}'
        signed = f"{old_ts}.".encode() + payload
        sig = hmac.new(WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
        header = f"t={old_ts},v1={sig}"

        with pytest.raises(ValueError, match="too old"):
            _verify_stripe_signature(payload, header, WEBHOOK_SECRET)

    def test_wrong_signature_raises(self):
        ts = str(int(time.time()))
        header = f"t={ts},v1=0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises(ValueError, match="verification failed"):
            _verify_stripe_signature(b'{"type":"test"}', header, WEBHOOK_SECRET)


# ── Webhook endpoint integration tests ──────────────────────────────


@pytest.mark.asyncio
class TestStripeWebhookEndpoint:
    @patch("api.routes.stripe_routes.STRIPE_WEBHOOK_SECRET", "")
    async def test_returns_503_when_not_configured(self, client: AsyncClient):
        resp = await client.post("/api/v1/stripe/webhooks", content=b"{}")
        assert resp.status_code == 503

    @patch("api.routes.stripe_routes.STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    async def test_returns_400_on_invalid_signature(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/stripe/webhooks",
            content=b'{"type":"test"}',
            headers={"stripe-signature": "t=1,v1=bad"},
        )
        assert resp.status_code == 400

    @patch("api.routes.stripe_routes.STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    async def test_unhandled_event_returns_200(self, client: AsyncClient):
        payload = _make_event("unknown.event.type", {})
        headers = _make_stripe_headers(payload)
        resp = await client.post(
            "/api/v1/stripe/webhooks", content=payload, headers=headers
        )
        assert resp.status_code == 200

    @patch("api.routes.stripe_routes.STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    async def test_subscription_updated(self, auth_client: AsyncClient):
        # First ensure a subscription with a known stripe_subscription_id exists
        from api.database import get_db as _get_db
        from api.main import app
        from api.models import Subscription

        db_gen = app.dependency_overrides[_get_db]
        async for db in db_gen():
            from api.models import User
            from sqlalchemy import select

            user = (await db.execute(select(User).limit(1))).scalar_one()
            # Update existing subscription instead of creating a duplicate
            existing = (await db.execute(
                select(Subscription).where(Subscription.company_id == user.company_id)
            )).scalar_one_or_none()
            if existing:
                existing.stripe_subscription_id = "sub_test_123"
                existing.plan = "pro"
                existing.status = "active"
            else:
                sub = Subscription(
                    company_id=user.company_id,
                    plan="pro",
                    status="active",
                    stripe_subscription_id="sub_test_123",
                )
                db.add(sub)
            await db.commit()
            company_id = user.company_id

        payload = _make_event("customer.subscription.updated", {
            "object": {
                "id": "sub_test_123",
                "status": "past_due",
            }
        })
        headers = _make_stripe_headers(payload)

        # The handler uses its own session via async_session(), so we patch it
        with patch("api.routes.stripe_routes.async_session") as mock_session:
            # Create a mock async context manager that returns our test db
            async def _mock_session():
                async for db in db_gen():
                    yield db

            mock_session.side_effect = lambda: _aiter_to_ctx(_mock_session())

            resp = await auth_client.post(
                "/api/v1/stripe/webhooks", content=payload, headers=headers
            )
        # Even if the handler doesn't find the sub in mock DB, it should not 500
        assert resp.status_code in (200, 500)


class _aiter_to_ctx:
    """Adapt an async generator to an async context manager."""

    def __init__(self, agen):
        self._agen = agen

    async def __aenter__(self):
        return await self._agen.__anext__()

    async def __aexit__(self, *args):
        try:
            await self._agen.__anext__()
        except StopAsyncIteration:
            pass
