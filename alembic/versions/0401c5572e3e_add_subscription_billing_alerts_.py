"""add subscription billing alerts marketplace models

Revision ID: 0401c5572e3e
Revises: d2cd1a2a2b76
Create Date: 2026-03-11 21:24:18.820712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0401c5572e3e'
down_revision: Union[str, Sequence[str], None] = 'd2cd1a2a2b76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subscription, credit_ledger, alerts, data_listings, and data_purchases tables."""

    op.create_table('subscriptions',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('plan', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
    sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_subscriptions_company_id'), ['company_id'], unique=False)

    op.create_table('credit_ledger',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=False),
    sa.Column('balance_after', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('credit_ledger', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_credit_ledger_company_id'), ['company_id'], unique=False)

    op.create_table('alerts',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('alert_type', sa.String(length=100), nullable=False),
    sa.Column('severity', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('metadata_json', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alerts_company_id'), ['company_id'], unique=False)

    op.create_table('data_listings',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('seller_company_id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('data_type', sa.String(length=100), nullable=False),
    sa.Column('industry', sa.String(length=100), nullable=False),
    sa.Column('region', sa.String(length=10), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('price_credits', sa.Integer(), nullable=False),
    sa.Column('anonymized_data', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['seller_company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('data_listings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_data_listings_seller_company_id'), ['seller_company_id'], unique=False)

    op.create_table('data_purchases',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('listing_id', sa.String(length=32), nullable=False),
    sa.Column('buyer_company_id', sa.String(length=32), nullable=False),
    sa.Column('price_credits', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['buyer_company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['listing_id'], ['data_listings.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('data_purchases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_data_purchases_buyer_company_id'), ['buyer_company_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_purchases_listing_id'), ['listing_id'], unique=False)


def downgrade() -> None:
    """Drop the 5 new tables."""
    with op.batch_alter_table('data_purchases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_data_purchases_listing_id'))
        batch_op.drop_index(batch_op.f('ix_data_purchases_buyer_company_id'))
    op.drop_table('data_purchases')

    with op.batch_alter_table('data_listings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_data_listings_seller_company_id'))
    op.drop_table('data_listings')

    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alerts_company_id'))
    op.drop_table('alerts')

    with op.batch_alter_table('credit_ledger', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_credit_ledger_company_id'))
    op.drop_table('credit_ledger')

    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_subscriptions_company_id'))
    op.drop_table('subscriptions')
