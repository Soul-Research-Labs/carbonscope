"""Phase 13: add missing indexes for production query performance.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-13
"""
from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"])
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(op.f("ix_credit_ledger_created_at"), "credit_ledger", ["created_at"])
    op.create_index(op.f("ix_alerts_created_at"), "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_created_at"), table_name="alerts")
    op.drop_index(op.f("ix_credit_ledger_created_at"), table_name="credit_ledger")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_users_company_id"), table_name="users")
