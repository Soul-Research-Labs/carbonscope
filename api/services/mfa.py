"""MFA (TOTP) service — setup, verification, and backup codes."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
import time


def generate_totp_secret(length: int = 20) -> str:
    """Generate a random base32-encoded TOTP secret."""
    import base64
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate human-readable backup codes (8-char hex)."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def hash_backup_code(code: str) -> str:
    """SHA-256 hash a backup code for storage."""
    return hashlib.sha256(code.upper().encode()).hexdigest()


def build_provisioning_uri(secret: str, email: str, issuer: str = "CarbonScope") -> str:
    """Build an otpauth:// URI for authenticator app scanning."""
    import urllib.parse
    label = urllib.parse.quote(f"{issuer}:{email}", safe=":")
    params = urllib.parse.urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": "6",
        "period": "30",
    })
    return f"otpauth://totp/{label}?{params}"


def _hotp(secret_b32: str, counter: int) -> str:
    """Compute HOTP(secret, counter) → 6-digit string (RFC 4226)."""
    import base64
    # Pad the base32 secret
    padded = secret_b32.upper() + "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(padded)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % 10**6).zfill(6)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code within ±window time steps (default ±30s)."""
    current_step = int(time.time()) // 30
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_hotp(secret, current_step + offset), code):
            return True
    return False


def generate_totp_code(secret: str) -> str:
    """Generate the current valid TOTP code for a secret (useful for testing)."""
    current_step = int(time.time()) // 30
    return _hotp(secret, current_step)
