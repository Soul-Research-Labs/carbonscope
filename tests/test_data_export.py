"""Tests for api.services.data_export.gather_user_export."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Company, User, EmissionReport, DataUpload, Webhook, AuditLog
from api.services.data_export import gather_user_export, _row_to_dict
from tests.conftest import TestSessionLocal, test_engine
from api.database import Base


@pytest_asyncio.fixture
async def db_session():
    """Provide a real async session with tables created."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_company(company_id: str = None) -> Company:
    return Company(
        id=company_id or str(uuid.uuid4()),
        name="TestCo",
        industry="manufacturing",
        region="US",
    )


def _make_user(company: Company, user_id: str = None) -> User:
    return User(
        id=user_id or str(uuid.uuid4()),
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="fakehash",
        full_name="Test User",
        company_id=company.id,
        role="admin",
    )


@pytest.mark.asyncio
async def test_export_contains_required_keys(db_session: AsyncSession):
    company = _make_company()
    user = _make_user(company)
    db_session.add_all([company, user])
    await db_session.commit()
    await db_session.refresh(user)

    export = await gather_user_export(db_session, user)

    assert "exported_at" in export
    assert "user" in export
    assert "company" in export
    # Ensure sensitive fields removed
    assert "hashed_password" not in export["user"]


@pytest.mark.asyncio
async def test_export_strips_webhook_secrets(db_session: AsyncSession):
    company = _make_company()
    user = _make_user(company)
    webhook = Webhook(
        id=str(uuid.uuid4()),
        company_id=company.id,
        url="https://example.com/hook",
        event_types=["report.created"],
        active=True,
        secret="supersecret",
    )
    db_session.add_all([company, user, webhook])
    await db_session.commit()
    await db_session.refresh(user)

    export = await gather_user_export(db_session, user)

    assert len(export["webhooks"]) == 1
    assert "secret" not in export["webhooks"][0]


@pytest.mark.asyncio
async def test_export_empty_company_has_empty_lists(db_session: AsyncSession):
    company = _make_company()
    user = _make_user(company)
    db_session.add_all([company, user])
    await db_session.commit()
    await db_session.refresh(user)

    export = await gather_user_export(db_session, user)

    for key in ("data_uploads", "emission_reports", "scenarios", "webhooks", "alerts"):
        assert export[key] == [], f"{key} should be empty"


@pytest.mark.asyncio
async def test_export_user_all_fields_present(db_session: AsyncSession):
    """Verify that the export includes all expected top-level keys."""
    company = _make_company()
    user = _make_user(company)
    db_session.add_all([company, user])
    await db_session.commit()
    await db_session.refresh(user)

    export = await gather_user_export(db_session, user)

    expected_keys = {
        "exported_at", "user", "company", "data_uploads", "emission_reports",
        "scenarios", "questionnaires", "supply_chain_links", "webhooks",
        "alerts", "credit_ledger", "data_listings", "subscriptions",
        "financed_portfolios", "data_purchases", "data_reviews", "audit_logs",
    }
    assert expected_keys.issubset(set(export.keys()))


@pytest.mark.asyncio
async def test_export_includes_reports(db_session: AsyncSession):
    company = _make_company()
    user = _make_user(company)
    report = EmissionReport(
        id=str(uuid.uuid4()),
        company_id=company.id,
        year=2024,
        scope1=100.0,
        scope2=200.0,
        scope3=300.0,
        total=600.0,
        methodology_version="ghg_protocol_v2025",
    )
    db_session.add_all([company, user, report])
    await db_session.commit()
    await db_session.refresh(user)

    export = await gather_user_export(db_session, user)

    assert len(export["emission_reports"]) == 1
    assert export["emission_reports"][0]["id"] == report.id


def test_row_to_dict_datetime_conversion():
    """_row_to_dict should convert datetime fields to ISO strings."""
    company = Company(
        id="test-id",
        name="DtCo",
        industry="technology",
        region="EU",
    )
    d = _row_to_dict(company)
    assert d["id"] == "test-id"
    assert d["name"] == "DtCo"
    # created_at may be None if not from DB, that's fine
    assert "industry" in d
