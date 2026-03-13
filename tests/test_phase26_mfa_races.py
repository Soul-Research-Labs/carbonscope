"""Tests for Phase 26 — MFA login enforcement, race conditions, mfa_pending token rejection."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app


# ── Helpers ──────────────────────────────────────────────────────────

async def _register_user(client: AsyncClient, email: str = "mfa@test.com") -> dict:
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Securepass123!",
        "full_name": "MFA User",
        "company_name": "MFACorp",
        "industry": "technology",
        "region": "US",
    })
    return resp.json()


async def _login(client: AsyncClient, email: str = "mfa@test.com") -> dict:
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Securepass123!",
    })
    return resp.json()


async def _enable_mfa(client: AsyncClient, token: str) -> str:
    """Enable MFA for a user and return the TOTP secret."""
    from api.services.mfa import generate_totp_code
    headers = {"Authorization": f"Bearer {token}"}
    setup_resp = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    secret = setup_resp.json()["secret"]

    # Generate valid TOTP code from the secret
    code = generate_totp_code(secret)
    await client.post("/api/v1/auth/mfa/verify", headers=headers, json={"totp_code": code})
    return secret


# ── MFA Login Enforcement Tests ──────────────────────────────────────


class TestMFALoginEnforcement:
    """Login should return mfa_required=True when MFA is enabled, not full tokens."""

    @pytest.mark.asyncio
    async def test_login_without_mfa_returns_full_tokens(self, client: AsyncClient):
        """Users without MFA should get full access + refresh tokens."""
        await _register_user(client, "nomfa@test.com")
        data = await _login(client, "nomfa@test.com")
        assert data.get("mfa_required", False) is False
        assert data["access_token"] != ""
        assert data["refresh_token"] != ""

    @pytest.mark.asyncio
    async def test_login_with_mfa_returns_pending_token(self, client: AsyncClient):
        """Users with MFA enabled should get mfa_required=True and no refresh token."""
        await _register_user(client)
        login_data = await _login(client)
        token = login_data["access_token"]

        # Enable MFA
        await _enable_mfa(client, token)

        # Login again — should require MFA
        data = await _login(client)
        assert data["mfa_required"] is True
        assert data["refresh_token"] == ""  # no refresh token until MFA verified
        assert data["access_token"] != ""   # mfa_pending token

    @pytest.mark.asyncio
    async def test_mfa_pending_token_rejected_by_normal_endpoints(self, client: AsyncClient):
        """An mfa_pending token should be rejected by normal auth-protected endpoints."""
        await _register_user(client)
        login_data = await _login(client)
        token = login_data["access_token"]
        await _enable_mfa(client, token)

        # Login again to get mfa_pending token
        data = await _login(client)
        mfa_token = data["access_token"]

        # Try to access a normal endpoint with mfa_pending token
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {mfa_token}"})
        assert resp.status_code == 403
        assert "MFA verification required" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_mfa_validate_completes_login(self, client: AsyncClient):
        """POST /auth/mfa/validate with valid TOTP should return full tokens."""
        from api.services.mfa import generate_totp_code

        await _register_user(client)
        login_data = await _login(client)
        token = login_data["access_token"]
        secret = await _enable_mfa(client, token)

        # Login again (MFA pending)
        pending = await _login(client)
        mfa_token = pending["access_token"]

        # Validate with correct TOTP
        code = generate_totp_code(secret)
        resp = await client.post(
            "/api/v1/auth/mfa/validate",
            headers={"Authorization": f"Bearer {mfa_token}"},
            json={"totp_code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["refresh_token"] != ""
        assert data.get("mfa_verified", False) is True

        # Full token should work on normal endpoints
        full_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert full_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mfa_validate_rejects_invalid_totp(self, client: AsyncClient):
        """POST /auth/mfa/validate with wrong TOTP should return 401."""
        await _register_user(client)
        login_data = await _login(client)
        token = login_data["access_token"]
        await _enable_mfa(client, token)

        pending = await _login(client)
        mfa_token = pending["access_token"]

        resp = await client.post(
            "/api/v1/auth/mfa/validate",
            headers={"Authorization": f"Bearer {mfa_token}"},
            json={"totp_code": "000000"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_validate_rejects_normal_token(self, client: AsyncClient):
        """POST /auth/mfa/validate should reject a normal access token."""
        await _register_user(client, "normal@test.com")
        data = await _login(client, "normal@test.com")
        token = data["access_token"]

        resp = await client.post(
            "/api/v1/auth/mfa/validate",
            headers={"Authorization": f"Bearer {token}"},
            json={"totp_code": "123456"},
        )
        assert resp.status_code == 400
        assert "Expected MFA pending token" in resp.json()["detail"]


# ── Race Condition Tests ─────────────────────────────────────────────


class TestRaceConditions:
    """Ensure IntegrityError from concurrent operations returns proper HTTP errors."""

    @pytest.mark.asyncio
    async def test_duplicate_registration_returns_409(self, client: AsyncClient):
        """Registering the same email twice should always return 409, not 500."""
        payload = {
            "email": "dup@test.com",
            "password": "Securepass123!",
            "full_name": "Dup User",
            "company_name": "DupCorp",
            "industry": "technology",
            "region": "US",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 409
        assert "already registered" in resp2.json()["detail"].lower()
