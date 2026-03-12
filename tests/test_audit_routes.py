"""Tests for audit log routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_report(auth_client: AsyncClient) -> str:
    upload = await auth_client.post("/api/v1/data", json={
        "year": 2024,
        "provided_data": {"electricity_kwh": 100000, "natural_gas_therms": 5000},
    })
    upload_id = upload.json()["id"]
    est = await auth_client.post("/api/v1/estimate", json={"data_upload_id": upload_id})
    return est.json()["id"]


@pytest.mark.asyncio
class TestAuditLogs:
    async def test_list_audit_logs_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_audit_logs_after_action(self, auth_client: AsyncClient):
        # PATCH /reports creates an audit entry
        report_id = await _create_report(auth_client)
        await auth_client.patch(f"/api/v1/reports/{report_id}", json={"year": 2023})
        resp = await auth_client.get("/api/v1/audit-logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_pagination_limit(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/audit-logs/", params={"limit": 5, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    async def test_pagination_offset(self, auth_client: AsyncClient):
        # Generate multiple audit entries via PATCH
        report_id = await _create_report(auth_client)
        await auth_client.patch(f"/api/v1/reports/{report_id}", json={"year": 2023})
        await auth_client.patch(f"/api/v1/reports/{report_id}", json={"year": 2022})
        resp = await auth_client.get("/api/v1/audit-logs/", params={"limit": 1, "offset": 0})
        assert resp.status_code == 200
        first_page = resp.json()["items"]

        resp2 = await auth_client.get("/api/v1/audit-logs/", params={"limit": 1, "offset": 1})
        assert resp2.status_code == 200
        second_page = resp2.json()["items"]

        if first_page and second_page:
            assert first_page[0]["id"] != second_page[0]["id"]

    async def test_invalid_limit(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/audit-logs/", params={"limit": 0})
        assert resp.status_code == 422

    async def test_invalid_limit_too_large(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/audit-logs/", params={"limit": 999})
        assert resp.status_code == 422

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit-logs/")
        assert resp.status_code == 401
