"""Add updated_at to email activation tokens.
Revision ID: e5f9a2b6c7d8
Revises: d4e8f1a2b3c4
Author: Farruh
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e5f9a2b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d4e8f1a2b3c4"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "email_activation_tokens",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade() -> None:
    op.drop_column("email_activation_tokens", "updated_at")
