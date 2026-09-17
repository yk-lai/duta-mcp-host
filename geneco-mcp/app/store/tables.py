"""SQLAlchemy tables: one row per tenant's credentials, per connector kind.

Unlike integration-hub's ``tenant_connectors`` (which stores several
connector *kinds* per tenant in one table), this service gives each
connector kind its own table with ``tenant_slug`` as the primary key
directly — ``D365Credential`` for the D365 connector, ``CustomApiCredential``
for the custom fee-waiver/re-contract API. Every secret column
(``client_secret_encrypted``, ``password_encrypted``) is a Fernet
ciphertext (see ``security/crypto.py``) — never the plaintext value.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class D365Credential(Base):
    """A tenant's *Key Vault* credentials, not its D365 ones.

    The D365 app registration (``Crm-Client-Id``/``Crm-Client-Secret``)
    lives in the tenant's vault and is fetched at call time — see
    ``clients/keyvault_client.py`` — so it is never at rest here. Only the
    vault credential is stored, and only its secret is encrypted.
    """

    __tablename__ = "d365_credentials"

    tenant_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_url: Mapped[str] = mapped_column(String(512), nullable=False)
    #: Entra tenant GUID — used as the authority for BOTH the Key Vault
    #: token and the Dataverse token, on the assumption (inherited from
    #: geneco-poc's ``crm_client.py``) that a tenant's vault and CRM app
    #: registrations live in the same Entra tenant.
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kv_vault_url: Mapped[str] = mapped_column(String(512), nullable=False)
    kv_client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Fernet ciphertext — see ``security/crypto.py``. Never stored plaintext.
    kv_client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    field_map: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class CustomApiCredential(Base):
    __tablename__ = "custom_api_credentials"

    tenant_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    #: Fernet ciphertext — see ``security/crypto.py``. Never stored plaintext.
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
