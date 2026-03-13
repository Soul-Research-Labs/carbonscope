"""Authentication utilities — JWT tokens, password hashing, persistent token storage."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from api.models import User, RefreshToken, RevokedToken, PasswordResetToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Refresh token expiry
REFRESH_TOKEN_EXPIRE_DAYS = 30
# Password reset token expiry
RESET_TOKEN_EXPIRE_MINUTES = 15

# Password reset tokens are now persisted in the database (PasswordResetToken model),
# following the same pattern as RefreshToken for consistency and multi-instance safety.


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for safe storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Password helpers ────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ─────────────────────────────────────────────────────


def create_access_token(user_id: str, company_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "exp": expire,
        "type": "access",
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Short-lived token issued when password is correct but MFA is still required.
MFA_PENDING_TOKEN_EXPIRE_MINUTES = 5


def create_mfa_pending_token(user_id: str, company_id: str) -> str:
    """Create a limited-scope token that can only be used to complete MFA verification."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=MFA_PENDING_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "exp": expire,
        "type": "mfa_pending",
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(db: AsyncSession, user_id: str, company_id: str) -> str:
    """Create a persistent refresh token stored in the database."""
    token = secrets.token_urlsafe(48)
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        expires_at=exp,
    ))
    await db.flush()
    return token


async def validate_refresh_token(db: AsyncSession, token: str) -> dict | None:
    """Validate and consume a refresh token (rotation — single use)."""
    hashed = _hash_token(token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hashed)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    # Make comparison tz-aware safe (SQLite returns naive datetimes)
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        await db.delete(row)
        await db.flush()
        return None
    data = {"user_id": row.user_id}
    # Look up company_id from user
    user_result = await db.execute(select(User.company_id).where(User.id == row.user_id))
    company_id = user_result.scalar_one_or_none()
    data["company_id"] = company_id or ""
    # Consume (single-use rotation)
    await db.delete(row)
    await db.flush()
    return data


async def revoke_refresh_tokens(db: AsyncSession, user_id: str) -> int:
    """Revoke all refresh tokens for a user. Returns count revoked."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    await db.flush()
    return result.rowcount


async def revoke_access_token(db: AsyncSession, jti: str, user_id: str, expires_at: datetime) -> None:
    """Add a JWT access token to the revocation list."""
    db.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))
    await db.flush()


async def is_token_revoked(db: AsyncSession, jti: str) -> bool:
    """Check if a JWT access token has been revoked."""
    result = await db.execute(select(RevokedToken.id).where(RevokedToken.jti == jti))
    return result.scalar_one_or_none() is not None


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Password reset ──────────────────────────────────────────────────


async def create_reset_token(db: AsyncSession, user_id: str, email: str) -> str:
    """Create a short-lived password reset token (persisted in DB)."""
    token = secrets.token_urlsafe(32)
    exp = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    db.add(PasswordResetToken(
        user_id=user_id,
        email=email,
        token_hash=_hash_token(token),
        expires_at=exp,
    ))
    await db.flush()
    return token


async def validate_reset_token(db: AsyncSession, token: str) -> dict | None:
    """Validate and consume a password reset token (single use)."""
    hashed = _hash_token(token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hashed)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        await db.delete(row)
        await db.flush()
        return None
    data = {"user_id": row.user_id, "email": row.email}
    # Consume (single-use)
    await db.delete(row)
    await db.flush()
    return data


# ── DB lookup ───────────────────────────────────────────────────────


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None.

    Rejects inactive or soft-deleted accounts.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active or user.deleted_at is not None:
        return None
    return user
