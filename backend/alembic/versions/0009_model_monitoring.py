"""Model monitoring tables, admin notifications, analyst ground-truth columns.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_performance_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("f1_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("precision_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("recall_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("auc_pr", sa.Numeric(10, 6), nullable=True),
        sa.Column("false_positive_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("avg_ml_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_version", sa.String(80), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "period_start",
            name="uq_perf_metric_company_period",
        ),
    )
    op.create_index("idx_perf_metric_company", "model_performance_metrics", ["company_id"])
    op.create_index("idx_perf_metric_period", "model_performance_metrics", ["period_start"])

    op.create_table(
        "feature_distribution_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("mean", sa.Numeric(18, 8), nullable=True),
        sa.Column("std", sa.Numeric(18, 8), nullable=True),
        sa.Column("p25", sa.Numeric(18, 8), nullable=True),
        sa.Column("p50", sa.Numeric(18, 8), nullable=True),
        sa.Column("p75", sa.Numeric(18, 8), nullable=True),
        sa.Column("p95", sa.Numeric(18, 8), nullable=True),
        sa.Column("psi_score", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "psi_status",
            sa.Enum("stable", "monitor", "drift", name="psi_status"),
            nullable=True,
        ),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "feature_name",
            "period_start",
            name="uq_feature_snap_company_feature_period",
        ),
    )
    op.create_index("idx_feature_snap_company", "feature_distribution_snapshots", ["company_id"])
    op.create_index("idx_feature_snap_feature", "feature_distribution_snapshots", ["feature_name"])

    op.create_table(
        "admin_notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "notification_type",
            sa.Enum("model_health", "drift_detected", name="admin_notification_type"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("warning", "critical", name="admin_notification_severity"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_admin_notif_company", "admin_notifications", ["company_id"])
    op.create_index("idx_admin_notif_created", "admin_notifications", ["created_at"])

    op.add_column(
        "fraud_alerts",
        sa.Column("is_confirmed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "fraud_alerts",
        sa.Column(
            "resolved_by_analyst_label",
            sa.Enum("fraud", "legitimate", name="analyst_ground_truth"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("fraud_alerts", "resolved_by_analyst_label")
    op.drop_column("fraud_alerts", "is_confirmed")

    op.drop_index("idx_admin_notif_created", table_name="admin_notifications")
    op.drop_index("idx_admin_notif_company", table_name="admin_notifications")
    op.drop_table("admin_notifications")

    op.drop_index("idx_feature_snap_feature", table_name="feature_distribution_snapshots")
    op.drop_index("idx_feature_snap_company", table_name="feature_distribution_snapshots")
    op.drop_table("feature_distribution_snapshots")

    op.drop_index("idx_perf_metric_period", table_name="model_performance_metrics")
    op.drop_index("idx_perf_metric_company", table_name="model_performance_metrics")
    op.drop_table("model_performance_metrics")
