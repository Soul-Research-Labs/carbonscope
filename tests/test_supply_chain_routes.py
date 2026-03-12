"""Tests for supply chain routes — links, suppliers, buyers, scope 3."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_supplier_link(auth_client: AsyncClient, supplier_id: str = "supplier_co_1", **kw) -> dict:
    resp = await auth_client.post("/api/v1/supply-chain/links", json={
        "supplier_company_id": supplier_id,
        "spend_usd": kw.get("spend_usd", 50000.0),
        "category": kw.get("category", "purchased_goods"),
        "notes": kw.get("notes"),
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
class TestSupplyChainLinks:
    async def test_create_link(self, auth_client: AsyncClient):
        data = await _create_supplier_link(auth_client)
        assert data["supplier_company_id"] == "supplier_co_1"
        assert data["category"] == "purchased_goods"
        assert data["status"] == "pending"

    async def test_create_link_self_reference_rejected(self, auth_client: AsyncClient):
        me = await auth_client.get("/api/v1/company")
        my_id = me.json()["id"]
        resp = await auth_client.post("/api/v1/supply-chain/links", json={
            "supplier_company_id": my_id,
        })
        assert resp.status_code == 400

    async def test_create_duplicate_link_rejected(self, auth_client: AsyncClient):
        await _create_supplier_link(auth_client, "dup_co")
        resp = await auth_client.post("/api/v1/supply-chain/links", json={
            "supplier_company_id": "dup_co",
        })
        assert resp.status_code == 400

    async def test_list_suppliers(self, auth_client: AsyncClient):
        await _create_supplier_link(auth_client, "sup_a")
        await _create_supplier_link(auth_client, "sup_b")
        resp = await auth_client.get("/api/v1/supply-chain/suppliers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    async def test_list_suppliers_pagination(self, auth_client: AsyncClient):
        # Note: list_suppliers JOINs on Company — supplier_company_id must reference
        # a real Company row for items to appear. Total counts links regardless.
        for i in range(3):
            await _create_supplier_link(auth_client, f"pag_{i}")
        resp = await auth_client.get("/api/v1/supply-chain/suppliers", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        # total counts SupplyChainLink rows; items only include those with a matching Company
        assert data["total"] == 3
        assert isinstance(data["items"], list)

    async def test_list_buyers(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/supply-chain/buyers")
        assert resp.status_code == 200
        assert "items" in resp.json()

    async def test_update_link_status(self, auth_client: AsyncClient):
        link = await _create_supplier_link(auth_client, "upd_co")
        resp = await auth_client.patch(f"/api/v1/supply-chain/links/{link['id']}", json={
            "status": "verified",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"

    async def test_update_link_invalid_status(self, auth_client: AsyncClient):
        link = await _create_supplier_link(auth_client, "inv_co")
        resp = await auth_client.patch(f"/api/v1/supply-chain/links/{link['id']}", json={
            "status": "invalid_value",
        })
        assert resp.status_code == 422

    async def test_delete_link(self, auth_client: AsyncClient):
        link = await _create_supplier_link(auth_client, "del_co")
        resp = await auth_client.delete(f"/api/v1/supply-chain/links/{link['id']}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_link(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/v1/supply-chain/links/nonexistent")
        assert resp.status_code == 404

    async def test_scope3_from_suppliers(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/supply-chain/scope3-from-suppliers")
        assert resp.status_code == 200

    async def test_scope3_with_year_filter(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/supply-chain/scope3-from-suppliers", params={"year": 2024})
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestSupplyChainAuth:
    async def test_unauthenticated_create(self, client: AsyncClient):
        resp = await client.post("/api/v1/supply-chain/links", json={
            "supplier_company_id": "x",
        })
        assert resp.status_code == 401

    async def test_unauthenticated_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/supply-chain/suppliers")
        assert resp.status_code == 401
