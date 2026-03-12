"""Tests for webhook routes — CRUD, toggle, deliveries."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_webhook(auth_client: AsyncClient, **kw) -> dict:
    resp = await auth_client.post("/api/v1/webhooks/", json={
        "url": kw.get("url", "https://example.com/hook"),
        "event_types": kw.get("event_types", ["report.created"]),
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
class TestWebhookCRUD:
    async def test_create_webhook(self, auth_client: AsyncClient):
        data = await _create_webhook(auth_client)
        assert data["url"] == "https://example.com/hook"
        assert data["event_types"] == ["report.created"]
        assert "secret" in data  # WebhookOut includes secret
        assert data["active"] is True

    async def test_create_webhook_multiple_events(self, auth_client: AsyncClient):
        data = await _create_webhook(auth_client, event_types=["report.created", "data.uploaded"])
        assert len(data["event_types"]) == 2

    async def test_create_webhook_empty_url(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/webhooks/", json={
            "url": "",
            "event_types": ["report.created"],
        })
        assert resp.status_code == 422

    async def test_create_webhook_empty_event_types(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/webhooks/", json={
            "url": "https://example.com/hook",
            "event_types": [],
        })
        assert resp.status_code == 422

    async def test_list_webhooks(self, auth_client: AsyncClient):
        await _create_webhook(auth_client)
        resp = await auth_client.get("/api/v1/webhooks/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Public view — no secret
        assert "secret" not in data[0]

    async def test_toggle_webhook_off(self, auth_client: AsyncClient):
        wh = await _create_webhook(auth_client)
        resp = await auth_client.patch(f"/api/v1/webhooks/{wh['id']}", json={"active": False})
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    async def test_toggle_webhook_on(self, auth_client: AsyncClient):
        wh = await _create_webhook(auth_client)
        await auth_client.patch(f"/api/v1/webhooks/{wh['id']}", json={"active": False})
        resp = await auth_client.patch(f"/api/v1/webhooks/{wh['id']}", json={"active": True})
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    async def test_toggle_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.patch("/api/v1/webhooks/nonexistent", json={"active": False})
        assert resp.status_code == 404

    async def test_delete_webhook(self, auth_client: AsyncClient):
        wh = await _create_webhook(auth_client)
        resp = await auth_client.delete(f"/api/v1/webhooks/{wh['id']}")
        assert resp.status_code == 204

    async def test_delete_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/v1/webhooks/nonexistent")
        assert resp.status_code == 404

    async def test_list_deliveries(self, auth_client: AsyncClient):
        wh = await _create_webhook(auth_client)
        resp = await auth_client.get(f"/api/v1/webhooks/{wh['id']}/deliveries")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_deliveries_pagination(self, auth_client: AsyncClient):
        wh = await _create_webhook(auth_client)
        resp = await auth_client.get(
            f"/api/v1/webhooks/{wh['id']}/deliveries",
            params={"limit": 5, "offset": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["limit"] == 5


@pytest.mark.asyncio
class TestWebhookAuth:
    async def test_unauthenticated_create(self, client: AsyncClient):
        resp = await client.post("/api/v1/webhooks/", json={
            "url": "https://example.com",
            "event_types": ["x"],
        })
        assert resp.status_code == 401

    async def test_unauthenticated_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/webhooks/")
        assert resp.status_code == 401
