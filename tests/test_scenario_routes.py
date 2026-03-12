"""Tests for scenario routes — CRUD, compute, PATCH."""

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


async def _create_scenario(auth_client: AsyncClient, report_id: str | None = None, **kw) -> dict:
    if report_id is None:
        report_id = await _create_report(auth_client)
    payload = {
        "name": kw.get("name", "Test Scenario"),
        "description": kw.get("description", "A test scenario"),
        "base_report_id": report_id,
        "parameters": kw.get("parameters", {"electricity_kwh": 50000}),
    }
    resp = await auth_client.post("/api/v1/scenarios/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
class TestScenarioCRUD:
    async def test_create_scenario_with_report(self, auth_client: AsyncClient):
        report_id = await _create_report(auth_client)
        data = await _create_scenario(auth_client, report_id=report_id)
        assert data["name"] == "Test Scenario"
        assert data["base_report_id"] == report_id
        assert data["status"] == "draft"

    async def test_create_scenario_requires_report(self, auth_client: AsyncClient):
        """base_report_id is required — passing None yields 404."""
        resp = await auth_client.post("/api/v1/scenarios/", json={
            "name": "No Report",
            "parameters": {"electricity_kwh": 50000},
        })
        assert resp.status_code == 404

    async def test_create_scenario_invalid_report(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/scenarios/", json={
            "name": "Bad",
            "base_report_id": "nonexistent",
            "parameters": {"x": 1},
        })
        assert resp.status_code == 404

    async def test_list_scenarios(self, auth_client: AsyncClient):
        await _create_scenario(auth_client, name="S1")
        await _create_scenario(auth_client, name="S2")
        resp = await auth_client.get("/api/v1/scenarios/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    async def test_list_scenarios_pagination(self, auth_client: AsyncClient):
        for i in range(3):
            await _create_scenario(auth_client, name=f"Pag{i}")
        resp = await auth_client.get("/api/v1/scenarios/", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    async def test_get_scenario(self, auth_client: AsyncClient):
        s = await _create_scenario(auth_client)
        resp = await auth_client.get(f"/api/v1/scenarios/{s['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == s["id"]

    async def test_get_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/scenarios/nonexistent")
        assert resp.status_code == 404

    async def test_patch_name(self, auth_client: AsyncClient):
        s = await _create_scenario(auth_client)
        resp = await auth_client.patch(f"/api/v1/scenarios/{s['id']}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    async def test_patch_description(self, auth_client: AsyncClient):
        s = await _create_scenario(auth_client)
        resp = await auth_client.patch(f"/api/v1/scenarios/{s['id']}", json={"description": "New desc"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "New desc"

    async def test_patch_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.patch("/api/v1/scenarios/nonexistent", json={"name": "X"})
        assert resp.status_code == 404

    async def test_patch_empty_name_rejected(self, auth_client: AsyncClient):
        s = await _create_scenario(auth_client)
        resp = await auth_client.patch(f"/api/v1/scenarios/{s['id']}", json={"name": ""})
        assert resp.status_code == 422

    async def test_delete_scenario(self, auth_client: AsyncClient):
        s = await _create_scenario(auth_client)
        resp = await auth_client.delete(f"/api/v1/scenarios/{s['id']}")
        assert resp.status_code == 204
        # Verify gone
        resp2 = await auth_client.get(f"/api/v1/scenarios/{s['id']}")
        assert resp2.status_code == 404

    async def test_delete_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/v1/scenarios/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestScenarioCompute:
    async def test_compute(self, auth_client: AsyncClient):
        report_id = await _create_report(auth_client)
        s = await _create_scenario(auth_client, report_id=report_id)
        resp = await auth_client.post(f"/api/v1/scenarios/{s['id']}/compute")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "computed"
        assert data["results"] is not None

    async def test_compute_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/scenarios/nonexistent/compute")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestScenarioAuth:
    async def test_unauthenticated_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/scenarios/")
        assert resp.status_code == 401

    async def test_unauthenticated_create(self, client: AsyncClient):
        resp = await client.post("/api/v1/scenarios/", json={
            "name": "X",
            "parameters": {},
        })
        assert resp.status_code == 401
