"""Tenant D365 credential store: the one place that resolves a
``tenant_slug`` into a live, ready-to-call ``D365Connector`` — and the one
place ``client_secret`` ever gets decrypted.

Mirrors integration-hub's ``_load_connector``/``store.py`` pattern, but for
a single connector kind stored locally instead of proxied over HTTP.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from geneco_mcp.clients.d365_connector import D365Connector
from geneco_mcp.security.crypto import decrypt_secret, encrypt_secret
from geneco_mcp.store.tables import D365Credential

#: Masked placeholder shown in place of the real secret on every read path.
MASK = "•••"


class D365CredentialsInput:
    """Plain data holder for the fields a stage-1 intake call provides —
    kept separate from the DB row so callers never need to import the ORM
    model just to construct one."""

    __slots__ = ("org_url", "tenant_id", "client_id", "client_secret", "field_map")

    def __init__(
        self,
        *,
        org_url: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        field_map: dict[str, str] | None = None,
    ) -> None:
        self.org_url = org_url
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.field_map = field_map or {}


class CredentialStore:
    def __init__(self, session: AsyncSession, *, encryption_key: str) -> None:
        self._session = session
        self._encryption_key = encryption_key

    async def upsert(self, tenant_slug: str, config: D365CredentialsInput) -> D365Credential:
        row = await self._session.get(D365Credential, tenant_slug)
        encrypted_secret = encrypt_secret(config.client_secret, key=self._encryption_key)
        if row is None:
            row = D365Credential(tenant_slug=tenant_slug)
            self._session.add(row)
        row.org_url = str(config.org_url)
        row.tenant_id = config.tenant_id
        row.client_id = config.client_id
        row.client_secret_encrypted = encrypted_secret
        row.field_map = config.field_map
        row.enabled = True
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def delete(self, tenant_slug: str) -> bool:
        result = await self._session.execute(
            delete(D365Credential).where(D365Credential.tenant_slug == tenant_slug)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def get_redacted(self, tenant_slug: str) -> dict[str, Any] | None:
        row = await self._session.get(D365Credential, tenant_slug)
        if row is None:
            return None
        return {
            "tenant_slug": row.tenant_slug,
            "org_url": row.org_url,
            "tenant_id": row.tenant_id,
            "client_id": row.client_id,
            "client_secret": MASK,
            "field_map": row.field_map,
            "enabled": row.enabled,
        }

    async def get_connector(self, tenant_slug: str) -> D365Connector | None:
        row = await self._session.scalar(
            select(D365Credential).where(
                D365Credential.tenant_slug == tenant_slug, D365Credential.enabled.is_(True)
            )
        )
        if row is None:
            return None
        client_secret = decrypt_secret(row.client_secret_encrypted, key=self._encryption_key)
        return D365Connector(
            org_url=row.org_url,
            tenant_id=row.tenant_id,
            client_id=row.client_id,
            client_secret=client_secret,
            field_map=row.field_map,
        )
