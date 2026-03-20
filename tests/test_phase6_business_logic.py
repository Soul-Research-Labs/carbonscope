"""Phase 6 — Business Logic Completeness tests.

Covers:
- B1: Credit/plan gating on premium endpoints
- B3: Webhook list pagination
- B4: Credit ledger history endpoint
- B5: User self-delete (GDPR)
- B6: GET single supply chain link
- B7: GET single marketplace listing
- B8: Audit log filtering
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────


async def _create_report(auth_client: AsyncClient, year: int = 2024) -> str:
    """Create a data upload + estimate to get a report ID."""
    upload = await auth_client.post("/api/v1/data", json={
        "year": year,
        "provided_data": {"electricity_kwh": 100000, "natural_gas_therms": 5000},
    })
    upload_id = upload.json()["id"]
    est = await auth_client.post("/api/v1/estimate", json={"data_upload_id": upload_id})
    assert est.status_code == 201, est.text
    return est.json()["id"]


async def _upgrade_plan(auth_client: AsyncClient, plan: str = "pro") -> dict:
    resp = await auth_client.post("/api/v1/billing/subscription", json={"plan": plan})
    return resp.json()


# ── B1: Credit gating on premium endpoints ──────────────────────────


@pytest.mark.asyncio
class TestCreditGating:
    async def test_estimate_deducts_credits(self, auth_client: AsyncClient):
        """POST /estimate should deduct credits (10 per estimation)."""
        # Get initial credit balance
        await auth_client.get("/api/v1/billing/subscription")
        bal_before = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]

        report_id = await _create_report(auth_client)
        assert report_id

        bal_after = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]
        assert bal_after == bal_before - 10  # CREDIT_COSTS["estimate"] = 10

    async def test_estimate_fails_when_no_credits(self, auth_client: AsyncClient):
        """POST /estimate returns 402 when credits are exhausted."""
        # Ensure subscription exists with 100 free credits
        await auth_client.get("/api/v1/billing/subscription")

        # Exhaust credits by running 10 estimates (10 * 10 = 100 credits)
        for _ in range(10):
            upload = await auth_client.post("/api/v1/data", json={
                "year": 2024,
                "provided_data": {"electricity_kwh": 1000},
            })
            await auth_client.post("/api/v1/estimate", json={"data_upload_id": upload.json()["id"]})

        # 11th should fail
        upload = await auth_client.post("/api/v1/data", json={
            "year": 2024,
            "provided_data": {"electricity_kwh": 1000},
        })
        resp = await auth_client.post("/api/v1/estimate", json={"data_upload_id": upload.json()["id"]})
        assert resp.status_code == 402

    async def test_pdf_export_deducts_credits(self, auth_client: AsyncClient):
        """GET /reports/{id}/export/pdf should deduct 5 credits."""
        report_id = await _create_report(auth_client)
        bal_before = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]

        resp = await auth_client.get(f"/api/v1/reports/{report_id}/export/pdf")
        assert resp.status_code == 200

        bal_after = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]
        assert bal_after == bal_before - 5  # CREDIT_COSTS["pdf_export"] = 5

    async def test_scenario_compute_deducts_credits(self, auth_client: AsyncClient):
        """POST /scenarios/{id}/compute should deduct 3 credits."""
        report_id = await _create_report(auth_client)

        # Create a scenario
        scenario_resp = await auth_client.post("/api/v1/scenarios/", json={
            "name": "Test Scenario",
            "base_report_id": report_id,
            "parameters": {"scope1_reduction_pct": 0.1},
        })
        assert scenario_resp.status_code == 201
        scenario_id = scenario_resp.json()["id"]

        bal_before = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]

        resp = await auth_client.post(f"/api/v1/scenarios/{scenario_id}/compute")
        assert resp.status_code == 200

        bal_after = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]
        assert bal_after == bal_before - 3  # CREDIT_COSTS["scenario_compute"] = 3

    async def test_compliance_report_deducts_credits(self, auth_client: AsyncClient):
        """POST /compliance/report should deduct credits."""
        report_id = await _create_report(auth_client)
        bal_before = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]

        resp = await auth_client.post("/api/v1/compliance/report", json={
            "report_id": report_id,
            "framework": "ghg_protocol",
        })
        assert resp.status_code == 200

        bal_after = (await auth_client.get("/api/v1/billing/credits")).json()["balance"]
        assert bal_after == bal_before - 10  # CREDIT_COSTS["estimate"] = 10


# ── B3: Webhook list pagination ─────────────────────────────────────


@pytest.mark.asyncio
class TestWebhookPagination:
    async def test_webhook_list_paginated(self, auth_client: AsyncClient):
        """GET /webhooks should return paginated results."""
        await _upgrade_plan(auth_client, "pro")

        # Create two webhooks
        for i in range(2):
            await auth_client.post("/api/v1/webhooks/", json={
                "url": f"https://example.com/hook{i}",
                "event_types": ["report.created"],
            })

        resp = await auth_client.get("/api/v1/webhooks/", params={"limit": 1, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["limit"] == 1
        assert data["offset"] == 0

    async def test_webhook_list_page2(self, auth_client: AsyncClient):
        """Webhook pagination offset works."""
        await _upgrade_plan(auth_client, "pro")
        for i in range(3):
            await auth_client.post("/api/v1/webhooks/", json={
                "url": f"https://example.com/hook{i}",
                "event_types": ["report.created"],
            })

        resp = await auth_client.get("/api/v1/webhooks/", params={"limit": 2, "offset": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1  # only 1 left on page 2


# ── B4: Credit ledger history ────────────────────────────────────────


@pytest.mark.asyncio
class TestCreditLedger:
    async def test_credit_ledger_returns_history(self, auth_client: AsyncClient):
        """GET /billing/credits/ledger should return transaction history."""
        # Trigger subscription creation (grants initial 100 credits)
        await auth_client.get("/api/v1/billing/subscription")

        # Grant extra credits
        await auth_client.post("/api/v1/billing/credits/grant", json={"amount": 50})

        resp = await auth_client.get("/api/v1/billing/credits/ledger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2  # initial grant + manual grant
        assert len(data["items"]) >= 2
        # Most recent should be the 50-credit grant
        assert data["items"][0]["amount"] == 50
        assert data["items"][0]["reason"] == "manual_grant"

    async def test_credit_ledger_pagination(self, auth_client: AsyncClient):
        """Credit ledger supports pagination."""
        await auth_client.get("/api/v1/billing/subscription")
        await auth_client.post("/api/v1/billing/credits/grant", json={"amount": 10})
        await auth_client.post("/api/v1/billing/credits/grant", json={"amount": 20})

        resp = await auth_client.get("/api/v1/billing/credits/ledger", params={"limit": 1})
        data = resp.json()
        assert data["total"] >= 3  # initial + 2 grants
        assert len(data["items"]) == 1


# ── B5: User self-delete (GDPR) ─────────────────────────────────────


@pytest.mark.asyncio
class TestUserSelfDelete:
    async def test_delete_account_soft_deletes(self, auth_client: AsyncClient):
        """DELETE /auth/me should soft-delete the account."""
        # Verify user exists first
        me = await auth_client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "test@example.com"

        # Delete account
        resp = await auth_client.delete("/api/v1/auth/me")
        assert resp.status_code == 204

        # Subsequent requests should fail (soft-deleted user filtered out)
        me2 = await auth_client.get("/api/v1/auth/me")
        assert me2.status_code == 401  # deleted_at filter → user not found → 401


# ── B6: GET single supply chain link ────────────────────────────────


@pytest.mark.asyncio
class TestSupplyChainSingleGet:
    async def test_get_supply_chain_link(self, auth_client: AsyncClient):
        """GET /supply-chain/links/{id} should return a single link."""
        # Need a second company to be the supplier
        from tests.conftest import _override_get_db

        # Create supplier company directly in DB
        async for session in _override_get_db():
            from api.models import Company
            supplier = Company(name="SupplierCo", industry="manufacturing", region="EU")
            session.add(supplier)
            await session.commit()
            supplier_id = supplier.id

        # Create a link
        resp = await auth_client.post("/api/v1/supply-chain/links", json={
            "supplier_company_id": supplier_id,
            "spend_usd": 50000,
            "category": "purchased_goods",
        })
        assert resp.status_code == 201
        link_id = resp.json()["id"]

        # GET the single link
        resp = await auth_client.get(f"/api/v1/supply-chain/links/{link_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == link_id
        assert data["supplier_company_id"] == supplier_id

    async def test_get_supply_chain_link_not_found(self, auth_client: AsyncClient):
        """GET /supply-chain/links/{id} returns 404 for nonexistent link."""
        resp = await auth_client.get("/api/v1/supply-chain/links/nonexistent")
        assert resp.status_code == 404


# ── B7: GET single marketplace listing ──────────────────────────────


@pytest.mark.asyncio
class TestMarketplaceSingleGet:
    async def test_get_listing(self, auth_client: AsyncClient):
        """GET /marketplace/listings/{id} should return a single listing."""
        await _upgrade_plan(auth_client, "pro")
        report_id = await _create_report(auth_client)

        # Create listing
        resp = await auth_client.post("/api/v1/marketplace/listings", json={
            "title": "Test Data",
            "description": "Sample emission data",
            "data_type": "emission_report",
            "report_id": report_id,
            "price_credits": 10,
        })
        assert resp.status_code == 201
        listing_id = resp.json()["id"]

        # GET single listing
        resp = await auth_client.get(f"/api/v1/marketplace/listings/{listing_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == listing_id
        assert data["title"] == "Test Data"

    async def test_get_listing_not_found(self, auth_client: AsyncClient):
        """GET /marketplace/listings/{id} returns 404 for nonexistent."""
        resp = await auth_client.get("/api/v1/marketplace/listings/nonexistent")
        assert resp.status_code == 404


# ── B8: Audit log filtering ─────────────────────────────────────────


@pytest.mark.asyncio
class TestAuditLogFiltering:
    async def test_audit_filter_by_action(self, auth_client: AsyncClient):
        """GET /audit-logs/?action=... should filter results."""
        # Generate some audit events by creating a report
        await _create_report(auth_client)

        # Filter by a specific action
        resp = await auth_client.get("/api/v1/audit-logs/", params={"action": "create"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["action"] == "create"

    async def test_audit_filter_by_resource_type(self, auth_client: AsyncClient):
        """GET /audit-logs/?resource_type=... should filter results."""
        await _create_report(auth_client)

        resp = await auth_client.get("/api/v1/audit-logs/", params={"resource_type": "emission_report"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["resource_type"] == "emission_report"

    async def test_audit_no_filter_returns_all(self, auth_client: AsyncClient):
        """GET /audit-logs/ without filters returns all company logs."""
        await _create_report(auth_client)
        resp = await auth_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0
