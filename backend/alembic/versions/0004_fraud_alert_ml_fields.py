"""Fraud alert ML fields: promote rule_metadata to TEXT, add model_version.

rule_metadata VARCHAR(1000) → TEXT: SHAP JSON for 5 features can reach ~800 chars;
Text avoids silent truncation.
model_version: enables per-model-version performance analysis + EU AI Act audit trail.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "fraud_alerts",
        "rule_metadata",
        existing_type=sa.String(1000),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.add_column(
        "fraud_alerts",
        sa.Column("model_version", sa.String(60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fraud_alerts", "model_version")
    op.alter_column(
        "fraud_alerts",
        "rule_metadata",
        existing_type=sa.Text(),
        type_=sa.String(1000),
        existing_nullable=True,
    )
