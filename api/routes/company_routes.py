"""Company & data upload routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import RATE_LIMIT_DEFAULT
from api.database import get_db
from api.deps import get_current_user, require_admin
from api.limiter import limiter
from api.models import User
from api.schemas import (
    CompanyOut,
    CompanyUpdate,
    DataUploadCreate,
    DataUploadOut,
    DataUploadUpdate,
    PaginatedResponse,
)
from api.services import ServiceError
from api.services import company as company_svc

router = APIRouter(tags=["company"])


# ── Company profile ─────────────────────────────────────────────────


@router.get("/company", response_model=CompanyOut)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_company(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's company profile."""
    try:
        return await company_svc.get_company(db, user.company_id)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/company", response_model=CompanyOut)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def update_company(
    request: Request,
    body: CompanyUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update company profile fields."""
    try:
        return await company_svc.update_company(
            db, user.company_id, user.id,
            body.model_dump(exclude_unset=True),
        )
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ── Data uploads ────────────────────────────────────────────────────


@router.post("/data", response_model=DataUploadOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def upload_data(
    request: Request,
    body: DataUploadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload operational data for a given reporting year."""
    return await company_svc.create_upload(
        db, user.company_id, year=body.year,
        provided_data=body.provided_data, notes=body.notes,
    )


@router.get("/data", response_model=PaginatedResponse[DataUploadOut])
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_data_uploads(
    request: Request,
    year: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List data uploads with pagination and optional year filter."""
    items, total = await company_svc.list_uploads(
        db, user.company_id, year=year, limit=limit, offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/data/{upload_id}", response_model=DataUploadOut)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_data_upload(
    request: Request,
    upload_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific data upload."""
    try:
        return await company_svc.get_upload(db, upload_id, user.company_id)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/data/{upload_id}", response_model=DataUploadOut)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def update_data_upload(
    request: Request,
    upload_id: str,
    body: DataUploadUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a data upload's fields."""
    try:
        return await company_svc.update_upload(
            db, upload_id, user.company_id, user.id,
            body.model_dump(exclude_unset=True),
        )
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/data/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def delete_data_upload(
    request: Request,
    upload_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a data upload."""
    try:
        await company_svc.delete_upload(db, upload_id, user.company_id, user.id)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
