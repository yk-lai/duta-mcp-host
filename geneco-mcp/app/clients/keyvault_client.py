"""Azure Key Vault secret reader — OAuth2 client-credentials via msal
against the tenant's Key-Vault-scoped Entra app registration.

This is the first hop of the two-hop credential chain: a tenant's stored
Key Vault credentials fetch that tenant's *real* D365 app registration
(``Crm-Client-Id``/``Crm-Client-Secret``) at call time, so the D365 secret
itself is never at rest in this service — only the vault credential is
(see ``store/crm_resolver.py`` for the caching layer above this).

Mirrors ``clients/d365_connector.py``'s honest-error boundary: every
outbound msal/httpx call and response parse is wrapped so a real failure
raises ``KeyVaultError`` rather than leaking an unhandled exception. The
resolver above translates that into the ``ConnectorError`` the tools
already handle, so a vault outage surfaces as a relayable error and never
a raw 500.
"""

from __future__ import annotations

from typing import Any

import httpx

#: Key Vault data-plane API version used for the secret GET.
API_VERSION = "7.4"

#: OAuth2 scope for the Key Vault data plane.
VAULT_SCOPE = "https://vault.azure.net/.default"

#: Vault secret names holding the tenant's real D365 app registration.
#: Hardcoded deliberately — every tenant's vault uses these exact names
#: (matching geneco-poc's ``crm_client.py``); make them per-tenant columns
#: only if a tenant ever needs different ones.
CRM_CLIENT_ID_SECRET = "Crm-Client-Id"
CRM_CLIENT_SECRET_SECRET = "Crm-Client-Secret"


class KeyVaultError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class KeyVaultClient:
    """One instance per resolution, built from a tenant's stored vault
    credentials — stateless across calls, no cached HTTP client."""

    def __init__(
        self, *, vault_url: str, tenant_id: str, client_id: str, client_secret: str
    ) -> None:
        self.vault_url = str(vault_url).rstrip("/")
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._msal_app: Any = None

    @property
    def _authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    def _get_msal_app(self) -> Any:
        if self._msal_app is None:
            import msal

            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=self._authority,
            )
        return self._msal_app

    def _acquire_token(self) -> str:
        try:
            result = self._get_msal_app().acquire_token_for_client(scopes=[VAULT_SCOPE])
        except Exception as exc:  # msal/network failure — never let this leak as a 500
            raise KeyVaultError(f"key vault token acquisition failed: {exc}") from exc
        if "access_token" not in result:
            raise KeyVaultError(
                f"key vault token acquisition failed: {result.get('error_description', result)}",
                retryable=False,
            )
        return result["access_token"]

    async def get_secret(self, name: str) -> str:
        """Read one secret's current value from the vault."""
        url = f"{self.vault_url}/secrets/{name}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    params={"api-version": API_VERSION},
                    headers={
                        "Authorization": f"Bearer {self._acquire_token()}",
                        "Accept": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise KeyVaultError(f"key vault request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise KeyVaultError(
                f"key vault request failed {resp.status_code}: {resp.text[:500]}",
                retryable=resp.status_code >= 500,
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise KeyVaultError("malformed key vault response (not JSON)") from exc
        value = data.get("value")
        if not value:
            raise KeyVaultError(f"key vault secret {name!r} has no value", retryable=False)
        return value

    async def get_crm_credentials(self) -> tuple[str, str]:
        """The tenant's real D365 app registration, as ``(client_id, client_secret)``."""
        client_id = await self.get_secret(CRM_CLIENT_ID_SECRET)
        client_secret = await self.get_secret(CRM_CLIENT_SECRET_SECRET)
        return client_id, client_secret
