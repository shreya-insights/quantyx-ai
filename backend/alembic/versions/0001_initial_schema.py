"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # companies
    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column(
            "subscription_tier",
            sa.Enum("starter", "growth", "enterprise"),
            nullable=False,
            server_default="starter",
        ),
        sa.Column("api_key", sa.String(255), unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_company_slug", "companies", ["slug"])
    op.create_index("idx_company_tier", "companies", ["subscription_tier"])

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column(
            "role",
            sa.Enum("admin", "analyst", "viewer"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("last_login", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_user_company", "users", ["company_id"])
    op.create_index("idx_user_email", "users", ["email"])
    op.create_index("idx_user_role", "users", ["role"])

    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column(
            "parent_id",
            sa.BigInteger,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
        ),
    )

    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("account_number", sa.String(50), unique=True, nullable=False),
        sa.Column(
            "account_type",
            sa.Enum("checking", "savings", "credit", "investment"),
            nullable=False,
        ),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("opened_at", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_account_company", "accounts", ["company_id"])
    op.create_index("idx_account_user", "accounts", ["user_id"])

    # merchants
    op.create_table(
        "merchants",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category_code", sa.String(10)),
        sa.Column("country", sa.String(3)),
        sa.Column("city", sa.String(100)),
        sa.Column("is_flagged", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_merchant_company", "merchants", ["company_id"])

    # transactions (partitioned by year in MySQL; Alembic creates base table)
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.BigInteger,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "merchant_id",
            sa.BigInteger,
            sa.ForeignKey("merchants.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "category_id",
            sa.BigInteger,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
        ),
        sa.Column("transaction_ref", sa.String(100), unique=True, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "transaction_type",
            sa.Enum("debit", "credit", "transfer", "refund"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", "failed", "reversed"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("description", sa.Text),
        sa.Column("metadata", sa.JSON),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("device_fingerprint", sa.String(255)),
        sa.Column("location_lat", sa.Numeric(9, 6)),
        sa.Column("location_lng", sa.Numeric(9, 6)),
        sa.Column("transaction_date", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_tx_company_date", "transactions", ["company_id", "transaction_date"])
    op.create_index("idx_tx_account_date", "transactions", ["account_id", "transaction_date"])
    op.create_index("idx_tx_status", "transactions", ["status"])
    op.create_index("idx_tx_merchant", "transactions", ["merchant_id"])
    op.create_index("idx_tx_company_status_type", "transactions", ["company_id", "status", "transaction_type"])

    # fraud_alerts
    op.create_table(
        "fraud_alerts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger,
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alert_type",
            sa.Enum(
                "rapid_transactions", "unusual_amount", "location_anomaly",
                "new_device", "velocity_breach", "duplicate_transaction", "night_pattern"
            ),
            nullable=False,
        ),
        sa.Column(
            "severity", sa.Enum("low", "medium", "high", "critical"), nullable=False
        ),
        sa.Column("confidence_score", sa.Numeric(5, 2)),
        sa.Column("description", sa.Text),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="0"),
        sa.Column(
            "resolved_by",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("rule_metadata", sa.String(1000)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_fraud_company", "fraud_alerts", ["company_id"])
    op.create_index("idx_fraud_severity", "fraud_alerts", ["severity"])
    op.create_index("idx_fraud_resolved", "fraud_alerts", ["is_resolved"])

    # kpi_reports
    op.create_table(
        "kpi_reports",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_name", sa.Enum("starter", "growth", "enterprise"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("active", "cancelled", "expired", "trial"),
            nullable=False,
            server_default="trial",
        ),
        sa.Column(
            "billing_cycle",
            sa.Enum("monthly", "annual"),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("starts_at", sa.DateTime, nullable=False),
        sa.Column("ends_at", sa.DateTime),
        sa.Column("api_calls_limit", sa.Integer),
        sa.Column("api_calls_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("transaction_limit", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # saved_queries
    op.create_table(
        "saved_queries",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.BigInteger,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("execution_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_executed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_sq_company_user", "saved_queries", ["company_id", "user_id"])


def downgrade() -> None:
    op.drop_table("saved_queries")
    op.drop_table("subscriptions")
    op.drop_table("kpi_reports")
    op.drop_table("fraud_alerts")
    op.drop_table("transactions")
    op.drop_table("merchants")
    op.drop_table("accounts")
    op.drop_table("categories")
    op.drop_table("users")
    op.drop_table("companies")
