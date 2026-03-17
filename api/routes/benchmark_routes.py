"""Industry benchmarking routes — compare company emissions against peers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import RATE_LIMIT_DEFAULT
from api.database import get_db
from api.deps import get_current_user
from api.limiter import limiter
from api.models import User
from api.schemas import BenchmarkComparison, BenchmarkOut, PaginatedResponse
from api.services.benchmarks import BenchmarkError, compare_to_industry as svc_compare, list_benchmarks as svc_list

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("", response_model=PaginatedResponse[BenchmarkOut])
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_benchmarks(
    request: Request,
    industry: str | None = None,
    region: str | None = None,
    year: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available industry benchmarks, optionally filtered."""
    return await svc_list(db, industry=industry, region=region, year=year, limit=limit, offset=offset)


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
