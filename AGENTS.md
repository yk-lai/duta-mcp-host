# AGENTS.md

Project-specific guidance for Codex working in this repo. Adapted from
`chatbot-poc-projects/AGENTS.md` for an MCP-hosting service rather than a
chat application — the layering names differ, the principles don't.

## Repo layout

```
duta-mcp-host/
├── gateway.py              # Mounts geneco-mcp (and future MCP hosts) behind one uvicorn
├── shared/                 # duta_mcp_shared — structlog + per-request context
└── geneco-mcp/                # MCP server for account inquiry / create case / case inquiry
    └── app/
        ├── protocol/        # ← MCP wire boundary. JSON-RPC in/out, tenant_slug from the URL.
        ├── tools/           # Tool definitions + handlers (LLM-facing contract, one file each)
        └── clients/         # ← Transport layer. HTTP adapter to duta-ilmu's integration-hub.
```

## Coding principles

### SOLID — applied concretely in this repo

- **Single responsibility.** `IntegrationHubClient` only does HTTP.
  `protocol/router.py` only speaks JSON-RPC. Tool handlers only adapt MCP
  arguments to a client call.
- **Open–closed.** Adding a tool = new file under `tools/` + `@register`;
  no edits to `protocol/router.py`'s dispatcher. Adding an integration-hub
  operation = new method on `IntegrationHubClient`; no edits to `_post`.
- **Liskov.** Prefer composition over inheritance — there is no inheritance
  hierarchy here worth mentioning, and that's the point; don't introduce
  one for "semantic tagging".
- **Interface segregation.** `IntegrationHubClient` exposes one method per
  tool operation, not a generic `call(endpoint, body)` — callers state
  intent, not wire shape.
- **Dependency inversion.** `IntegrationHubClient` is constructed from
  `Settings` and passed into tool handlers as an argument, never reached
  for as a module-level singleton — this is what makes `respx`-mocked
  tests possible without monkeypatching internals.

### Type hygiene

- **No `Any`** at typed boundaries. MCP arguments are validated into a
  Pydantic input model (one per tool) before a handler ever sees them.
- **Prefer Pydantic models over bare dicts at boundaries** — every tool's
  input is a `BaseModel`; JSON-RPC envelopes are built via the typed
  helpers in `protocol/models.py`, not hand-assembled dicts scattered
  across the router.
- Integration-hub's own response dict is passed through as-is once
  received (it's already a `dict[str, Any]` shaped by an internal
  contract this project doesn't own) — don't re-wrap it in a redundant
  model just to satisfy a type checker.

### YAGNI

- This service hosts exactly the tools duta-ilmu's orchestrator actually
  calls today. Don't add placeholder tools, config knobs, or a "generic"
  MCP-server framework in anticipation of a second consumer that hasn't
  arrived.
- No Streamable-HTTP SSE duplex support, no session persistence — the one
  MCP client this project talks to (duta-ilmu's orchestrator) only POSTs
  and never opens a separate stream, and every tool is stateless per call.
  Build the framework this client actually needs, not the full spec.

### Async-all-the-way

- FastAPI endpoints, tool handlers, and `IntegrationHubClient` methods are
  all `async def`. Use `httpx.AsyncClient` for the integration-hub calls —
  never a sync HTTP call inside an `async def` route.

### Honest errors, never fabricated data

This is a hard constraint inherited from the tools this project proxies to
(duta-ilmu's own decision, not just a style preference): a transport
failure or an unconfigured backend must come back as
`{"error": "<message the model can relay to the customer>"}`, never a
mocked/fabricated result. `IntegrationHubClient._post` is the one place
that boundary is enforced — don't add a second error-shaping path
elsewhere.

## Test expectations

- **`pytest` + `respx`** for HTTP mocks against `IntegrationHubClient` —
  no live network calls in tests.
- **`asyncio_mode = "auto"`** (set in each sub-app's `pyproject.toml`) — no
  `@pytest.mark.asyncio` needed on async test functions.
- Cover the full JSON-RPC sequence (`initialize` → `tools/list` →
  `tools/call`) at least once per tool, plus the honest-error path when
  integration-hub is unreachable or answers `{"error": ...}`.

## PR hygiene

- One PR = one concern.
- Commit messages: `<type>(<scope>): <subject>` — e.g. `feat(geneco-mcp):
  add create_support_case tool`.
- Never skip pre-commit hooks or force-push shared branches.
