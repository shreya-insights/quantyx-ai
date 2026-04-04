"""Add fraud_analyzed_at for async fraud idempotency.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("fraud_analyzed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_tx_fraud_analyzed_at",
        "transactions",
        ["fraud_analyzed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_tx_fraud_analyzed_at", table_name="transactions")
    op.drop_column("transactions", "fraud_analyzed_at")
