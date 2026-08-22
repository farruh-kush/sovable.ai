"""Add secure email activation links.
Revision ID: d4e8f1a2b3c4
Revises: c3e7a9b4d2f1
Author: Farruh
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e8f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c3e7a9b4d2f1"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "email_activation_tokens",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("account_type", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_activation_tokens_token_hash", "email_activation_tokens", ["token_hash"], unique=True)
    op.create_index("ix_email_activation_tokens_email", "email_activation_tokens", ["email"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_email_activation_tokens_email", table_name="email_activation_tokens")
    op.drop_index("ix_email_activation_tokens_token_hash", table_name="email_activation_tokens")
    op.drop_table("email_activation_tokens")
