"""Tenant custom-API credential store: the one place that resolves a
``tenant_slug`` into the decrypted ``base_url``/``username``/``password``
the custom fee-waiver/re-contract API client needs — and the one place
``password`` ever gets decrypted.

Mirrors ``store/credentials.py``'s ``CredentialStore`` for the D365
connector, but for this second, simpler credential kind (Basic Auth, no
MSAL token exchange).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from geneco_mcp.security.crypto import decrypt_secret, encrypt_secret
from geneco_mcp.store.tables import CustomApiCredential

#: Masked placeholder shown in place of the real secret on every read path.
MASK = "•••"


class CustomApiCredentialsInput:
    """Plain data holder for the fields a stage-1 intake call provides —
    kept separate from the DB row so callers never need to import the ORM
    model just to construct one."""

    __slots__ = ("base_url", "username", "password")

    def __init__(self, *, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password


@dataclass(frozen=True, slots=True)
class ResolvedCustomApiCredentials:
    """Decrypted credentials, ready to hand to the custom API client."""

    base_url: str
    username: str
    password: str


class CustomApiCredentialStore:
    def __init__(self, session: AsyncSession, *, encryption_key: str) -> None:
        self._session = session
        self._encryption_key = encryption_key

    async def upsert(
        self, tenant_slug: str, config: CustomApiCredentialsInput
    ) -> CustomApiCredential:
        row = await self._session.get(CustomApiCredential, tenant_slug)
        encrypted_password = encrypt_secret(config.password, key=self._encryption_key)
        if row is None:
            row = CustomApiCredential(tenant_slug=tenant_slug)
            self._session.add(row)
        row.base_url = config.base_url
        row.username = config.username
        row.password_encrypted = encrypted_password
        row.enabled = True
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def delete(self, tenant_slug: str) -> bool:
        result = await self._session.execute(
            delete(CustomApiCredential).where(CustomApiCredential.tenant_slug == tenant_slug)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def get_redacted(self, tenant_slug: str) -> dict[str, Any] | None:
        row = await self._session.get(CustomApiCredential, tenant_slug)
        if row is None:
            return None
        return {
            "tenant_slug": row.tenant_slug,
            "base_url": row.base_url,
            "username": row.username,
            "password": MASK,
            "enabled": row.enabled,
        }

    async def get_credentials(self, tenant_slug: str) -> ResolvedCustomApiCredentials | None:
        row = await self._session.scalar(
            select(CustomApiCredential).where(
                CustomApiCredential.tenant_slug == tenant_slug,
                CustomApiCredential.enabled.is_(True),
            )
        )
        if row is None:
            return None
        password = decrypt_secret(row.password_encrypted, key=self._encryption_key)
        return ResolvedCustomApiCredentials(
            base_url=row.base_url, username=row.username, password=password
        )
