"""Persist Celery task id on transactions for fraud polling after page refresh."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("fraud_check_job_id", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "idx_tx_fraud_check_job_id",
        "transactions",
        ["fraud_check_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_tx_fraud_check_job_id", table_name="transactions")
    op.drop_column("transactions", "fraud_check_job_id")
