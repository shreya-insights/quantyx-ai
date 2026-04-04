"""Pre-aggregated analytics cache tables (hourly Celery refresh).

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_revenue_summaries",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, nullable=False),
        sa.Column("summary_month", sa.String(7), nullable=False),
        sa.Column("inflow", sa.Numeric(18, 2), nullable=False),
        sa.Column("outflow", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_flow", sa.Numeric(18, 2), nullable=False),
        sa.Column("transaction_count", sa.Integer, nullable=False),
        sa.Column("avg_transaction", sa.Numeric(18, 4), nullable=False),
        sa.Column("mom_growth_pct", sa.Numeric(18, 4), nullable=True),
        sa.Column("transaction_snapshot_count", sa.Integer, nullable=False),
        sa.Column("refreshed_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "summary_month",
            name="uq_revenue_company_month",
        ),
    )
    op.create_index(
        "ix_revenue_company_refreshed",
        "daily_revenue_summaries",
        ["company_id", "refreshed_at"],
    )

    op.create_table(
        "monthly_category_summaries",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, nullable=False),
        sa.Column("category_code", sa.String(32), nullable=False),
        sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("period_days", sa.Integer, nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("transaction_count", sa.Integer, nullable=False),
        sa.Column("pct_of_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("transaction_snapshot_count", sa.Integer, nullable=False),
        sa.Column("refreshed_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "category_code",
            "period_days",
            name="uq_category_company_code_period",
        ),
    )
    op.create_index(
        "ix_category_company_refreshed",
        "monthly_category_summaries",
        ["company_id", "refreshed_at"],
    )

    op.create_table(
        "merchant_ranking_caches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, nullable=False),
        sa.Column("merchant_id", sa.BigInteger, nullable=False),
        sa.Column("period_days", sa.Integer, nullable=False),
        sa.Column("merchant_name", sa.String(255), nullable=False),
        sa.Column("category_code", sa.String(10), nullable=True),
        sa.Column("rank_position", sa.Integer, nullable=False),
        sa.Column("total_revenue", sa.Numeric(18, 2), nullable=False),
        sa.Column("transaction_count", sa.Integer, nullable=False),
        sa.Column("avg_transaction", sa.Numeric(18, 4), nullable=False),
        sa.Column("revenue_share_pct", sa.Numeric(18, 4), nullable=False),
        sa.Column("rank_in_category", sa.Integer, nullable=False),
        sa.Column("transaction_snapshot_count", sa.Integer, nullable=False),
        sa.Column("refreshed_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "merchant_id",
            "period_days",
            name="uq_merchant_ranking_company_merchant_period",
        ),
    )
    op.create_index(
        "ix_merchant_ranking_company_refreshed",
        "merchant_ranking_caches",
        ["company_id", "refreshed_at"],
    )

    op.create_table(
        "kpi_summary_caches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger, nullable=False),
        sa.Column("period_type", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("total_transactions", sa.Integer, nullable=False),
        sa.Column("total_volume", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_inflow", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_outflow", sa.Numeric(18, 2), nullable=False),
        sa.Column("unique_customers", sa.Integer, nullable=False),
        sa.Column("unique_merchants", sa.Integer, nullable=False),
        sa.Column("avg_transaction_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("fraud_alert_count", sa.Integer, nullable=False),
        sa.Column("fraud_alert_rate_pct", sa.Float, nullable=False),
        sa.Column("active_accounts", sa.Integer, nullable=False),
        sa.Column("top_category", sa.String(100), nullable=True),
        sa.Column("mom_volume_growth_pct", sa.Float, nullable=True),
        sa.Column("transaction_snapshot_count", sa.Integer, nullable=False),
        sa.Column("refreshed_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "period_type",
            name="uq_kpi_company_period",
        ),
    )
    op.create_index(
        "ix_kpi_company_refreshed",
        "kpi_summary_caches",
        ["company_id", "refreshed_at"],
    )


def downgrade() -> None:
    op.drop_table("kpi_summary_caches")
    op.drop_table("merchant_ranking_caches")
    op.drop_table("monthly_category_summaries")
    op.drop_table("daily_revenue_summaries")
