"""add expiring team invitations

Revision ID: c91e820b8a31
Revises: dbf6b5eba66b
Create Date: 2026-11-07
"""
from alembic import op
import sqlalchemy as sa

revision = "c91e820b8a31"
down_revision = "dbf6b5eba66b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('admin','member')", name="ck_team_invitation_role"),
    )
    op.create_index("ix_team_invitations_team_id", "team_invitations", ["team_id"])
    op.create_index("ix_team_invitations_email", "team_invitations", ["email"])
    op.create_index("ix_team_invitations_token_hash", "team_invitations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_team_invitations_token_hash", table_name="team_invitations")
    op.drop_index("ix_team_invitations_email", table_name="team_invitations")
    op.drop_index("ix_team_invitations_team_id", table_name="team_invitations")
    op.drop_table("team_invitations")
