"""Data warehouse OLAP tables — cohort retention, LTV, hourly heatmap.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cohort_retention_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("cohort_month", sa.String(length=7), nullable=False),
        sa.Column("months_since_cohort", sa.Integer(), nullable=False),
        sa.Column("user_count", sa.Integer(), nullable=False),
        sa.Column("retained_count", sa.Integer(), nullable=False),
        sa.Column("retention_rate", sa.Float(), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "cohort_month",
            "months_since_cohort",
            name="uq_cohort_retention_company_cohort_period",
        ),
    )
    op.create_index(
        "ix_cohort_retention_company",
        "cohort_retention_metrics",
        ["company_id"],
    )

    op.create_table(
        "lifetime_value_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("first_tx_date", sa.Date(), nullable=False),
        sa.Column("total_spend", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("tx_count", sa.Integer(), nullable=False),
        sa.Column("ltv_segment", sa.String(length=16), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "user_id",
            name="uq_ltv_company_user",
        ),
    )
    op.create_index(
        "ix_ltv_company_segment",
        "lifetime_value_metrics",
        ["company_id", "ltv_segment"],
    )

    op.create_table(
        "hourly_transaction_heatmaps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("hour_of_day", sa.Integer(), nullable=False),
        sa.Column("avg_count", sa.Float(), nullable=False),
        sa.Column("avg_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("fraud_rate", sa.Float(), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "day_of_week",
            "hour_of_day",
            name="uq_heatmap_company_dow_hod",
        ),
    )
    op.create_index(
        "ix_heatmap_company",
        "hourly_transaction_heatmaps",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_heatmap_company", table_name="hourly_transaction_heatmaps")
    op.drop_table("hourly_transaction_heatmaps")
    op.drop_index("ix_ltv_company_segment", table_name="lifetime_value_metrics")
    op.drop_table("lifetime_value_metrics")
    op.drop_index("ix_cohort_retention_company", table_name="cohort_retention_metrics")
    op.drop_table("cohort_retention_metrics")
