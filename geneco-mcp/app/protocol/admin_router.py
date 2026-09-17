"""Stage-1 credential intake: ``POST``/``GET``/``DELETE
/{tenant_slug}/credentials`` (D365) and ``.../custom-api-credentials``
(the custom fee-waiver/re-contract API).

This is a fundamentally more sensitive surface than the MCP ``tools/call``
endpoint (``router.py``) — it accepts real secrets (D365 ``client_secret``,
custom-API ``password``) — so unlike ``tools/call`` (intentionally
unauthenticated, matching duta-ilmu's platform-wide MCP convention), every
route here requires ``X-Admin-Api-Key``, mirroring integration-hub's
``require_internal_key`` pattern
(``services/integration-hub/src/integration_hub/api.py``).
"""

from __future__ import annotations

import secrets
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, HttpUrl

from geneco_mcp.config import Settings
from geneco_mcp.store.credentials import CredentialStore, D365CredentialsInput
from geneco_mcp.store.custom_api_credentials import (
    CustomApiCredentialsInput,
    CustomApiCredentialStore,
)

log = structlog.get_logger()

router = APIRouter()


class D365CredentialsIn(BaseModel):
    org_url: HttpUrl = Field(description="D365 org URL, e.g. https://yourorg.crm.dynamics.com")
    tenant_id: str = Field(description="Entra (Azure AD) tenant GUID.")
    client_id: str = Field(description="Entra app registration's client/application ID.")
    client_secret: str = Field(description="Entra app registration's client secret.")
    field_map: dict[str, str] = Field(default_factory=dict)


def _require_admin_key(settings: Settings, x_admin_api_key: str | None) -> None:
    if x_admin_api_key is None or not secrets.compare_digest(x_admin_api_key, settings.admin_api_key):
        log.warning("admin.api_key_rejected", header_present=x_admin_api_key is not None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin api key")


@router.post("/{tenant_slug}/credentials", status_code=status.HTTP_200_OK)
async def upsert_credentials(
    tenant_slug: str,
    body: D365CredentialsIn,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CredentialStore(session, encryption_key=settings.credential_encryption_key)
        await store.upsert(
            tenant_slug,
            D365CredentialsInput(
                org_url=str(body.org_url),
                tenant_id=body.tenant_id,
                client_id=body.client_id,
                client_secret=body.client_secret,
                field_map=body.field_map,
            ),
        )
        redacted = await store.get_redacted(tenant_slug)
    assert redacted is not None
    return redacted


@router.get("/{tenant_slug}/credentials")
async def get_credentials(
    tenant_slug: str,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CredentialStore(session, encryption_key=settings.credential_encryption_key)
        redacted = await store.get_redacted(tenant_slug)
    if redacted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no credentials registered")
    return redacted


@router.delete("/{tenant_slug}/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credentials(
    tenant_slug: str,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> None:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CredentialStore(session, encryption_key=settings.credential_encryption_key)
        deleted = await store.delete(tenant_slug)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no credentials registered")


class CustomApiCredentialsIn(BaseModel):
    base_url: HttpUrl = Field(description="Custom API base URL, e.g. https://api.geneco.example")
    username: str = Field(description="Basic auth username for the custom API.")
    password: str = Field(description="Basic auth password for the custom API.")


@router.post("/{tenant_slug}/custom-api-credentials", status_code=status.HTTP_200_OK)
async def upsert_custom_api_credentials(
    tenant_slug: str,
    body: CustomApiCredentialsIn,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CustomApiCredentialStore(session, encryption_key=settings.credential_encryption_key)
        await store.upsert(
            tenant_slug,
            CustomApiCredentialsInput(
                base_url=str(body.base_url),
                username=body.username,
                password=body.password,
            ),
        )
        redacted = await store.get_redacted(tenant_slug)
    assert redacted is not None
    return redacted


@router.get("/{tenant_slug}/custom-api-credentials")
async def get_custom_api_credentials(
    tenant_slug: str,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CustomApiCredentialStore(session, encryption_key=settings.credential_encryption_key)
        redacted = await store.get_redacted(tenant_slug)
    if redacted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no credentials registered")
    return redacted


@router.delete("/{tenant_slug}/custom-api-credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_api_credentials(
    tenant_slug: str,
    request: Request,
    x_admin_api_key: Annotated[str | None, Header()] = None,
) -> None:
    settings: Settings = request.app.state.settings
    _require_admin_key(settings, x_admin_api_key)
    async with request.app.state.session_factory() as session:
        store = CustomApiCredentialStore(session, encryption_key=settings.credential_encryption_key)
        deleted = await store.delete(tenant_slug)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no credentials registered")
