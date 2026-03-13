"""Review service — business logic for data review workflows."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import DataReview, EmissionReport, ReviewStatus


class ReviewError(Exception):
    """Domain error raised by review operations."""

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


async def create_review(db: AsyncSession, report_id: str, company_id: str) -> DataReview:
    """Create a review record for an emission report (starts in 'draft').

    Raises ReviewError if the report doesn't exist or a review already exists.
    """
    result = await db.execute(
        select(EmissionReport).where(
            EmissionReport.id == report_id,
            EmissionReport.company_id == company_id,
            EmissionReport.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise ReviewError("Report not found", status_code=404)

    existing = await db.execute(
        select(DataReview).where(DataReview.report_id == report_id)
    )
    if existing.scalar_one_or_none():
        raise ReviewError("Review already exists for this report", status_code=409)

    review = DataReview(
        report_id=report_id,
        company_id=company_id,
        status=ReviewStatus.draft,
    )
    db.add(review)
    await db.flush()
    return review


async def list_reviews(
    db: AsyncSession,
    company_id: str,
    *,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DataReview], int]:
    """Return (reviews, total_count) for a company, optionally filtered by status."""
    base = select(DataReview).where(DataReview.company_id == company_id)
    if status_filter:
        base = base.where(DataReview.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(DataReview.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    return rows, total


async def get_review(db: AsyncSession, review_id: str, company_id: str) -> DataReview:
    """Fetch a single review owned by company_id. Raises ReviewError if not found."""
    result = await db.execute(
        select(DataReview).where(
            DataReview.id == review_id,
            DataReview.company_id == company_id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise ReviewError("Review not found", status_code=404)
    return review


async def perform_action(
    db: AsyncSession,
    review: DataReview,
    action: str,
    user_id: str,
    user_role: str,
    notes: str | None = None,
) -> DataReview:
    """Execute a review state transition (submit / approve / reject).

    Raises ReviewError on invalid transitions or insufficient permissions.
    """
    now = datetime.now(timezone.utc)

    if action == "submit":
        if review.status not in (ReviewStatus.draft, ReviewStatus.rejected):
            raise ReviewError("Can only submit from draft or rejected status")
        review.status = ReviewStatus.submitted
        review.submitted_by = user_id
        review.submitted_at = now
        review.reviewed_by = None
        review.reviewed_at = None
        review.review_notes = None

    elif action == "approve":
        if user_role != "admin":
            raise ReviewError("Only admins can approve reviews", status_code=403)
        if review.status not in (ReviewStatus.submitted, ReviewStatus.in_review):
            raise ReviewError("Can only approve submitted or in-review items")
        review.status = ReviewStatus.approved
        review.reviewed_by = user_id
        review.reviewed_at = now
        review.review_notes = notes

    elif action == "reject":
        if user_role != "admin":
            raise ReviewError("Only admins can reject reviews", status_code=403)
        if review.status not in (ReviewStatus.submitted, ReviewStatus.in_review):
            raise ReviewError("Can only reject submitted or in-review items")
        review.status = ReviewStatus.rejected
        review.reviewed_by = user_id
        review.reviewed_at = now
        review.review_notes = notes

    else:
        raise ReviewError(f"Unknown action: {action}")

    await db.flush()
    return review
