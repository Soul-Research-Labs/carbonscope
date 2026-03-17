"""Company & data upload service — business logic extracted from routes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Company, DataUpload, _utcnow
from api.services import ServiceError


async def get_company(db: AsyncSession, company_id: str) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id, Company.deleted_at.is_(None)))
    company = result.scalar_one_or_none()
    if company is None:
        raise ServiceError("Company not found", status_code=404)
    return company


async def update_company(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    updates: dict[str, Any],
) -> Company:
    company = await get_company(db, company_id)
    for key, value in updates.items():
        setattr(company, key, value)

    from api.services import audit
    await audit.record(
        db, user_id=user_id, company_id=company_id,
        action="update", resource_type="company", resource_id=company.id,
        detail=f"fields: {', '.join(updates.keys())}",
    )
    await db.commit()
    await db.refresh(company)
    return company


async def create_upload(
    db: AsyncSession, company_id: str, *, year: int, provided_data: dict, notes: str | None = None,
) -> DataUpload:
    upload = DataUpload(
        company_id=company_id,
        year=year,
        provided_data=provided_data,
        notes=notes,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    from api.services.webhooks import dispatch_event
    await dispatch_event(db, company_id, "data.uploaded", {
        "upload_id": upload.id, "year": upload.year,
    })
    return upload


async def list_uploads(
    db: AsyncSession,
    company_id: str,
    *,
    year: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DataUpload], int]:
    base = select(DataUpload).where(
        DataUpload.company_id == company_id,
        DataUpload.deleted_at.is_(None),
    )
    if year is not None:
        base = base.where(DataUpload.year == year)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(base.order_by(DataUpload.year.desc()).limit(limit).offset(offset))
    return result.scalars().all(), total


async def get_upload(db: AsyncSession, upload_id: str, company_id: str) -> DataUpload:
    result = await db.execute(
        select(DataUpload).where(
            DataUpload.id == upload_id,
            DataUpload.company_id == company_id,
            DataUpload.deleted_at.is_(None),
        )
    )
    upload = result.scalar_one_or_none()
    if upload is None:
        raise ServiceError("Data upload not found", status_code=404)
    return upload


async def update_upload(
    db: AsyncSession,
    upload_id: str,
    company_id: str,
    user_id: str,
    updates: dict[str, Any],
) -> DataUpload:
    upload = await get_upload(db, upload_id, company_id)
    for key, value in updates.items():
        setattr(upload, key, value)

    from api.services import audit
    await audit.record(
        db, user_id=user_id, company_id=company_id,
        action="update", resource_type="data_upload", resource_id=upload_id,
    )
    await db.commit()
    await db.refresh(upload)
    return upload


async def delete_upload(
    db: AsyncSession, upload_id: str, company_id: str, user_id: str,
) -> None:
    upload = await get_upload(db, upload_id, company_id)
    upload.deleted_at = _utcnow()
    from api.services import audit
    await audit.record(
        db, user_id=user_id, company_id=company_id,
        action="delete", resource_type="data_upload", resource_id=upload_id,
    )
    await db.commit()
