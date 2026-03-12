"""Tests for AI routes — parse-text, predict, audit-trail, recommendations."""

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
class TestParseText:
    async def test_parse_text(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/parse-text", json={
            "text": "Our factory used 50000 kWh of electricity and 1000 therms of gas in 2024",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "extracted_data" in data
        assert isinstance(data["extracted_data"], dict)

    async def test_parse_text_empty(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/parse-text", json={"text": ""})
        assert resp.status_code == 422

    async def test_parse_text_too_long(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/parse-text", json={"text": "x" * 10001})
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestPredict:
    async def test_predict(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/predict", json={
            "known_data": {"electricity_kwh": 100000},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "predictions" in data
        assert "method" in data

    async def test_predict_with_industry(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/predict", json={
            "known_data": {"electricity_kwh": 100000},
            "industry": "manufacturing",
            "region": "US",
        })
        assert resp.status_code == 200

    async def test_predict_empty_data(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/predict", json={
            "known_data": {},
        })
        # Empty dict is still valid — service handles it
        assert resp.status_code in (200, 400)


@pytest.mark.asyncio
class TestAuditTrail:
    async def test_audit_trail(self, auth_client: AsyncClient):
        report_id = await _create_report(auth_client)
        resp = await auth_client.post("/api/v1/ai/audit-trail", json={
            "report_id": report_id,
        })
        assert resp.status_code == 200
        assert "audit_trail" in resp.json()

    async def test_audit_trail_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai/audit-trail", json={
            "report_id": "nonexistent",
        })
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestRecommendations:
    async def test_get_recommendations(self, auth_client: AsyncClient):
        report_id = await _create_report(auth_client)
        resp = await auth_client.get(f"/api/v1/ai/recommendations/{report_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert "summary" in data

    async def test_get_recommendations_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/ai/recommendations/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestAIAuth:
    async def test_unauthenticated_parse(self, client: AsyncClient):
        resp = await client.post("/api/v1/ai/parse-text", json={"text": "test"})
        assert resp.status_code == 401

    async def test_unauthenticated_predict(self, client: AsyncClient):
        resp = await client.post("/api/v1/ai/predict", json={"known_data": {}})
        assert resp.status_code == 401

    async def test_unauthenticated_recommendations(self, client: AsyncClient):
        resp = await client.get("/api/v1/ai/recommendations/some_id")
        assert resp.status_code == 401
