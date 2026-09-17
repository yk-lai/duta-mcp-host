"""custom api credentials store

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-15
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_api_credentials",
        sa.Column("tenant_slug", sa.String(length=64), primary_key=True),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("custom_api_credentials")
