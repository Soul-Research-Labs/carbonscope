"""Tests for Phase 27: Security hardening — TOTP encryption, cascade deletes, soft delete filtering."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    Alert,
    Company,
    CreditLedger,
    DataListing,
    DataListingStatus,
    DataListingType,
    MFASecret,
    User,
    Webhook,
)
from api.services.mfa import decrypt_secret, encrypt_secret, generate_totp_secret, verify_totp


# ── TOTP Encryption Round-trip ──────────────────────────────────────


class TestTOTPEncryption:
    """Verify Fernet encrypt/decrypt round-trip for TOTP secrets."""

    def test_encrypt_decrypt_round_trip(self):
        secret = generate_totp_secret()
        encrypted = encrypt_secret(secret)
        assert encrypted != secret, "Encrypted text should differ from plaintext"
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret

    def test_encrypted_secret_produces_valid_totp(self):
        secret = generate_totp_secret()
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        from api.services.mfa import generate_totp_code

        code = generate_totp_code(decrypted)
        assert verify_totp(decrypted, code)

    def test_different_secrets_produce_different_ciphertext(self):
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        assert encrypt_secret(s1) != encrypt_secret(s2)


# ── MFA Routes Use Encryption ──────────────────────────────────────


@pytest.mark.asyncio
async def test_mfa_setup_stores_encrypted_secret(auth_client: AsyncClient):
    """POST /auth/mfa/setup should store an encrypted (non-plaintext) TOTP secret."""
    resp = await auth_client.post("/api/v1/auth/mfa/setup")
    assert resp.status_code == 200
    data = resp.json()
    plaintext_secret = data["secret"]

    # The secret returned to the user is the raw base32 secret for QR scanning
    assert plaintext_secret
    # Verify it's a valid base32 string (no padding needed for TOTP)
    import base64

    base64.b32decode(plaintext_secret.upper() + "=" * (-len(plaintext_secret) % 8))

    # Verify the DB contains encrypted (not plaintext) TOTP secret
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(select(MFASecret))
        mfa = result.scalar_one_or_none()
        assert mfa is not None
        assert mfa.totp_secret != plaintext_secret, "DB should store encrypted secret, not plaintext"
        # Decrypt and verify
        assert decrypt_secret(mfa.totp_secret) == plaintext_secret


@pytest.mark.asyncio
async def test_mfa_verify_works_with_encrypted_secret(auth_client: AsyncClient):
    """POST /auth/mfa/verify should decrypt the stored secret and validate the TOTP code."""
    resp = await auth_client.post("/api/v1/auth/mfa/setup")
    assert resp.status_code == 200
    plaintext_secret = resp.json()["secret"]

    from api.services.mfa import generate_totp_code

    code = generate_totp_code(plaintext_secret)

    resp = await auth_client.post("/api/v1/auth/mfa/verify", json={"totp_code": code})
    assert resp.status_code == 200
    assert resp.json()["mfa_enabled"] is True


# ── User updated_at ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_has_updated_at_column(auth_client: AsyncClient):
    """User model should have an updated_at column."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(select(User))
        user = result.scalar_one()
        assert user.updated_at is not None
        assert user.created_at is not None


# ── Cascade Delete Behavior ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cascade_delete_company_removes_users(auth_client: AsyncClient):
    """Deleting a company should cascade delete its users (with FK enforcement)."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        # Enable SQLite foreign key enforcement for this session
        await db.execute(text("PRAGMA foreign_keys=ON"))

        # Find the test company
        result = await db.execute(select(Company))
        company = result.scalar_one()
        company_id = company.id

        # Verify user exists
        result = await db.execute(select(User).where(User.company_id == company_id))
        assert result.scalar_one_or_none() is not None

        # Delete company via raw SQL to trigger DB-level cascade (not ORM)
        await db.execute(text("DELETE FROM companies WHERE id = :cid"), {"cid": company_id})
        await db.commit()

        # Verify user is cascade-deleted
        result = await db.execute(select(User).where(User.company_id == company_id))
        assert result.scalar_one_or_none() is None


# ── Soft Delete Columns ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_has_deleted_at_column():
    """Webhook model should have a deleted_at column."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(text("PRAGMA table_info('webhooks')"))
        columns = {row[1] for row in result.fetchall()}
        assert "deleted_at" in columns


@pytest.mark.asyncio
async def test_data_listing_has_deleted_at_column():
    """DataListing model should have a deleted_at column."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(text("PRAGMA table_info('data_listings')"))
        columns = {row[1] for row in result.fetchall()}
        assert "deleted_at" in columns


# ── Index Existence ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_data_reviews_report_id_index():
    """data_reviews.report_id should have an index."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(text("PRAGMA index_list('data_reviews')"))
        indexes = result.fetchall()
        index_names = [row[1] for row in indexes]
        assert any("report_id" in name for name in index_names)
