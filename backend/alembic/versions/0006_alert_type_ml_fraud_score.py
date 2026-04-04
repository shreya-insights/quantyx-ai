"""Add ml_fraud_score to fraud_alerts.alert_type enum.

Required for the ML scoring Celery task to persist FraudAlert rows when the
XGBoost model flags a transaction.  The application model AlertType already
defines this variant; the DB enum was missing it.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_ENUM_WITHOUT_ML = (
    "rapid_transactions",
    "unusual_amount",
    "location_anomaly",
    "new_device",
    "velocity_breach",
    "duplicate_transaction",
    "night_pattern",
)
_ENUM_WITH_ML = _ENUM_WITHOUT_ML + ("ml_fraud_score",)


def upgrade() -> None:
    op.alter_column(
        "fraud_alerts",
        "alert_type",
        existing_type=sa.Enum(*_ENUM_WITHOUT_ML),
        type_=sa.Enum(*_ENUM_WITH_ML),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM fraud_alerts WHERE alert_type = 'ml_fraud_score'"
    )
    op.alter_column(
        "fraud_alerts",
        "alert_type",
        existing_type=sa.Enum(*_ENUM_WITH_ML),
        type_=sa.Enum(*_ENUM_WITHOUT_ML),
        existing_nullable=False,
    )
