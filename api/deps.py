"""FastAPI dependencies — current user extraction, plan gates, DB sessions."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import decode_access_token
from api.database import get_db
from api.models import User

_bearer = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Bearer token."""
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_plan(feature: str) -> Callable:
    """Dependency factory that gates an endpoint behind a plan feature.

    Usage: Depends(require_plan("pdf_export"))
    """

    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        from api.services.subscriptions import check_feature_access

        if not await check_feature_access(db, user.company_id, feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' requires a Pro or Enterprise plan. Upgrade at /billing/subscription",
            )
        return user

    return _check


def require_credits(operation: str) -> Callable:
    """Dependency factory that checks and deducts credits for an operation.

    Usage: Depends(require_credits("estimate"))
    """

    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        from api.services.subscriptions import check_credit_and_deduct

        try:
            await check_credit_and_deduct(db, user.company_id, operation)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e),
            )
        return user

    return _check


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that ensures the current user has admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
