"""Tests for middleware — RequestID, SecurityHeaders, global exception handler."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRequestIDMiddleware:
    async def test_response_has_request_id(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    async def test_custom_request_id_echoed(self, client: AsyncClient):
        custom_id = "my-custom-request-id-123"
        resp = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["x-request-id"] == custom_id

    async def test_generated_request_id_is_unique(self, client: AsyncClient):
        r1 = await client.get("/api/v1/health")
        r2 = await client.get("/api/v1/health")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


@pytest.mark.asyncio
class TestSecurityHeadersMiddleware:
    async def test_content_type_options(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_frame_options(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    async def test_xss_protection(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("x-xss-protection") == "1; mode=block"

    async def test_referrer_policy(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert "permissions-policy" in resp.headers


@pytest.mark.asyncio
class TestCarbonReportCRUD:
    """Test PATCH endpoint added in Phase 2 Stream G."""

    async def _create_report(self, auth_client: AsyncClient) -> str:
        upload = await auth_client.post("/api/v1/data", json={
            "year": 2024,
            "provided_data": {"electricity_kwh": 100000, "natural_gas_therms": 5000},
        })
        upload_id = upload.json()["id"]
        est = await auth_client.post("/api/v1/estimate", json={"data_upload_id": upload_id})
        return est.json()["id"]

    async def test_patch_report_year(self, auth_client: AsyncClient):
        report_id = await self._create_report(auth_client)
        resp = await auth_client.patch(f"/api/v1/reports/{report_id}", json={"year": 2023})
        assert resp.status_code == 200
        assert resp.json()["year"] == 2023

    async def test_patch_report_notes(self, auth_client: AsyncClient):
        report_id = await self._create_report(auth_client)
        resp = await auth_client.patch(f"/api/v1/reports/{report_id}", json={"notes": "Test note"})
        assert resp.status_code == 200

    async def test_patch_report_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.patch("/api/v1/reports/nonexistent", json={"year": 2023})
        assert resp.status_code == 404

    async def test_patch_report_empty_body(self, auth_client: AsyncClient):
        report_id = await self._create_report(auth_client)
        resp = await auth_client.patch(f"/api/v1/reports/{report_id}", json={})
        assert resp.status_code == 200
