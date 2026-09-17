# geneco-mcp

An MCP server hosting seven tools for duta-ilmu's orchestrator to call:

| Tool | What it does |
|---|---|
| `verify_account` | Account inquiry — confirms an `account_id`/`mobile_number` pair, returns the account holder's name and balance. |
| `create_support_case` | Create case — re-verifies the account, then creates a D365 incident. |
| `get_support_cases` | Case inquiry — re-verifies the account, then lists its recent D365 incidents. |
| `check_fee_waiver_status` | Fee waiver inquiry — looks up an account's fee waiver contract lines (ETF, APDF, LPC, PF) against the custom cxchat API. |
| `check_recontract_eligibility` | Re-contract eligibility check — looks up whether an account is eligible to re-contract, against the custom cxchat API. |
| `reverse_fee` | Fee reversal — reverses the applicable fees for an account, against the custom cxchat API. |
| `request_password_reset` | Self-service-portal password reset — sends a password-reset email for a registered account email address, against the custom cxchat API. |

This service owns its own connectors and credential storage — D365/Dataverse
(`app/clients/d365_connector.py`) and the custom fee-waiver API
(`app/clients/custom_api_client.py`), each with its own table under
`app/store/` — no dependency on duta-ilmu's integration-hub. Each tenant's
credentials are registered once per connector kind (stage 1, below) and
encrypted at rest (`app/security/crypto.py`); every `tools/call` (stage 2)
resolves the tenant's stored credentials for whichever connector that tool
needs and talks to the backend directly.

For D365 the stored credential is the tenant's **Key Vault** app
registration, not its D365 one: the real D365 app registration
(`Crm-Client-Id`/`Crm-Client-Secret`) is fetched from that vault on the
tenant's first call and cached in memory for 15 minutes
(`app/store/crm_resolver.py`), so the D365 secret is never at rest here.
The fetch is lazy rather than at startup — a tenant registered after boot
works without a restart, a vault outage degrades only the tenant being
called, and a rotated secret is picked up within the TTL (immediately, if
the credentials are re-registered). The custom API stores Basic Auth
credentials directly, since it has no vault.

## Two-stage flow

**Stage 1 — one-time credential intake** (authenticated, `X-Admin-Api-Key`),
one pair of endpoints per connector kind:

```
POST   /{tenant_slug}/credentials   # register/replace a tenant's D365 credentials
GET    /{tenant_slug}/credentials   # confirm what's registered (kv_client_secret always masked)
DELETE /{tenant_slug}/credentials   # revoke

POST   /{tenant_slug}/custom-api-credentials   # register/replace the custom API's Basic Auth creds
GET    /{tenant_slug}/custom-api-credentials   # confirm what's registered (password always masked)
DELETE /{tenant_slug}/custom-api-credentials   # revoke
```

```bash
curl -s -X POST localhost:8000/geneco/credentials \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Api-Key: dev-admin-key' \
  -d '{
    "org_url": "https://geneco.crm.dynamics.com",
    "tenant_id": "<entra-tenant-guid>",
    "kv_vault_url": "https://<your-vault>.vault.azure.net",
    "kv_client_id": "<vault-reader-app-client-id>",
    "kv_client_secret": "<vault-reader-app-client-secret>"
  }'

curl -s -X POST localhost:8000/geneco/custom-api-credentials \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Api-Key: dev-admin-key' \
  -d '{
    "base_url": "https://<custom-api-host>",
    "username": "<basic-auth-username>",
    "password": "<basic-auth-password>"
  }'
```

**Stage 2 — the MCP protocol face**, matching exactly what duta-ilmu's
orchestrator MCP client speaks
(`services/orchestrator/src/orchestrator/tools/mcp.py`): JSON-RPC
`initialize` / `notifications/initialized` / `tools/list` / `tools/call`.

```
POST /{tenant_slug}
```

`tenant_slug` is a URL path parameter, not hardcoded — any tenant with
credentials registered via stage 1 can point its MCP config at
`.../geneco-mcp/{their_slug}`.

No transport-level authentication on this endpoint (the orchestrator's MCP
client sends no auth headers to tenant MCP servers today — a
platform-wide convention, not introduced here). This is a deliberate,
confirmed tradeoff, not an oversight — see the project's "deferred
security follow-up" note: once real D365 credentials live here, this
endpoint directly triggers live D365/custom-API calls using stored
secrets, so this is worth revisiting alongside network-level access
control. The data-level gate is unchanged regardless: every D365 tool
requires a correct `account_id` + `mobile_number` match before returning
anything. The four custom-API tools (`check_fee_waiver_status`,
`check_recontract_eligibility`, `reverse_fee`, `request_password_reset`)
are the exception — the custom API has no documented shape for that
cross-check, so `account_number` (or `email`, for password reset) is a
direct lookup key there, not something re-verified first.

## Configuration

All env vars are prefixed `GENECO_MCP_` — see [.env.example](./.env.example).

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://genecomcp:genecomcp-dev@localhost:55441/geneco_mcp` | Where tenant credentials are stored (D365 and custom API, one table each). |
| `CREDENTIAL_ENCRYPTION_KEY` | *(empty)* | Fernet key encrypting each stored `kv_client_secret` (D365's vault credential) and `password` (custom API). Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. A bare env var is a stopgap — swap for a real KMS/Key Vault-issued key before production. |
| `ADMIN_API_KEY` | *(empty)* | Sent as `X-Admin-Api-Key` — required on `/{tenant_slug}/credentials` and `/{tenant_slug}/custom-api-credentials`. |
| `LOG_LEVEL` | `INFO` | |
| `LOG_FORMAT` | `json` | `json` or `human`. |
| `ENV` | `local` | |

## Local quickstart

```bash
cp .env.example .env   # fill in DATABASE_URL / CREDENTIAL_ENCRYPTION_KEY / ADMIN_API_KEY
make dev                # installs [dev] extras
docker compose -f ../docker-compose.yml up -d db   # or point DATABASE_URL at your own Postgres
make migrate            # alembic upgrade head
make run                # serves on :8000
make test
```

```bash
curl -s -X POST localhost:8000/geneco \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### SIT test data

A known-real account in the `orca-sit` D365/Dataverse org, used for manual
smoke-testing all seven tools end-to-end against the real SIT backends
(both D365 and the custom cxchat API) — not fixture data, and not
guaranteed stable if the SIT org's data changes:

| Field | Value |
|---|---|
| Account number | `GC8030359D` |
| Mobile number | `87654321` |
| Registered email | `serayageneco+test-renewdtoc@gmail.com` |

The custom cxchat API's own base URL/Basic Auth credentials for SIT are
**not** in this file — they're in `.env`'s gitignored reference block
(`CUSTOM_API_BASE_URL`/`CUSTOM_API_USERNAME`/`CUSTOM_API_PASSWORD`, not
read directly by `Settings`); fetch them from there and register them via
stage 1 before testing the custom-API tools locally.

## Adding a tool

1. New file under `app/tools/<name>.py`: a Pydantic input model + an
   `@register("<name>", description=..., input_model=...)` handler that
   takes a `ToolContext` (`app/tools/registry.py`) as its first argument —
   `ctx.session` and `ctx.encryption_key` are all a handler gets; it
   builds whichever credential store it needs from those
   (`CredentialStore` for D365, `CustomApiCredentialStore` for the custom
   API, or a new store class for a new connector kind entirely).
2. Import it in `app/tools/__init__.py`.
3. If it needs a new D365 operation, add a method to `D365Connector` in
   `app/clients/d365_connector.py` (same for `CustomApiClient` and the
   custom API); wrap any new outbound `httpx`/`msal` call and response
   parse the same way `_request`/`_acquire_token` already do, so a real
   failure always raises `ConnectorError` rather than an unhandled
   exception (never a raw 500 to the caller).
4. A genuinely new connector/credential kind (not D365 or the custom API)
   needs its own table in `app/store/tables.py` + Alembic migration, a
   store class mirroring `store/custom_api_credentials.py`, and its own
   `POST`/`GET`/`DELETE /{tenant_slug}/<kind>-credentials` routes in
   `app/protocol/admin_router.py` reusing `_require_admin_key`.

`app/protocol/router.py` never needs to change — `tools/list` and
`tools/call` both read from the registry, and handlers are handed a
store-agnostic `ToolContext` rather than a concrete store.
