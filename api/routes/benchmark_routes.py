"""Industry benchmarking routes — compare company emissions against peers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import RATE_LIMIT_DEFAULT
from api.database import get_db
from api.deps import get_current_user
from api.limiter import limiter
from api.models import IndustryBenchmark, User
from api.schemas import BenchmarkComparison, BenchmarkOut, PaginatedResponse
from api.services.benchmarks import BenchmarkError, compare_to_industry as svc_compare

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("", response_model=PaginatedResponse[BenchmarkOut])
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_benchmarks(
    request: Request,
    industry: str | None = None,
    region: str | None = None,
    year: int | None = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available industry benchmarks, optionally filtered."""
    base = select(IndustryBenchmark)
    if industry:
        base = base.where(IndustryBenchmark.industry == industry)
    if region:
        base = base.where(IndustryBenchmark.region == region)
    if year:
        base = base.where(IndustryBenchmark.year == year)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    rows = (await db.execute(
        base.order_by(IndustryBenchmark.year.desc(), IndustryBenchmark.industry).offset(offset).limit(limit)
    )).scalars().all()
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/compare", response_model=BenchmarkComparison)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def compare_to_industry(
    request: Request,
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare a company's emission report against the industry benchmark."""
    try:
        return await svc_compare(db, report_id, user.company_id)
    except BenchmarkError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
