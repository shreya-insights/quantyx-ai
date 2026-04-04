"""Feature store tables for ML features (user, merchant, velocity).

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("avg_amount_7d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_amount_30d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_amount_90d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tx_count_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tx_count_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tx_count_1h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_merchants_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_categories_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fraud_rate_30d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("most_common_hour", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("most_common_dow", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("std_amount_30d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_company_features"),
    )
    op.create_index(
        "ix_user_features_company_computed",
        "user_features",
        ["company_id", "computed_at"],
    )
    op.create_index(
        "ix_user_features_lookup",
        "user_features",
        ["user_id", "company_id"],
    )

    op.create_table(
        "merchant_features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("merchant_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("avg_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tx_count_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fraud_rate_30d", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unique_users_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_high_risk_category", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "company_id", name="uq_merchant_company_features"),
    )
    op.create_index(
        "ix_merchant_features_company_computed",
        "merchant_features",
        ["company_id", "computed_at"],
    )

    op.create_table(
        "velocity_features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("tx_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unique_merchants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "company_id",
            "window_minutes",
            name="uq_velocity_user_company_window",
        ),
    )
    op.create_index(
        "ix_velocity_lookup",
        "velocity_features",
        ["user_id", "company_id", "window_minutes", "computed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_velocity_lookup", table_name="velocity_features")
    op.drop_table("velocity_features")
    op.drop_index("ix_merchant_features_company_computed", table_name="merchant_features")
    op.drop_table("merchant_features")
    op.drop_index("ix_user_features_lookup", table_name="user_features")
    op.drop_index("ix_user_features_company_computed", table_name="user_features")
    op.drop_table("user_features")
