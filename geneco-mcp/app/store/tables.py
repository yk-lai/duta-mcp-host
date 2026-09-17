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
    __tablename__ = "d365_credentials"

    tenant_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_url: Mapped[str] = mapped_column(String(512), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Fernet ciphertext — see ``security/crypto.py``. Never stored plaintext.
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
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
