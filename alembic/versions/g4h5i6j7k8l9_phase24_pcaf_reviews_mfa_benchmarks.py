"""Phase 24 tables: PCAF, reviews, MFA, benchmarks

Revision ID: g4h5i6j7k8l9
Revises: f3a4b5c6d7e8
Create Date: 2026-03-13 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "g4h5i6j7k8l9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Financed Portfolios (PCAF) ──
    op.create_table(
        "financed_portfolios",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_financed_portfolios_company_year", "financed_portfolios", ["company_id", "year"])

    # ── Financed Assets (PCAF) ──
    op.create_table(
        "financed_assets",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("portfolio_id", sa.String(32), sa.ForeignKey("financed_portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column("asset_class", sa.String(50), nullable=False),
        sa.Column("outstanding_amount", sa.Float, nullable=False),
        sa.Column("total_equity_debt", sa.Float, nullable=False),
        sa.Column("investee_emissions_tco2e", sa.Float, nullable=False),
        sa.Column("attribution_factor", sa.Float, nullable=True),
        sa.Column("financed_emissions_tco2e", sa.Float, nullable=True),
        sa.Column("data_quality_score", sa.Integer, nullable=False, server_default="3"),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("outstanding_amount >= 0", name="ck_financed_assets_outstanding_non_negative"),
        sa.CheckConstraint("total_equity_debt > 0", name="ck_financed_assets_equity_debt_positive"),
        sa.CheckConstraint("investee_emissions_tco2e >= 0", name="ck_financed_assets_emissions_non_negative"),
        sa.CheckConstraint("data_quality_score >= 1 AND data_quality_score <= 5", name="ck_financed_assets_dq_range"),
    )

    # ── Data Reviews ──
    op.create_table(
        "data_reviews",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("report_id", sa.String(32), sa.ForeignKey("emission_reports.id"), nullable=False, index=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("submitted_by", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_by", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── MFA Secrets ──
    op.create_table(
        "mfa_secrets",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("totp_secret", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.false_()),
        sa.Column("backup_codes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Industry Benchmarks ──
    op.create_table(
        "industry_benchmarks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("industry", sa.String(100), nullable=False, index=True),
        sa.Column("region", sa.String(10), nullable=False, server_default="GLOBAL"),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("avg_scope1_tco2e", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_scope2_tco2e", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_scope3_tco2e", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_total_tco2e", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_intensity_per_employee", sa.Float, nullable=True),
        sa.Column("avg_intensity_per_revenue", sa.Float, nullable=True),
        sa.Column("sample_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source", sa.String(255), nullable=False, server_default="CarbonScope aggregated data"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("industry", "region", "year", name="uq_benchmark_industry_region_year"),
    )


def downgrade() -> None:
    op.drop_table("industry_benchmarks")
    op.drop_table("mfa_secrets")
    op.drop_table("data_reviews")
    op.drop_table("financed_assets")
    op.drop_index("ix_financed_portfolios_company_year", table_name="financed_portfolios")
    op.drop_table("financed_portfolios")
