"""Add password hashes to first-party accounts and activation links.

Revision ID: f6a1b2c3d4e5
Revises: e5f9a2b6c7d8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "e5f9a2b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_accounts", sa.Column("password_hash", sa.String(length=512), nullable=True))
    op.add_column(
        "email_activation_tokens",
        sa.Column("password_hash", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_activation_tokens", "password_hash")
    op.drop_column("user_accounts", "password_hash")
