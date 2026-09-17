from __future__ import annotations

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from geneco_mcp.config import Settings
from geneco_mcp.main import create_app
from geneco_mcp.store.tables import Base

TEST_ADMIN_API_KEY = "test-admin-key"
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture
def settings(tmp_path) -> Settings:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    # DDL setup uses a plain sync engine (no event loop involved) so the
    # async engine the app actually uses never has a connection reused
    # across a different event loop than TestClient's own.
    sync_engine = sa.create_engine(db_url.replace("+aiosqlite", ""))
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    return Settings(
        database_url=db_url,
        credential_encryption_key=TEST_ENCRYPTION_KEY,
        admin_api_key=TEST_ADMIN_API_KEY,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
