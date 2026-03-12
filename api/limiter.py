"""Shared rate limiter instance — importable without circular dependencies."""

from __future__ import annotations

from starlette.requests import Request
from slowapi import Limiter

from api.config import RATE_LIMIT_DEFAULT


def _get_real_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the chain is the real client
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


limiter = Limiter(key_func=_get_real_ip, default_limits=[RATE_LIMIT_DEFAULT])
