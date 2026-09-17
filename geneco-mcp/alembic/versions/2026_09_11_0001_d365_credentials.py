"""d365 credentials store

Revision ID: 0001
Revises:
Create Date: 2026-09-11
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "d365_credentials",
        sa.Column("tenant_slug", sa.String(length=64), primary_key=True),
        sa.Column("org_url", sa.String(length=512), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("field_map", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("d365_credentials")
