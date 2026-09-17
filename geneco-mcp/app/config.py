from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """geneco-mcp settings.

    This service owns its own D365 connector: it stores each tenant's
    Entra/Dataverse credentials (encrypted, see ``security/crypto.py``) and
    calls D365 directly (see ``clients/d365_connector.py``) — it no longer
    depends on duta-ilmu's integration-hub.
    """

    database_url: str = "postgresql+asyncpg://genecomcp:genecomcp-dev@localhost:55441/geneco_mcp"
    #: Fernet key (``cryptography.fernet.Fernet.generate_key()``) used to
    #: encrypt each stored ``client_secret`` at rest. In production this
    #: should be a key issued by a real KMS/Key Vault, not a bare env var —
    #: see the plan's "deferred security follow-up" note.
    credential_encryption_key: str = ""
    #: Shared secret required on the credential-intake endpoints
    #: (``POST``/``GET``/``DELETE /{tenant_slug}/credentials``), header
    #: ``X-Admin-Api-Key``. Unlike ``tools/call``, this surface accepts real
    #: secrets and must be authenticated.
    admin_api_key: str = ""

    log_level: str = "INFO"
    log_format: str = "json"
    env: str = "local"

    model_config = SettingsConfigDict(
        env_prefix="GENECO_MCP_",
        env_file=".env",
        extra="ignore",
    )
