"""Audit log routes — list audit entries for the current company."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.deps import get_current_user, require_admin
from api.models import AuditLog, User
from api.schemas import AuditLogOut, PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/", response_model=PaginatedResponse[AuditLogOut])
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries for the current user's company."""
    base = select(AuditLog).where(AuditLog.company_id == user.company_id)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)
