"""Authentication utilities — JWT tokens, password hashing, refresh tokens, password reset."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from api.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Refresh token expiry
REFRESH_TOKEN_EXPIRE_DAYS = 30
# Password reset token expiry
RESET_TOKEN_EXPIRE_MINUTES = 15

# In-memory store for refresh tokens and password reset tokens
# In production, these should be stored in Redis or the database
_refresh_tokens: dict[str, dict] = {}  # token -> {"user_id", "company_id", "exp"}
_reset_tokens: dict[str, dict] = {}  # token -> {"user_id", "email", "exp"}


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
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, company_id: str) -> str:
    """Create a refresh token for token rotation."""
    token = secrets.token_urlsafe(48)
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    _refresh_tokens[token] = {
        "user_id": user_id,
        "company_id": company_id,
        "exp": exp,
    }
    return token


def validate_refresh_token(token: str) -> dict | None:
    """Validate and consume a refresh token (rotation — single use)."""
    data = _refresh_tokens.pop(token, None)
    if data is None:
        return None
    if datetime.now(timezone.utc) > data["exp"]:
        return None
    return data


def revoke_refresh_tokens(user_id: str) -> int:
    """Revoke all refresh tokens for a user. Returns count revoked."""
    to_remove = [k for k, v in _refresh_tokens.items() if v["user_id"] == user_id]
    for k in to_remove:
        del _refresh_tokens[k]
    return len(to_remove)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Password reset ──────────────────────────────────────────────────


def create_reset_token(user_id: str, email: str) -> str:
    """Create a short-lived password reset token."""
    token = secrets.token_urlsafe(32)
    exp = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    _reset_tokens[token] = {"user_id": user_id, "email": email, "exp": exp}
    return token


def validate_reset_token(token: str) -> dict | None:
    """Validate and consume a password reset token (single use)."""
    data = _reset_tokens.pop(token, None)
    if data is None:
        return None
    if datetime.now(timezone.utc) > data["exp"]:
        return None
    return data


# ── DB lookup ───────────────────────────────────────────────────────


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
