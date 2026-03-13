"""Shared rate limiter instance — importable without circular dependencies."""

from __future__ import annotations

import os

from starlette.requests import Request
from slowapi import Limiter

from api.config import RATE_LIMIT_DEFAULT, TRUST_PROXY


def _get_real_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For only when behind a trusted proxy."""
    if TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


# Use Redis for rate limit storage when REDIS_URL is set (shared across replicas).
# Falls back to in-memory storage for local development.
_redis_url = os.getenv("REDIS_URL")
_storage_uri = _redis_url if _redis_url else "memory://"

limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=_storage_uri,
)
