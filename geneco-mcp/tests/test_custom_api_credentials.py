from __future__ import annotations

import pytest

from geneco_mcp.config import Settings
from geneco_mcp.db import build_engine, build_session_factory
from geneco_mcp.store.custom_api_credentials import (
    CustomApiCredentialsInput,
    CustomApiCredentialStore,
)

CREDENTIALS = CustomApiCredentialsInput(
    base_url="https://custom-api.geneco.example",
    username="cxchat-svc",
    password="super-secret-value",
)


@pytest.fixture
async def store(settings: Settings) -> CustomApiCredentialStore:
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        yield CustomApiCredentialStore(session, encryption_key=settings.credential_encryption_key)
    await engine.dispose()


async def test_upsert_then_get_redacted_masks_password(store: CustomApiCredentialStore) -> None:
    await store.upsert("geneco", CREDENTIALS)

    redacted = await store.get_redacted("geneco")

    assert redacted is not None
    assert redacted["base_url"] == CREDENTIALS.base_url
    assert redacted["username"] == CREDENTIALS.username
    assert redacted["password"] == "•••"


async def test_get_credentials_decrypts_password(store: CustomApiCredentialStore) -> None:
    await store.upsert("geneco", CREDENTIALS)

    resolved = await store.get_credentials("geneco")

    assert resolved is not None
    assert resolved.base_url == CREDENTIALS.base_url
    assert resolved.username == CREDENTIALS.username
    assert resolved.password == CREDENTIALS.password


async def test_get_credentials_missing_tenant_is_none(store: CustomApiCredentialStore) -> None:
    assert await store.get_credentials("unknown-tenant") is None


async def test_get_redacted_missing_tenant_is_none(store: CustomApiCredentialStore) -> None:
    assert await store.get_redacted("unknown-tenant") is None


async def test_delete_then_get_is_none(store: CustomApiCredentialStore) -> None:
    await store.upsert("geneco", CREDENTIALS)

    deleted = await store.delete("geneco")

    assert deleted is True
    assert await store.get_redacted("geneco") is None


async def test_delete_missing_tenant_returns_false(store: CustomApiCredentialStore) -> None:
    assert await store.delete("unknown-tenant") is False


async def test_upsert_twice_overwrites_previous_values(store: CustomApiCredentialStore) -> None:
    await store.upsert("geneco", CREDENTIALS)
    updated = CustomApiCredentialsInput(
        base_url="https://custom-api.geneco.example/v2",
        username="cxchat-svc-2",
        password="rotated-secret",
    )

    await store.upsert("geneco", updated)
    resolved = await store.get_credentials("geneco")

    assert resolved is not None
    assert resolved.base_url == updated.base_url
    assert resolved.username == updated.username
    assert resolved.password == updated.password
