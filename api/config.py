"""Application configuration — loaded from environment variables."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ───────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Database ────────────────────────────────────────────────────────

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'carbonscope.db'}",
)

# ── Auth ────────────────────────────────────────────────────────────

_DEFAULT_SECRET = "change-me-in-production"
SECRET_KEY: str = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
if SECRET_KEY == _DEFAULT_SECRET:
    logger.warning(
        "SECRET_KEY is using the default value. Set SECRET_KEY env var in production!"
    )
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ── CORS ────────────────────────────────────────────────────────────

ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

# ── Rate Limiting ───────────────────────────────────────────────────

RATE_LIMIT_AUTH: str = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")

# ── Logging ─────────────────────────────────────────────────────────

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# ── Bittensor ───────────────────────────────────────────────────────

BT_NETWORK: str = os.getenv("BT_NETWORK", "test")
BT_NETUID: int = int(os.getenv("BT_NETUID", "1"))
BT_WALLET_NAME: str = os.getenv("BT_WALLET_NAME", "api_client")
BT_WALLET_HOTKEY: str = os.getenv("BT_WALLET_HOTKEY", "default")
BT_QUERY_TIMEOUT: float = float(os.getenv("BT_QUERY_TIMEOUT", "30.0"))
