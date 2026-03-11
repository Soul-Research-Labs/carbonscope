"""Tests for coverage gaps: soft deletes, token refresh, supply chain pagination,
audit logs, webhook toggle, and cross-company isolation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestTokenRefresh:
    async def test_refresh_returns_new_token(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_without_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code in (401, 403)  # no bearer token


@pytest.mark.asyncio
class TestSoftDeletes:
    async def test_deleted_upload_hidden_from_list(self, auth_client: AsyncClient):
        # Create a data upload
        upload_resp = await auth_client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 50000},
        })
        upload_id = upload_resp.json()["id"]

        # Delete it
        del_resp = await auth_client.delete(f"/api/v1/data/{upload_id}")
        assert del_resp.status_code == 204

        # Verify it's not in the list
        list_resp = await auth_client.get("/api/v1/data")
        items = list_resp.json()["items"]
        assert all(item["id"] != upload_id for item in items)

    async def test_deleted_upload_not_found_by_id(self, auth_client: AsyncClient):
        upload_resp = await auth_client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 10000},
        })
        upload_id = upload_resp.json()["id"]
        await auth_client.delete(f"/api/v1/data/{upload_id}")

        get_resp = await auth_client.get(f"/api/v1/data/{upload_id}")
        assert get_resp.status_code == 404

    async def test_deleted_report_hidden_from_list(self, auth_client: AsyncClient):
        # Create upload + estimate
        upload_resp = await auth_client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 50000, "natural_gas_therms": 2000},
        })
        est_resp = await auth_client.post("/api/v1/estimate", json={
            "data_upload_id": upload_resp.json()["id"],
        })
        report_id = est_resp.json()["id"]

        # Delete
        del_resp = await auth_client.delete(f"/api/v1/reports/{report_id}")
        assert del_resp.status_code == 204

        # Not in list
        list_resp = await auth_client.get("/api/v1/reports")
        items = list_resp.json()["items"]
        assert all(r["id"] != report_id for r in items)


@pytest.mark.asyncio
class TestSupplyChainPagination:
    async def test_suppliers_returns_paginated(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/supply-chain/suppliers?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_buyers_returns_paginated(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/supply-chain/buyers?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["limit"] == 5


@pytest.mark.asyncio
class TestWebhookToggle:
    async def test_create_and_toggle_webhook(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post("/api/v1/webhooks/", json={
            "url": "https://example.com/hook",
            "event_types": ["report.created"],
        })
        assert create_resp.status_code == 201
        wh = create_resp.json()
        assert wh["active"] is True
        assert "secret" in wh  # secret returned on creation

        # List — secret should be hidden
        list_resp = await auth_client.get("/api/v1/webhooks/")
        listed = list_resp.json()
        assert len(listed) >= 1
        assert "secret" not in listed[0]

        # Toggle off
        toggle_resp = await auth_client.patch(f"/api/v1/webhooks/{wh['id']}", json={"active": False})
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["active"] is False
        assert "secret" not in toggle_resp.json()

        # Toggle back on
        toggle_resp2 = await auth_client.patch(f"/api/v1/webhooks/{wh['id']}", json={"active": True})
        assert toggle_resp2.json()["active"] is True


@pytest.mark.asyncio
class TestAuditLogs:
    async def test_audit_log_created_on_password_change(self, auth_client: AsyncClient):
        # Change password triggers audit
        await auth_client.post("/api/v1/auth/change-password", json={
            "current_password": "Securepass123",
            "new_password": "Newpassword456",
        })

        resp = await auth_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        actions = [entry["action"] for entry in data["items"]]
        assert "change_password" in actions

    async def test_audit_log_created_on_company_update(self, auth_client: AsyncClient):
        await auth_client.patch("/api/v1/company", json={"name": "UpdatedCorp"})

        resp = await auth_client.get("/api/v1/audit-logs/")
        data = resp.json()
        actions = [entry["action"] for entry in data["items"]]
        assert "update" in actions
        resource_types = [entry["resource_type"] for entry in data["items"]]
        assert "company" in resource_types

    async def test_audit_log_on_data_upload_delete(self, auth_client: AsyncClient):
        upload_resp = await auth_client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 1000},
        })
        upload_id = upload_resp.json()["id"]
        await auth_client.delete(f"/api/v1/data/{upload_id}")

        resp = await auth_client.get("/api/v1/audit-logs/")
        data = resp.json()
        delete_entries = [e for e in data["items"] if e["action"] == "delete" and e["resource_type"] == "data_upload"]
        assert len(delete_entries) >= 1

    async def test_audit_log_on_report_delete(self, auth_client: AsyncClient):
        upload_resp = await auth_client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 50000, "natural_gas_therms": 2000},
        })
        est_resp = await auth_client.post("/api/v1/estimate", json={
            "data_upload_id": upload_resp.json()["id"],
        })
        report_id = est_resp.json()["id"]
        await auth_client.delete(f"/api/v1/reports/{report_id}")

        resp = await auth_client.get("/api/v1/audit-logs/")
        data = resp.json()
        delete_entries = [e for e in data["items"] if e["action"] == "delete" and e["resource_type"] == "emission_report"]
        assert len(delete_entries) >= 1


@pytest.mark.asyncio
class TestCrossCompanyIsolation:
    async def _make_user(self, client: AsyncClient, email: str, company: str) -> str:
        """Register a user and return their token."""
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123",
            "full_name": "Isolation User",
            "company_name": company,
            "industry": "technology",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "Password123",
        })
        return resp.json()["access_token"]

    async def test_cannot_see_other_company_uploads(self, client: AsyncClient):
        token_a = await self._make_user(client, "comp_a@test.com", "CompanyA")
        token_b = await self._make_user(client, "comp_b@test.com", "CompanyB")

        # A creates upload
        client.headers["Authorization"] = f"Bearer {token_a}"
        upload_resp = await client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 5000},
        })
        upload_id = upload_resp.json()["id"]

        # B cannot see A's upload
        client.headers["Authorization"] = f"Bearer {token_b}"
        list_resp = await client.get("/api/v1/data")
        items = list_resp.json()["items"]
        assert all(item["id"] != upload_id for item in items)

    async def test_cannot_delete_other_company_upload(self, client: AsyncClient):
        token_a = await self._make_user(client, "iso_a@test.com", "IsoA")
        token_b = await self._make_user(client, "iso_b@test.com", "IsoB")

        client.headers["Authorization"] = f"Bearer {token_a}"
        upload_resp = await client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 5000},
        })
        upload_id = upload_resp.json()["id"]

        # B tries to delete A's upload
        client.headers["Authorization"] = f"Bearer {token_b}"
        del_resp = await client.delete(f"/api/v1/data/{upload_id}")
        assert del_resp.status_code == 404

    async def test_cannot_see_other_company_reports(self, client: AsyncClient):
        token_a = await self._make_user(client, "rep_a@test.com", "RepA")
        token_b = await self._make_user(client, "rep_b@test.com", "RepB")

        # A creates report
        client.headers["Authorization"] = f"Bearer {token_a}"
        upload_resp = await client.post("/api/v1/data", json={
            "year": 2023,
            "provided_data": {"electricity_kwh": 50000, "natural_gas_therms": 2000},
        })
        est_resp = await client.post("/api/v1/estimate", json={
            "data_upload_id": upload_resp.json()["id"],
        })
        report_id = est_resp.json()["id"]

        # B cannot see A's report
        client.headers["Authorization"] = f"Bearer {token_b}"
        list_resp = await client.get("/api/v1/reports")
        items = list_resp.json()["items"]
        assert all(r["id"] != report_id for r in items)

    async def test_cannot_see_other_company_audit_logs(self, client: AsyncClient):
        token_a = await self._make_user(client, "aud_a@test.com", "AudA")
        token_b = await self._make_user(client, "aud_b@test.com", "AudB")

        # A changes password (creates audit log)
        client.headers["Authorization"] = f"Bearer {token_a}"
        await client.post("/api/v1/auth/change-password", json={
            "current_password": "Password123",
            "new_password": "Newpassword456",
        })

        # B sees no audit logs from A
        client.headers["Authorization"] = f"Bearer {token_b}"
        resp = await client.get("/api/v1/audit-logs/")
        items = resp.json()["items"]
        assert len(items) == 0
