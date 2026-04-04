"""Create audit_logs table with append-only MySQL triggers.

Two-layer tamper protection:
  - SQLAlchemy event listeners (in app/models/audit_log.py) block ORM path.
  - MySQL triggers below block direct SQL path (defense in depth).

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_path", sa.String(512), nullable=False),
        sa.Column("request_method", sa.String(8), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_audit_logs_company_id", "audit_logs", ["company_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_audit_company_action_date",
        "audit_logs",
        ["company_id", "action", "created_at"],
    )
    op.create_index(
        "ix_audit_user_date",
        "audit_logs",
        ["user_id", "created_at"],
    )

    # Layer 2: DB-level append-only enforcement.
    # These triggers fire even when someone bypasses SQLAlchemy and runs raw SQL.
    # Note: no DELIMITER needed when executing via Python DB driver.
    op.execute(
        """
        CREATE TRIGGER prevent_audit_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'AuditLog is append-only. Updates are forbidden.';
        END
        """
    )

    op.execute(
        """
        CREATE TRIGGER prevent_audit_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'AuditLog records cannot be deleted.';
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_update")
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_delete")
    op.drop_table("audit_logs")
