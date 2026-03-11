"""Subscription & billing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.deps import get_current_user
from api.models import User
from api.schemas import (
    CreditBalanceOut,
    CreditLedgerOut,
    PaginatedResponse,
    SubscriptionCreate,
    SubscriptionOut,
)
from api.services.subscriptions import (
    PLAN_LIMITS,
    change_plan,
    get_credit_balance,
    get_or_create_subscription,
    get_plan_limits,
    grant_credits,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current company subscription."""
    sub = await get_or_create_subscription(db, user.company_id)
    await db.commit()
    return sub


@router.post("/subscription", response_model=SubscriptionOut)
async def update_subscription(
    body: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the company's subscription plan."""
    try:
        old_sub = await get_or_create_subscription(db, user.company_id)
        old_plan = old_sub.plan
        sub = await change_plan(db, user.company_id, body.plan)
        await db.commit()
        await db.refresh(sub)

        # Send email notification for plan change
        if old_plan != body.plan:
            from api.services.email_async import send_subscription_change_email
            await send_subscription_change_email(user.email, old_plan, body.plan)

        return sub
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/credits", response_model=CreditBalanceOut)
async def get_credits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the company's current credit balance."""
    sub = await get_or_create_subscription(db, user.company_id)
    balance = await get_credit_balance(db, user.company_id)
    await db.commit()
    return CreditBalanceOut(
        company_id=user.company_id,
        balance=balance,
        plan=sub.plan,
    )


@router.get("/plans")
async def list_plans():
    """List available subscription plans and their limits."""
    return {
        plan: {k: v for k, v in limits.items()}
        for plan, limits in PLAN_LIMITS.items()
    }


@router.post("/credits/grant", response_model=CreditBalanceOut)
async def admin_grant_credits(
    amount: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant credits manually (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

    await grant_credits(db, user.company_id, amount, "manual_grant")
    balance = await get_credit_balance(db, user.company_id)
    sub = await get_or_create_subscription(db, user.company_id)
    await db.commit()
    return CreditBalanceOut(
        company_id=user.company_id,
        balance=balance,
        plan=sub.plan,
    )
