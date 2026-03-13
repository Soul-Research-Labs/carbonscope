"""Unit tests for api/services/reviews.py — review business logic."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import DataReview, EmissionReport, ReviewStatus
from api.services.reviews import (
    ReviewError,
    create_review,
    get_review,
    list_reviews,
    perform_action,
)


# ── Helpers ──────────────────────────────────────────────────────────


async def _create_report(db: AsyncSession, company_id: str, year: int = 2025) -> EmissionReport:
    """Insert a minimal emission report for testing."""
    report = EmissionReport(
        company_id=company_id,
        year=year,
        scope1=100.0,
        scope2=200.0,
        scope3=300.0,
        total=600.0,
        confidence=0.8,
    )
    db.add(report)
    await db.flush()
    return report


async def _get_company_id(db: AsyncSession) -> str:
    from api.models import User

    result = await db.execute(select(User))
    user = result.scalars().first()
    return user.company_id


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_review_success(auth_client: AsyncClient):
    """Create a review for an existing report."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        report = await _create_report(db, cid)
        await db.commit()

        review = await create_review(db, report.id, cid)
        assert review.status == ReviewStatus.draft
        assert review.report_id == report.id
        await db.commit()


@pytest.mark.asyncio
async def test_create_review_report_not_found(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        with pytest.raises(ReviewError, match="Report not found"):
            await create_review(db, "nonexistent", cid)


@pytest.mark.asyncio
async def test_create_review_duplicate(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        report = await _create_report(db, cid)
        await db.commit()
        await create_review(db, report.id, cid)
        await db.commit()
        with pytest.raises(ReviewError, match="Review already exists"):
            await create_review(db, report.id, cid)


@pytest.mark.asyncio
async def test_list_reviews_empty(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        rows, total = await list_reviews(db, cid)
        assert total == 0
        assert rows == []


@pytest.mark.asyncio
async def test_list_reviews_with_filter(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        report = await _create_report(db, cid)
        await db.commit()
        await create_review(db, report.id, cid)
        await db.commit()

        rows, total = await list_reviews(db, cid, status_filter="draft")
        assert total == 1

        rows, total = await list_reviews(db, cid, status_filter="submitted")
        assert total == 0


@pytest.mark.asyncio
async def test_get_review_not_found(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        with pytest.raises(ReviewError, match="Review not found"):
            await get_review(db, "nonexistent", cid)


@pytest.mark.asyncio
async def test_perform_action_submit(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        from api.models import User

        user = (await db.execute(select(User))).scalars().first()
        report = await _create_report(db, cid)
        await db.commit()
        review = await create_review(db, report.id, cid)
        await db.commit()

        review = await perform_action(db, review, "submit", user.id, "member")
        assert review.status == ReviewStatus.submitted
        assert review.submitted_by == user.id


@pytest.mark.asyncio
async def test_perform_action_approve_requires_admin(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        from api.models import User

        user = (await db.execute(select(User))).scalars().first()
        report = await _create_report(db, cid)
        await db.commit()
        review = await create_review(db, report.id, cid)
        await db.commit()
        await perform_action(db, review, "submit", user.id, "member")
        await db.commit()

        with pytest.raises(ReviewError, match="Only admins can approve"):
            await perform_action(db, review, "approve", user.id, "member")


@pytest.mark.asyncio
async def test_perform_action_reject_from_submitted(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        from api.models import User

        user = (await db.execute(select(User))).scalars().first()
        report = await _create_report(db, cid)
        await db.commit()
        review = await create_review(db, report.id, cid)
        await db.commit()
        await perform_action(db, review, "submit", user.id, "member")
        await db.commit()

        review = await perform_action(db, review, "reject", user.id, "admin", notes="Needs revision")
        assert review.status == ReviewStatus.rejected
        assert review.review_notes == "Needs revision"


@pytest.mark.asyncio
async def test_perform_action_invalid_transition(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        cid = await _get_company_id(db)
        from api.models import User

        user = (await db.execute(select(User))).scalars().first()
        report = await _create_report(db, cid)
        await db.commit()
        review = await create_review(db, report.id, cid)
        await db.commit()

        # Can't approve from draft
        with pytest.raises(ReviewError):
            await perform_action(db, review, "approve", user.id, "admin")
