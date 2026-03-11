"""Shared rate limiter instance — importable without circular dependencies."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from api.config import RATE_LIMIT_DEFAULT

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])
