"""phase3 — soft delete columns, CHECK constraints

Revision ID: c9d4e5f6a7b8
Revises: b7f2d3e4a5c6
Create Date: 2026-03-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7f2d3e4a5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft-delete columns
    op.add_column("companies", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("supply_chain_links", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # CHECK constraints (SQLite ignores these; enforced in PostgreSQL)
    op.create_check_constraint("ck_emission_reports_scope1_non_negative", "emission_reports", "scope1 >= 0")
    op.create_check_constraint("ck_emission_reports_scope2_non_negative", "emission_reports", "scope2 >= 0")
    op.create_check_constraint("ck_emission_reports_scope3_non_negative", "emission_reports", "scope3 >= 0")
    op.create_check_constraint(
        "ck_emission_reports_confidence_range", "emission_reports",
        "confidence >= 0 AND confidence <= 1",
    )
    op.create_check_constraint("ck_credit_ledger_balance_non_negative", "credit_ledger", "balance_after >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_credit_ledger_balance_non_negative", "credit_ledger", type_="check")
    op.drop_constraint("ck_emission_reports_confidence_range", "emission_reports", type_="check")
    op.drop_constraint("ck_emission_reports_scope3_non_negative", "emission_reports", type_="check")
    op.drop_constraint("ck_emission_reports_scope2_non_negative", "emission_reports", type_="check")
    op.drop_constraint("ck_emission_reports_scope1_non_negative", "emission_reports", type_="check")

    op.drop_column("supply_chain_links", "deleted_at")
    op.drop_column("subscriptions", "deleted_at")
    op.drop_column("companies", "deleted_at")
