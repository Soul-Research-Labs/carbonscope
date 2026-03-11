"""Auth routes — registration, login, refresh tokens, password reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    hash_password,
    validate_refresh_token,
    validate_reset_token,
    verify_password,
)
from api.config import RATE_LIMIT_AUTH
from api.database import get_db
from api.deps import get_current_user
from api.limiter import limiter
from api.models import Company, User
from api.schemas import PasswordChange, Token, UserLogin, UserOut, UserProfileUpdate, UserRegister
from api.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(request: Request, body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user and company."""
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    company = Company(
        name=body.company_name,
        industry=body.industry,
        region=body.region,
    )
    db.add(company)
    await db.flush()  # get company.id

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        company_id=company.id,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenWithRefresh)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and return JWT access + refresh tokens."""
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access = create_access_token(user.id, user.company_id)
    refresh = create_refresh_token(user.id, user.company_id)
    return TokenWithRefresh(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserOut)
async def get_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return user


@router.patch("/me", response_model=UserOut)
async def update_profile(
    body: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile (name, email)."""
    updates = body.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != user.email:
        existing = await db.execute(select(User).where(User.email == updates["email"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    for key, value in updates.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.hashed_password = hash_password(body.new_password)
    await audit.record(
        db, user_id=user.id, company_id=user.company_id,
        action="change_password", resource_type="user", resource_id=user.id,
    )
    await db.commit()


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token(body: RefreshRequest):
    """Exchange a refresh token for a new access + refresh token pair (rotation)."""
    data = validate_refresh_token(body.refresh_token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    access = create_access_token(data["user_id"], data["company_id"])
    refresh = create_refresh_token(data["user_id"], data["company_id"])
    return TokenWithRefresh(access_token=access, refresh_token=refresh)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RATE_LIMIT_AUTH)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset. Sends a reset token via email."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is not None:
        token = create_reset_token(user.id, user.email)
        from api.services.email_async import send_password_reset_email
        await send_password_reset_email(user.email, token)
    # Always return 204 to prevent email enumeration


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RATE_LIMIT_AUTH)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a valid reset token."""
    data = validate_reset_token(body.token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    result = await db.execute(select(User).where(User.id == data["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
