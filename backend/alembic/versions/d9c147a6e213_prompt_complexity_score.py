"""store prompt complexity score

Revision ID: d9c147a6e213
Revises: c91e820b8a31
Create Date: 2026-11-07
"""
from alembic import op
import sqlalchemy as sa

revision = "d9c147a6e213"
down_revision = "c91e820b8a31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prompt_analysis", sa.Column("complexity_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("prompt_analysis", "complexity_score")
