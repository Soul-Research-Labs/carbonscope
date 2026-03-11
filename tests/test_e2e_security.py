"""End-to-end integration and security tests."""

from __future__ import annotations

import time
from typing import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.config import ALGORITHM, SECRET_KEY
from api.database import get_db
from api.limiter import limiter
from api.main import app
from tests.conftest import _override_get_db, TestSessionLocal

app.dependency_overrides[get_db] = _override_get_db


# ── Helpers ──────────────────────────────────────────────────────────


async def _register_and_login(client: AsyncClient, email: str, password: str, company_name: str) -> str:
    """Register a user and return an access token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
        "company_name": company_name,
        "industry": "manufacturing",
        "region": "US",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    return resp.json()["access_token"]


# ── E2E: Full lifecycle test ────────────────────────────────────────


@pytest.mark.asyncio
class TestE2ELifecycle:
    async def test_full_workflow(self, client: AsyncClient):
        """Register → Upload data → Estimate → List reports → Export → Dashboard."""
        # 1. Register + login
        token = await _register_and_login(client, "e2e@test.com", "StrongPass1", "E2ECorp")
        client.headers["Authorization"] = f"Bearer {token}"

        # 2. Upload operational data
        upload_resp = await client.post("/api/v1/data", json={
            "year": 2025,
            "provided_data": {
                "fuel_use_liters": 40_000,
                "fuel_type": "diesel",
                "electricity_kwh": 300_000,
                "employee_count": 80,
                "revenue_usd": 5_000_000,
            },
            "notes": "FY2025 data",
        })
        assert upload_resp.status_code == 201
        upload_id = upload_resp.json()["id"]

        # 3. Run estimation
        est_resp = await client.post("/api/v1/estimate", json={
            "data_upload_id": upload_id,
        })
        assert est_resp.status_code == 201
        report = est_resp.json()
        assert report["scope1"] > 0
        assert report["scope2"] > 0
        assert report["total"] > 0
        report_id = report["id"]

        # 4. List reports (paginated)
        list_resp = await client.get("/api/v1/reports")
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == report_id

        # 5. Export as CSV
        csv_resp = await client.get("/api/v1/reports/export?format=csv")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]
        lines = csv_resp.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 row

        # 6. Dashboard
        dash_resp = await client.get("/api/v1/dashboard")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["reports_count"] == 1
        assert dash["data_uploads_count"] == 1
        assert dash["latest_report"]["id"] == report_id

        # 7. Soft-delete the report
        del_resp = await client.delete(f"/api/v1/reports/{report_id}")
        assert del_resp.status_code == 204

        # 8. Verify it's gone from listing
        list_resp2 = await client.get("/api/v1/reports")
        assert list_resp2.json()["total"] == 0


# ── Security: Cross-company access ──────────────────────────────────


@pytest.mark.asyncio
class TestCrossCompanyIsolation:
    async def test_cannot_access_other_company_data(self, client: AsyncClient):
        """User A cannot see User B's data uploads or reports."""
        # Register two users in different companies
        token_a = await _register_and_login(client, "usera@corp.com", "StrongPass1", "CorpA")
        token_b = await _register_and_login(client, "userb@corp.com", "StrongPass1", "CorpB")

        # User A uploads data
        client.headers["Authorization"] = f"Bearer {token_a}"
        upload_resp = await client.post("/api/v1/data", json={
            "year": 2025,
            "provided_data": {"electricity_kwh": 100_000},
        })
        upload_id = upload_resp.json()["id"]

        # User A creates a report
        est_resp = await client.post("/api/v1/estimate", json={
            "data_upload_id": upload_id,
        })
        report_id = est_resp.json()["id"]

        # User B cannot see User A's data
        client.headers["Authorization"] = f"Bearer {token_b}"

        resp_data = await client.get("/api/v1/data")
        assert resp_data.json()["total"] == 0

        resp_upload = await client.get(f"/api/v1/data/{upload_id}")
        assert resp_upload.status_code == 404

        resp_reports = await client.get("/api/v1/reports")
        assert resp_reports.json()["total"] == 0

        resp_report = await client.get(f"/api/v1/reports/{report_id}")
        assert resp_report.status_code == 404

        # User B cannot delete User A's data
        resp_del = await client.delete(f"/api/v1/data/{upload_id}")
        assert resp_del.status_code == 404

        resp_del_report = await client.delete(f"/api/v1/reports/{report_id}")
        assert resp_del_report.status_code == 404


# ── Security: JWT validation ────────────────────────────────────────


@pytest.mark.asyncio
class TestJWTSecurity:
    async def test_expired_token_rejected(self, client: AsyncClient):
        """An expired JWT should be rejected."""
        expired = jwt.encode(
            {"sub": "fake@test.com", "exp": int(time.time()) - 60},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        client.headers["Authorization"] = f"Bearer {expired}"
        resp = await client.get("/api/v1/company")
        assert resp.status_code in (401, 403)

    async def test_invalid_signature_rejected(self, client: AsyncClient):
        """A JWT signed with the wrong key should be rejected."""
        bad_token = jwt.encode(
            {"sub": "fake@test.com", "exp": int(time.time()) + 3600},
            "wrong-secret-key-that-is-long-enough-for-hmac",
            algorithm=ALGORITHM,
        )
        client.headers["Authorization"] = f"Bearer {bad_token}"
        resp = await client.get("/api/v1/company")
        assert resp.status_code in (401, 403)

    async def test_no_token_rejected(self, client: AsyncClient):
        """Requests without a token should be rejected."""
        resp = await client.get("/api/v1/company")
        assert resp.status_code in (401, 403)

    async def test_malformed_token_rejected(self, client: AsyncClient):
        """A malformed token should be rejected."""
        client.headers["Authorization"] = "Bearer not.a.valid.jwt"
        resp = await client.get("/api/v1/company")
        assert resp.status_code in (401, 403)


# ── Security: Rate limiting ─────────────────────────────────────────


@pytest.mark.asyncio
class TestRateLimiting:
    async def test_rate_limit_enforced_on_login(self, client: AsyncClient):
        """Login endpoint should enforce rate limiting when enabled."""
        # Re-enable rate limiter for this test
        limiter.enabled = True
        try:
            # Register first
            await client.post("/api/v1/auth/register", json={
                "email": "ratelimit@test.com",
                "password": "StrongPass1",
                "full_name": "Rate Test",
                "company_name": "RateCorp",
                "industry": "technology",
                "region": "US",
            })

            # Fire many login requests — beyond the 10/minute limit
            statuses = []
            for _ in range(15):
                resp = await client.post("/api/v1/auth/login", json={
                    "email": "ratelimit@test.com",
                    "password": "StrongPass1",
                })
                statuses.append(resp.status_code)

            # At least one should be rate-limited (429)
            assert 429 in statuses, f"Expected 429 in responses, got: {set(statuses)}"
        finally:
            limiter.enabled = False
            # Clear rate limiter state
            if hasattr(limiter, "_limiter") and hasattr(limiter._limiter, "_storage"):
                limiter._limiter._storage.reset()


# ── Security: Input validation ──────────────────────────────────────


@pytest.mark.asyncio
class TestInputValidation:
    async def test_register_weak_password_rejected(self, client: AsyncClient):
        """Password without uppercase should be rejected (if validation exists)."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@test.com",
            "password": "short",
            "full_name": "Weak User",
            "company_name": "WeakCorp",
            "industry": "manufacturing",
            "region": "US",
        })
        assert resp.status_code == 422

    async def test_register_invalid_email_rejected(self, client: AsyncClient):
        """Invalid email format should be rejected."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "StrongPass1",
            "full_name": "Bad Email",
            "company_name": "Corp",
            "industry": "manufacturing",
            "region": "US",
        })
        assert resp.status_code == 422

    async def test_upload_invalid_year_rejected(self, auth_client: AsyncClient):
        """Year out of range should be rejected."""
        resp = await auth_client.post("/api/v1/data", json={
            "year": 1899,
            "provided_data": {"electricity_kwh": 100},
        })
        assert resp.status_code == 422

    async def test_webhook_invalid_event_rejected(self, auth_client: AsyncClient):
        """Invalid event types should be rejected with 400."""
        resp = await auth_client.post("/api/v1/webhooks/", json={
            "url": "https://example.com/hook",
            "event_types": ["fake.event"],
        })
        assert resp.status_code == 400
