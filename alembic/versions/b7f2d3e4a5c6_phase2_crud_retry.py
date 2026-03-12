"""phase2 — EmissionReport.notes + WebhookDelivery retry columns

Revision ID: b7f2d3e4a5c6
Revises: a8f3e1b9c4d2
Create Date: 2026-03-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7f2d3e4a5c6"
down_revision: Union[str, Sequence[str], None] = "a8f3e1b9c4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # EmissionReport.notes
    with op.batch_alter_table("emission_reports") as batch_op:
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))

    # WebhookDelivery retry columns
    with op.batch_alter_table("webhook_deliveries") as batch_op:
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("webhook_deliveries") as batch_op:
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("max_retries")
        batch_op.drop_column("retry_count")

    with op.batch_alter_table("emission_reports") as batch_op:
        batch_op.drop_column("notes")
