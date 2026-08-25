"""Add account type to verification challenges.
Revision ID: c3e7a9b4d2f1
Revises: c2f4d9a1b7e0
Author: Farruh
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e7a9b4d2f1"
down_revision: str | Sequence[str] | None = "c2f4d9a1b7e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verification_challenges",
        sa.Column("account_type", sa.String(length=16), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("verification_challenges", "account_type")
