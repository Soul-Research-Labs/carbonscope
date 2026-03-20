"""Tests for team management routes — invite, accept, list, role update, remove."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient) -> AsyncClient:
    """Authenticated admin client."""
    await client.post("/api/v1/auth/register", json={
        "email": "admin@team.io",
        "password": "StrongPass1!",
        "full_name": "Admin User",
        "company_name": "TeamCorp",
        "industry": "technology",
        "region": "US",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@team.io",
        "password": "StrongPass1!",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestInviteMember:
    async def test_invite_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/team/invite", json={"email": "new@team.io"})
        assert resp.status_code == 401

    async def test_invite_success(self, admin_client: AsyncClient):
        resp = await admin_client.post("/api/v1/team/invite", json={
            "email": "new@team.io",
            "role": "member",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@team.io"
        assert data["role"] == "member"
        assert data["accepted_at"] is None

    async def test_invite_duplicate_email(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/team/invite", json={"email": "dup@team.io", "role": "member"})
        resp = await admin_client.post("/api/v1/team/invite", json={"email": "dup@team.io", "role": "member"})
        assert resp.status_code == 409

    async def test_invite_existing_member(self, admin_client: AsyncClient):
        """Inviting someone who's already a company member returns 409."""
        resp = await admin_client.post("/api/v1/team/invite", json={
            "email": "admin@team.io",
            "role": "member",
        })
        assert resp.status_code == 409


class TestListMembers:
    async def test_list_members(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/team/members")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(m["email"] == "admin@team.io" for m in data["items"])


class TestListInvitations:
    async def test_list_invitations_empty(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/team/invitations")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_list_invitations_after_invite(self, admin_client: AsyncClient):
        await admin_client.post("/api/v1/team/invite", json={"email": "inv@team.io", "role": "member"})
        resp = await admin_client.get("/api/v1/team/invitations")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestUpdateRole:
    async def test_cannot_change_own_role(self, admin_client: AsyncClient):
        # Get own user id
        members = (await admin_client.get("/api/v1/team/members")).json()["items"]
        own_id = members[0]["id"]
        resp = await admin_client.patch(f"/api/v1/team/members/{own_id}/role?role=member")
        assert resp.status_code == 400


class TestRemoveMember:
    async def test_cannot_remove_self(self, admin_client: AsyncClient):
        members = (await admin_client.get("/api/v1/team/members")).json()["items"]
        own_id = members[0]["id"]
        resp = await admin_client.delete(f"/api/v1/team/members/{own_id}")
        assert resp.status_code == 400

    async def test_remove_nonexistent(self, admin_client: AsyncClient):
        resp = await admin_client.delete("/api/v1/team/members/nonexistent-uuid")
        assert resp.status_code == 404
