"""Tests for Phase 24 features:
- CSRD / ISSB / SECR compliance frameworks
- PCAF financed emissions
- Data review & approval workflows
- MFA (TOTP) setup/verify/disable
- Industry benchmarking
"""

from __future__ import annotations

import json
import time

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Helpers ─────────────────────────────────────────────────────────


async def _register_and_login(client: AsyncClient, email: str = "phase24@example.com") -> str:
    """Register a user and return an access token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Securepass123!",
        "full_name": "Phase24 User",
        "company_name": "Phase24Corp",
        "industry": "manufacturing",
        "region": "US",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Securepass123!",
    })
    return resp.json()["access_token"]


async def _create_report(client: AsyncClient, token: str) -> str:
    """Upload data and estimate to get a report_id."""
    client.headers["Authorization"] = f"Bearer {token}"
    up = await client.post("/api/v1/data", json={
        "year": 2024,
        "provided_data": {
            "electricity_kwh": 300_000,
            "natural_gas_therms": 5000,
            "employee_count": 150,
            "revenue_usd": 20_000_000,
            "diesel_gallons": 2000,
        },
    })
    assert up.status_code == 201
    upload_id = up.json()["id"]
    est = await client.post("/api/v1/estimate", json={"data_upload_id": upload_id})
    assert est.status_code == 201
    return est.json()["id"]


# ═════════════════════════════════════════════════════════════════════
# 1. CSRD / ISSB / SECR Compliance Frameworks
# ═════════════════════════════════════════════════════════════════════


class TestCSRDCompliance:
    """Test CSRD framework report generation."""

    async def test_csrd_report_generation(self, client: AsyncClient):
        token = await _register_and_login(client, "csrd@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "csrd",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework"] == "CSRD — ESRS E1 Climate Change"
        assert "E1_1_transition_plan" in data
        assert "E1_4_targets" in data
        assert "E1_6_gross_ghg_emissions" in data
        assert "E1_7_ghg_removals_and_offsets" in data
        assert "E1_8_internal_carbon_pricing" in data
        assert "E1_9_energy" in data
        assert "intensity_metrics" in data
        assert data["E1_6_gross_ghg_emissions"]["scope1_tco2e"] >= 0

    async def test_csrd_targets_structure(self, client: AsyncClient):
        token = await _register_and_login(client, "csrd2@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "csrd",
        })
        targets = resp.json()["E1_4_targets"]
        assert targets["target_type"] == "Absolute GHG emission reduction"
        assert "short_term_target" in targets
        assert "long_term_target" in targets
        assert targets["short_term_target"]["reduction_pct"] == 30


class TestISSBCompliance:
    """Test ISSB/IFRS S2 report generation."""

    async def test_issb_report_generation(self, client: AsyncClient):
        token = await _register_and_login(client, "issb@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "issb",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework"] == "IFRS S2 Climate-related Disclosures"
        assert "governance" in data
        assert "strategy" in data
        assert "risk_management" in data
        assert "metrics_and_targets" in data
        # Cross-industry metrics present
        metrics = data["metrics_and_targets"]["paragraph_29_cross_industry_metrics"]
        assert len(metrics) >= 5

    async def test_issb_strategy_risks(self, client: AsyncClient):
        token = await _register_and_login(client, "issb2@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "issb",
        })
        strategy = resp.json()["strategy"]
        risks = strategy["paragraph_10_risks_and_opportunities"]
        assert len(risks) >= 3
        types = {r["type"] for r in risks}
        assert "Transition risk" in types
        assert "Physical risk" in types


class TestSECRCompliance:
    """Test UK SECR report generation."""

    async def test_secr_report_generation(self, client: AsyncClient):
        token = await _register_and_login(client, "secr@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "secr",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework"] == "UK Streamlined Energy and Carbon Reporting (SECR)"
        assert "uk_ghg_emissions" in data
        assert "energy_consumption" in data
        assert "intensity_ratio" in data
        assert "methodology" in data
        assert "energy_efficiency_narrative" in data

    async def test_secr_emissions_breakdown(self, client: AsyncClient):
        token = await _register_and_login(client, "secr2@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "secr",
        })
        ghg = resp.json()["uk_ghg_emissions"]
        assert ghg["scope1_tco2e"] >= 0
        assert ghg["scope2_location_tco2e"] >= 0
        assert ghg["total_scope1_and_2_tco2e"] == round(ghg["scope1_tco2e"] + ghg["scope2_location_tco2e"], 2)


class TestComplianceValidation:
    """Test framework validation rejects unknown frameworks."""

    async def test_invalid_framework_rejected(self, client: AsyncClient):
        token = await _register_and_login(client, "invalid_fw@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "unknown_framework",
        })
        assert resp.status_code == 422  # Pydantic validation


# ═════════════════════════════════════════════════════════════════════
# 2. PCAF Financed Emissions
# ═════════════════════════════════════════════════════════════════════


class TestPCAFPortfolios:
    """Test PCAF portfolio CRUD."""

    async def _upgrade_plan(self, company_id: str):
        """Upgrade a company to pro plan for PCAF access."""
        from sqlalchemy import update
        from api.models import Subscription
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            await session.execute(
                update(Subscription).where(Subscription.company_id == company_id).values(plan="pro")
            )
            await session.commit()

    async def test_create_portfolio(self, client: AsyncClient):
        token = await _register_and_login(client, "pcaf1@example.com")
        client.headers["Authorization"] = f"Bearer {token}"
        # Get company id from profile
        me = (await client.get("/api/v1/auth/me")).json()
        await self._upgrade_plan(me["company_id"])

        resp = await client.post("/api/v1/pcaf/portfolios", json={
            "name": "2024 Lending Portfolio",
            "year": 2024,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "2024 Lending Portfolio"
        assert data["year"] == 2024

    async def test_list_portfolios(self, client: AsyncClient):
        token = await _register_and_login(client, "pcaf2@example.com")
        client.headers["Authorization"] = f"Bearer {token}"
        me = (await client.get("/api/v1/auth/me")).json()
        await self._upgrade_plan(me["company_id"])

        await client.post("/api/v1/pcaf/portfolios", json={"name": "P1", "year": 2024})
        await client.post("/api/v1/pcaf/portfolios", json={"name": "P2", "year": 2023})

        resp = await client.get("/api/v1/pcaf/portfolios")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    async def test_portfolio_not_found(self, client: AsyncClient):
        token = await _register_and_login(client, "pcaf3@example.com")
        client.headers["Authorization"] = f"Bearer {token}"
        resp = await client.get("/api/v1/pcaf/portfolios/nonexistent/summary")
        assert resp.status_code == 404


class TestPCAFAssets:
    """Test PCAF asset operations and calculations."""

    async def _setup_portfolio(self, client: AsyncClient, email: str) -> tuple[str, str]:
        """Register, upgrade to pro, create portfolio, return (token, portfolio_id)."""
        token = await _register_and_login(client, email)
        client.headers["Authorization"] = f"Bearer {token}"
        me = (await client.get("/api/v1/auth/me")).json()
        from sqlalchemy import update
        from api.models import Subscription
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            await session.execute(
                update(Subscription).where(Subscription.company_id == me["company_id"]).values(plan="pro")
            )
            await session.commit()
        portfolio = (await client.post("/api/v1/pcaf/portfolios", json={
            "name": "Test Portfolio", "year": 2024,
        })).json()
        return token, portfolio["id"]

    async def test_add_asset_auto_calculates(self, client: AsyncClient):
        _, pid = await self._setup_portfolio(client, "pcaf_a1@example.com")

        resp = await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Company A Loan",
            "asset_class": "business_loans",
            "outstanding_amount": 1_000_000,
            "total_equity_debt": 10_000_000,
            "investee_emissions_tco2e": 5000,
            "data_quality_score": 2,
        })
        assert resp.status_code == 201
        asset = resp.json()
        # Attribution factor = 1M / 10M = 0.1
        assert abs(asset["attribution_factor"] - 0.1) < 0.001
        # Financed emissions = 0.1 * 5000 = 500
        assert abs(asset["financed_emissions_tco2e"] - 500.0) < 0.01

    async def test_portfolio_summary(self, client: AsyncClient):
        _, pid = await self._setup_portfolio(client, "pcaf_a2@example.com")

        # Add two assets
        await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Loan A", "asset_class": "business_loans",
            "outstanding_amount": 500_000, "total_equity_debt": 5_000_000,
            "investee_emissions_tco2e": 10000, "data_quality_score": 2,
        })
        await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Bond B", "asset_class": "corporate_bonds",
            "outstanding_amount": 200_000, "total_equity_debt": 2_000_000,
            "investee_emissions_tco2e": 3000, "data_quality_score": 3,
        })

        resp = await client.get(f"/api/v1/pcaf/portfolios/{pid}/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["asset_count"] == 2
        assert summary["total_financed_emissions_tco2e"] > 0
        assert "business_loans" in summary["by_asset_class"]
        assert "corporate_bonds" in summary["by_asset_class"]

    async def test_delete_asset(self, client: AsyncClient):
        _, pid = await self._setup_portfolio(client, "pcaf_a3@example.com")

        asset = (await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "To Delete", "asset_class": "listed_equity",
            "outstanding_amount": 100_000, "total_equity_debt": 1_000_000,
            "investee_emissions_tco2e": 500, "data_quality_score": 4,
        })).json()

        resp = await client.delete(f"/api/v1/pcaf/portfolios/{pid}/assets/{asset['id']}")
        assert resp.status_code == 204

        # Verify it's gone
        listing = await client.get(f"/api/v1/pcaf/portfolios/{pid}/assets")
        assert listing.json()["total"] == 0

    async def test_invalid_asset_class_rejected(self, client: AsyncClient):
        _, pid = await self._setup_portfolio(client, "pcaf_a4@example.com")

        resp = await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Bad", "asset_class": "invalid_class",
            "outstanding_amount": 100, "total_equity_debt": 1000,
            "investee_emissions_tco2e": 50, "data_quality_score": 3,
        })
        assert resp.status_code == 422

    async def test_data_quality_score_range(self, client: AsyncClient):
        _, pid = await self._setup_portfolio(client, "pcaf_a5@example.com")

        # Score 0 should fail
        resp = await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Bad DQ", "asset_class": "business_loans",
            "outstanding_amount": 100, "total_equity_debt": 1000,
            "investee_emissions_tco2e": 50, "data_quality_score": 0,
        })
        assert resp.status_code == 422

        # Score 6 should fail
        resp = await client.post(f"/api/v1/pcaf/portfolios/{pid}/assets", json={
            "asset_name": "Bad DQ2", "asset_class": "business_loans",
            "outstanding_amount": 100, "total_equity_debt": 1000,
            "investee_emissions_tco2e": 50, "data_quality_score": 6,
        })
        assert resp.status_code == 422


class TestPCAFCalculations:
    """Test PCAF calculation logic directly."""

    def test_attribution_factor(self):
        from api.services.pcaf import calculate_attribution_factor
        assert calculate_attribution_factor(1_000_000, 10_000_000) == 0.1
        assert calculate_attribution_factor(0, 10_000_000) == 0.0
        assert calculate_attribution_factor(5_000_000, 5_000_000) == 1.0

    def test_financed_emissions_calculation(self):
        from api.services.pcaf import calculate_financed_emissions
        af, fe = calculate_financed_emissions(2_000_000, 10_000_000, 8000)
        assert abs(af - 0.2) < 0.001
        assert abs(fe - 1600.0) < 0.01

    def test_portfolio_summary(self):
        from api.services.pcaf import summarise_portfolio
        assets = [
            {"outstanding_amount": 1_000_000, "financed_emissions_tco2e": 500, "data_quality_score": 2, "asset_class": "business_loans"},
            {"outstanding_amount": 500_000, "financed_emissions_tco2e": 200, "data_quality_score": 3, "asset_class": "business_loans"},
        ]
        summary = summarise_portfolio(assets)
        assert summary["asset_count"] == 2
        assert summary["total_financed_emissions_tco2e"] == 700.0
        assert summary["total_outstanding"] == 1_500_000.0
        assert "business_loans" in summary["by_asset_class"]


# ═════════════════════════════════════════════════════════════════════
# 3. Data Review & Approval Workflows
# ═════════════════════════════════════════════════════════════════════


class TestDataReviewWorkflow:
    """Test the review state machine."""

    async def test_create_review(self, client: AsyncClient):
        token = await _register_and_login(client, "review1@example.com")
        report_id = await _create_report(client, token)

        resp = await client.post("/api/v1/reviews", json={"report_id": report_id})
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    async def test_submit_review(self, client: AsyncClient):
        token = await _register_and_login(client, "review2@example.com")
        report_id = await _create_report(client, token)

        review = (await client.post("/api/v1/reviews", json={"report_id": report_id})).json()
        resp = await client.post(f"/api/v1/reviews/{review['id']}/action", json={"action": "submit"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"
        assert resp.json()["submitted_by"] is not None

    async def test_approve_review_requires_admin(self, client: AsyncClient):
        token = await _register_and_login(client, "review3@example.com")
        report_id = await _create_report(client, token)

        # Demote user to member (register sets role=admin by default)
        from sqlalchemy import update
        from api.models import User
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            await session.execute(update(User).where(User.email == "review3@example.com").values(role="member"))
            await session.commit()

        review = (await client.post("/api/v1/reviews", json={"report_id": report_id})).json()
        await client.post(f"/api/v1/reviews/{review['id']}/action", json={"action": "submit"})

        # Member tries to approve — should fail
        resp = await client.post(f"/api/v1/reviews/{review['id']}/action", json={
            "action": "approve", "notes": "Looks good",
        })
        assert resp.status_code == 403

    async def test_full_approval_flow_with_admin(self, client: AsyncClient):
        """Register as admin role (first user is admin), create review, submit, approve."""
        token = await _register_and_login(client, "reviewadmin@example.com")
        report_id = await _create_report(client, token)

        # Promote to admin via DB
        from sqlalchemy import update
        from api.models import User
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            await session.execute(update(User).where(User.email == "reviewadmin@example.com").values(role="admin"))
            await session.commit()

        review = (await client.post("/api/v1/reviews", json={"report_id": report_id})).json()
        await client.post(f"/api/v1/reviews/{review['id']}/action", json={"action": "submit"})

        resp = await client.post(f"/api/v1/reviews/{review['id']}/action", json={
            "action": "approve", "notes": "Verified and approved",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["review_notes"] == "Verified and approved"

    async def test_reject_and_resubmit(self, client: AsyncClient):
        token = await _register_and_login(client, "reviewreject@example.com")
        report_id = await _create_report(client, token)

        from sqlalchemy import update
        from api.models import User
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            await session.execute(update(User).where(User.email == "reviewreject@example.com").values(role="admin"))
            await session.commit()

        review = (await client.post("/api/v1/reviews", json={"report_id": report_id})).json()
        await client.post(f"/api/v1/reviews/{review['id']}/action", json={"action": "submit"})

        resp = await client.post(f"/api/v1/reviews/{review['id']}/action", json={
            "action": "reject",
            "notes": "Missing Scope 3 data",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # Resubmit after rejection
        resp = await client.post(f"/api/v1/reviews/{review['id']}/action", json={"action": "submit"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    async def test_duplicate_review_rejected(self, client: AsyncClient):
        token = await _register_and_login(client, "reviewdup@example.com")
        report_id = await _create_report(client, token)

        await client.post("/api/v1/reviews", json={"report_id": report_id})
        resp = await client.post("/api/v1/reviews", json={"report_id": report_id})
        assert resp.status_code == 409

    async def test_list_reviews_with_filter(self, client: AsyncClient):
        token = await _register_and_login(client, "reviewlist@example.com")
        report_id = await _create_report(client, token)

        await client.post("/api/v1/reviews", json={"report_id": report_id})

        resp = await client.get("/api/v1/reviews")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        resp = await client.get("/api/v1/reviews?status_filter=draft")
        assert resp.json()["total"] >= 1

        resp = await client.get("/api/v1/reviews?status_filter=approved")
        assert resp.json()["total"] == 0


# ═════════════════════════════════════════════════════════════════════
# 4. MFA (TOTP)
# ═════════════════════════════════════════════════════════════════════


class TestMFAService:
    """Test MFA service functions directly."""

    def test_generate_totp_secret(self):
        from api.services.mfa import generate_totp_secret
        secret = generate_totp_secret()
        assert len(secret) >= 20
        # Should be base32 characters
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_generate_backup_codes(self):
        from api.services.mfa import generate_backup_codes
        codes = generate_backup_codes(8)
        assert len(codes) == 8
        assert all(len(c) == 8 for c in codes)

    def test_provisioning_uri(self):
        from api.services.mfa import build_provisioning_uri
        uri = build_provisioning_uri("JBSWY3DPEHPK3PXP", "user@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "CarbonScope" in uri
        assert "user%40example.com" in uri

    def test_verify_totp_valid(self):
        from api.services.mfa import generate_totp_secret, verify_totp, _hotp
        secret = generate_totp_secret()
        current_step = int(time.time()) // 30
        valid_code = _hotp(secret, current_step)
        assert verify_totp(secret, valid_code)

    def test_verify_totp_invalid(self):
        from api.services.mfa import generate_totp_secret, verify_totp
        secret = generate_totp_secret()
        assert not verify_totp(secret, "000000")

    def test_hash_backup_code(self):
        from api.services.mfa import hash_backup_code
        h1 = hash_backup_code("ABCD1234")
        h2 = hash_backup_code("abcd1234")  # case-insensitive
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex


class TestMFARoutes:
    """Test MFA API endpoints."""

    async def test_mfa_status_default_disabled(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/auth/mfa/status")
        assert resp.status_code == 200
        assert resp.json()["mfa_enabled"] is False

    async def test_mfa_setup_returns_secret(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/auth/mfa/setup")
        assert resp.status_code == 200
        data = resp.json()
        assert "secret" in data
        assert "provisioning_uri" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 8

    async def test_mfa_verify_activates(self, auth_client: AsyncClient):
        setup = (await auth_client.post("/api/v1/auth/mfa/setup")).json()
        secret = setup["secret"]

        # Generate a valid TOTP code
        from api.services.mfa import _hotp
        current_step = int(time.time()) // 30
        code = _hotp(secret, current_step)

        resp = await auth_client.post("/api/v1/auth/mfa/verify", json={"totp_code": code})
        assert resp.status_code == 200
        assert resp.json()["mfa_enabled"] is True

        # Status should now show enabled
        status = await auth_client.get("/api/v1/auth/mfa/status")
        assert status.json()["mfa_enabled"] is True

    async def test_mfa_verify_bad_code(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/auth/mfa/setup")
        resp = await auth_client.post("/api/v1/auth/mfa/verify", json={"totp_code": "000000"})
        assert resp.status_code == 401

    async def test_mfa_validate_after_enable(self, client: AsyncClient):
        token = await _register_and_login(client, "mfaval@example.com")
        client.headers["Authorization"] = f"Bearer {token}"

        setup = (await client.post("/api/v1/auth/mfa/setup")).json()
        secret = setup["secret"]

        from api.services.mfa import _hotp
        current_step = int(time.time()) // 30
        code = _hotp(secret, current_step)
        await client.post("/api/v1/auth/mfa/verify", json={"totp_code": code})

        # Login again — should return mfa_pending token
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "mfaval@example.com",
            "password": "Securepass123!",
        })
        assert login_resp.json()["mfa_required"] is True
        mfa_token = login_resp.json()["access_token"]

        # Validate with mfa_pending token
        code2 = _hotp(secret, int(time.time()) // 30)
        resp = await client.post(
            "/api/v1/auth/mfa/validate",
            headers={"Authorization": f"Bearer {mfa_token}"},
            json={"totp_code": code2},
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] != ""

    async def test_mfa_disable(self, client: AsyncClient):
        token = await _register_and_login(client, "mfadis@example.com")
        client.headers["Authorization"] = f"Bearer {token}"

        setup = (await client.post("/api/v1/auth/mfa/setup")).json()
        secret = setup["secret"]

        from api.services.mfa import _hotp
        current_step = int(time.time()) // 30
        code = _hotp(secret, current_step)
        await client.post("/api/v1/auth/mfa/verify", json={"totp_code": code})

        # Disable with valid code
        code2 = _hotp(secret, int(time.time()) // 30)
        resp = await client.request("DELETE", "/api/v1/auth/mfa/disable", json={"totp_code": code2})
        assert resp.status_code == 204

        # Status should now show disabled
        status = await client.get("/api/v1/auth/mfa/status")
        assert status.json()["mfa_enabled"] is False

    async def test_mfa_setup_when_already_enabled(self, client: AsyncClient):
        token = await _register_and_login(client, "mfadup@example.com")
        client.headers["Authorization"] = f"Bearer {token}"

        setup = (await client.post("/api/v1/auth/mfa/setup")).json()
        from api.services.mfa import _hotp
        code = _hotp(setup["secret"], int(time.time()) // 30)
        await client.post("/api/v1/auth/mfa/verify", json={"totp_code": code})

        # Try setup again — should 409
        resp = await client.post("/api/v1/auth/mfa/setup")
        assert resp.status_code == 409


# ═════════════════════════════════════════════════════════════════════
# 5. Industry Benchmarking
# ═════════════════════════════════════════════════════════════════════


class TestBenchmarkRoutes:
    """Test industry benchmark endpoints."""

    async def test_list_benchmarks_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/benchmarks")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_list_benchmarks_with_data(self, auth_client: AsyncClient):
        # Seed a benchmark
        from api.models import IndustryBenchmark
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            session.add(IndustryBenchmark(
                industry="manufacturing", region="US", year=2024,
                avg_scope1_tco2e=1200, avg_scope2_tco2e=800,
                avg_scope3_tco2e=3000, avg_total_tco2e=5000,
                avg_intensity_per_employee=5.0,
                avg_intensity_per_revenue=12.0,
                sample_size=150, source="Test data",
            ))
            await session.commit()

        resp = await auth_client.get("/api/v1/benchmarks?industry=manufacturing")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        bm = resp.json()["items"][0]
        assert bm["avg_total_tco2e"] == 5000

    async def test_benchmark_comparison(self, client: AsyncClient):
        token = await _register_and_login(client, "bench@example.com")
        report_id = await _create_report(client, token)

        # Seed benchmark for manufacturing/US/2024
        from api.models import IndustryBenchmark
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            session.add(IndustryBenchmark(
                industry="manufacturing", region="US", year=2024,
                avg_scope1_tco2e=1000, avg_scope2_tco2e=600,
                avg_scope3_tco2e=2500, avg_total_tco2e=4100,
                sample_size=200, source="Test benchmark",
            ))
            await session.commit()

        resp = await client.get(f"/api/v1/benchmarks/compare?report_id={report_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "company_emissions" in data
        assert "industry_average" in data
        assert "percentile_rank" in data
        assert "vs_average" in data
        assert data["industry_average"] is not None

    async def test_benchmark_comparison_no_benchmark(self, client: AsyncClient):
        token = await _register_and_login(client, "bench2@example.com")
        report_id = await _create_report(client, token)

        resp = await client.get(f"/api/v1/benchmarks/compare?report_id={report_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["industry_average"] is None
        assert data["vs_average"]["total"] is None

    async def test_benchmark_filter_by_year(self, auth_client: AsyncClient):
        from api.models import IndustryBenchmark
        from tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            session.add(IndustryBenchmark(
                industry="tech", region="GLOBAL", year=2023,
                avg_scope1_tco2e=500, avg_scope2_tco2e=300,
                avg_scope3_tco2e=1000, avg_total_tco2e=1800,
                sample_size=80, source="Test",
            ))
            session.add(IndustryBenchmark(
                industry="tech", region="GLOBAL", year=2024,
                avg_scope1_tco2e=450, avg_scope2_tco2e=280,
                avg_scope3_tco2e=900, avg_total_tco2e=1630,
                sample_size=90, source="Test",
            ))
            await session.commit()

        resp = await auth_client.get("/api/v1/benchmarks?year=2024")
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["year"] == 2024


# ═════════════════════════════════════════════════════════════════════
# 6. Compliance service unit tests (CSRD, ISSB, SECR generators)
# ═════════════════════════════════════════════════════════════════════


class TestComplianceServiceCSRD:
    """Unit tests for CSRD generator."""

    def test_csrd_with_intensity_metrics(self):
        from api.services.compliance import generate_csrd_report
        result = generate_csrd_report(
            company_name="TestCo", industry="manufacturing", region="US",
            year=2024, scope1=1000, scope2=500, scope3=3000, total=4500,
            breakdown=None, sources=["EPA"], assumptions=["Test"],
            confidence=0.85, employee_count=100, revenue_usd=10_000_000,
        )
        assert result["intensity_metrics"]["tco2e_per_employee"] == 45.0
        assert result["intensity_metrics"]["tco2e_per_million_revenue"] == 450.0

    def test_csrd_without_denominators(self):
        from api.services.compliance import generate_csrd_report
        result = generate_csrd_report(
            company_name="TestCo", industry="tech", region="EU",
            year=2024, scope1=500, scope2=200, scope3=1000, total=1700,
            breakdown=None, sources=None, assumptions=None,
            confidence=0.5, employee_count=None, revenue_usd=None,
        )
        assert result["intensity_metrics"] == {}
        assert result["data_quality"]["external_assurance"] == "Not yet assured"


class TestComplianceServiceISSB:
    """Unit tests for ISSB generator."""

    def test_issb_structure(self):
        from api.services.compliance import generate_issb_report
        result = generate_issb_report(
            company_name="FinCo", industry="finance", region="UK",
            year=2024, scope1=200, scope2=100, scope3=5000, total=5300,
            breakdown=None, sources=["DEFRA"], confidence=0.9,
            employee_count=500, revenue_usd=50_000_000,
            recommendations=[{"title": "Switch to renewables"}],
        )
        assert result["framework"] == "IFRS S2 Climate-related Disclosures"
        metrics = result["metrics_and_targets"]["paragraph_29_cross_industry_metrics"]
        metric_names = [m["metric"] for m in metrics]
        assert any("per $M revenue" in m for m in metric_names)
        assert any("per employee" in m for m in metric_names)


class TestComplianceServiceSECR:
    """Unit tests for SECR generator."""

    def test_secr_structure(self):
        from api.services.compliance import generate_secr_report
        result = generate_secr_report(
            company_name="UKCo", industry="retail", region="UK",
            year=2024, scope1=800, scope2=400, scope3=2000, total=3200,
            breakdown=None, sources=["BEIS"], confidence=0.75,
            revenue_usd=20_000_000,
        )
        assert result["framework"] == "UK Streamlined Energy and Carbon Reporting (SECR)"
        assert result["uk_ghg_emissions"]["total_scope1_and_2_tco2e"] == 1200
        assert result["methodology"]["emission_factors"] == "UK DEFRA / BEIS Conversion Factors"
        assert result["intensity_ratio"]["value"] is not None
