"""d365 credentials store holds key vault creds, not crm creds

The D365 app registration is now read from each tenant's Key Vault at call
time (``Crm-Client-Id``/``Crm-Client-Secret``), so ``client_id``/
``client_secret_encrypted`` are replaced by the vault credentials that
fetch them.

Destructive by design: the dropped columns hold the only copy of each
tenant's D365 app registration *in this service*, and the replacement
values (vault URL + vault client credentials) can't be derived from them.
Existing tenants must be re-registered via
``POST /{tenant_slug}/credentials`` after this migration.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "d365_credentials", sa.Column("kv_vault_url", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "d365_credentials", sa.Column("kv_client_id", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "d365_credentials", sa.Column("kv_client_secret_encrypted", sa.Text(), nullable=True)
    )
    # Any pre-existing row carries D365 credentials that this schema no
    # longer has anywhere to put; it must be re-registered rather than
    # back-filled with placeholders that would fail at call time.
    op.execute("DELETE FROM d365_credentials")
    op.alter_column("d365_credentials", "kv_vault_url", nullable=False)
    op.alter_column("d365_credentials", "kv_client_id", nullable=False)
    op.alter_column("d365_credentials", "kv_client_secret_encrypted", nullable=False)
    op.drop_column("d365_credentials", "client_secret_encrypted")
    op.drop_column("d365_credentials", "client_id")


def downgrade() -> None:
    op.add_column("d365_credentials", sa.Column("client_id", sa.String(length=64), nullable=True))
    op.add_column(
        "d365_credentials", sa.Column("client_secret_encrypted", sa.Text(), nullable=True)
    )
    op.execute("DELETE FROM d365_credentials")
    op.alter_column("d365_credentials", "client_id", nullable=False)
    op.alter_column("d365_credentials", "client_secret_encrypted", nullable=False)
    op.drop_column("d365_credentials", "kv_client_secret_encrypted")
    op.drop_column("d365_credentials", "kv_client_id")
    op.drop_column("d365_credentials", "kv_vault_url")
