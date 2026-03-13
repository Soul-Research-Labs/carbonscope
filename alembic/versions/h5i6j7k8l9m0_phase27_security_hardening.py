"""Phase 27: Security hardening — TOTP encryption, updated_at, cascades, indexes, soft delete

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-03-13 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "h5i6j7k8l9m0"
down_revision = "g4h5i6j7k8l9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add updated_at to users table ──
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
        )

    # ── 2. Add deleted_at soft delete to webhooks ──
    with op.batch_alter_table("webhooks") as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )

    # ── 3. Add deleted_at soft delete to data_listings ──
    with op.batch_alter_table("data_listings") as batch_op:
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )

    # ── 4. Add missing index on data_reviews.report_id ──
    with op.batch_alter_table("data_reviews") as batch_op:
        batch_op.create_index("ix_data_reviews_report_id", ["report_id"])

    # ── 5. Add CASCADE ON DELETE to company ForeignKeys ──
    # Using batch mode for SQLite compatibility (render_as_batch=True in env.py)
    _fk_cascade_tables = [
        ("users", "company_id", "companies", "id"),
        ("data_uploads", "company_id", "companies", "id"),
        ("emission_reports", "company_id", "companies", "id"),
        ("supply_chain_links", "buyer_company_id", "companies", "id"),
        ("supply_chain_links", "supplier_company_id", "companies", "id"),
        ("webhooks", "company_id", "companies", "id"),
        ("subscriptions", "company_id", "companies", "id"),
        ("credit_ledger", "company_id", "companies", "id"),
        ("alerts", "company_id", "companies", "id"),
        ("data_listings", "seller_company_id", "companies", "id"),
        ("data_reviews", "company_id", "companies", "id"),
        ("audit_logs", "company_id", "companies", "id"),
        ("questionnaires", "company_id", "companies", "id"),
        ("scenarios", "company_id", "companies", "id"),
        ("data_purchases", "buyer_company_id", "companies", "id"),
        ("financed_portfolios", "company_id", "companies", "id"),
    ]

    # Note: batch_alter_table handles SQLite's lack of ALTER TABLE support.
    # For PostgreSQL, this recreates constraints with ON DELETE CASCADE.
    for table, col, ref_table, ref_col in _fk_cascade_tables:
        with op.batch_alter_table(table) as batch_op:
            # Drop old FK and create new one with CASCADE
            fk_name = f"fk_{table}_{col}_{ref_table}"
            batch_op.drop_constraint(fk_name, type_="foreignkey")
            batch_op.create_foreign_key(
                fk_name, ref_table, [col], [ref_col], ondelete="CASCADE"
            )


def downgrade() -> None:
    # Reverse CASCADE constraints
    _fk_cascade_tables = [
        ("users", "company_id", "companies", "id"),
        ("data_uploads", "company_id", "companies", "id"),
        ("emission_reports", "company_id", "companies", "id"),
        ("supply_chain_links", "buyer_company_id", "companies", "id"),
        ("supply_chain_links", "supplier_company_id", "companies", "id"),
        ("webhooks", "company_id", "companies", "id"),
        ("subscriptions", "company_id", "companies", "id"),
        ("credit_ledger", "company_id", "companies", "id"),
        ("alerts", "company_id", "companies", "id"),
        ("data_listings", "seller_company_id", "companies", "id"),
        ("data_reviews", "company_id", "companies", "id"),
        ("audit_logs", "company_id", "companies", "id"),
        ("questionnaires", "company_id", "companies", "id"),
        ("scenarios", "company_id", "companies", "id"),
        ("data_purchases", "buyer_company_id", "companies", "id"),
        ("financed_portfolios", "company_id", "companies", "id"),
    ]

    for table, col, ref_table, ref_col in _fk_cascade_tables:
        with op.batch_alter_table(table) as batch_op:
            fk_name = f"fk_{table}_{col}_{ref_table}"
            batch_op.drop_constraint(fk_name, type_="foreignkey")
            batch_op.create_foreign_key(
                fk_name, ref_table, [col], [ref_col]
            )

    # Drop index
    with op.batch_alter_table("data_reviews") as batch_op:
        batch_op.drop_index("ix_data_reviews_report_id")

    # Drop soft delete columns
    with op.batch_alter_table("data_listings") as batch_op:
        batch_op.drop_column("deleted_at")

    with op.batch_alter_table("webhooks") as batch_op:
        batch_op.drop_column("deleted_at")

    # Drop updated_at from users
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("updated_at")
