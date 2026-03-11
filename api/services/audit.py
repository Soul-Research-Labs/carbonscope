"""Audit logging helper — records sensitive operations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import AuditLog


async def record(
    db: AsyncSession,
    *,
    user_id: str,
    company_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
) -> None:
    """Write an audit log entry (non-blocking — piggybacks on the caller's commit)."""
    db.add(
        AuditLog(
            user_id=user_id,
            company_id=company_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
        )
    )
