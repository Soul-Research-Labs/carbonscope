"""Structured JSON logging for CarbonScope.

In production, emits JSON lines for structured log aggregation.
In development/test, uses a human-readable format.

Sensitive fields (email, password, token, secret, authorization) are
automatically redacted from log output via a custom filter.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone


# Patterns to redact in log messages
_SENSITIVE_PATTERNS = re.compile(
    r'("(?:[Pp]assword|[Ss]ecret|[Tt]oken|[Aa]uthorization|[Aa]pi_key|[Hh]ashed_password)":\s*)"[^"]*"'
    r'|'
    r'(?:[Pp]assword|[Ss]ecret|[Tt]oken|[Aa]pi_key)=\S+',
)

_EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)


def _redact(message: str) -> str:
    """Mask sensitive values in log messages."""
    message = _SENSITIVE_PATTERNS.sub(
        lambda m: m.group(1) + '"***"' if m.group(1) else m.group(0).split("=")[0] + "=***",
        message,
    )
    message = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", message)
    return message


class SensitiveFilter(logging.Filter):
    """Redact sensitive data from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            record.args = tuple(
                _redact(str(a)) if isinstance(a, str) else a for a in record.args
            ) if isinstance(record.args, tuple) else record.args
        return True


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include request_id if threaded through
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure root logger with optional JSON output and sensitive-data filter."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    handler = logging.StreamHandler()
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )

    handler.addFilter(SensitiveFilter())
    root.addHandler(handler)
