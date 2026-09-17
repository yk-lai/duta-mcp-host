"""MCP JSON-RPC endpoint: ``POST /{tenant_slug}``.

Speaks exactly the subset duta-ilmu's orchestrator MCP client uses
(``services/orchestrator/src/orchestrator/tools/mcp.py`` in the duta-ilmu
repo): ``initialize`` -> ``notifications/initialized`` -> ``tools/list`` /
``tools/call``, JSON-RPC 2.0 over a single POST — that client only POSTs
and never opens a separate SSE stream, so no bidirectional Streamable-HTTP
support is needed here.

That client sends no auth headers when calling a tenant's MCP server (this
is a platform-wide convention in duta-ilmu, not something introduced
here — see ``control_plane/aggregation.py``: "Our MCP registrations never
carry auth headers"), so this endpoint is intentionally unauthenticated at
the transport level. The data-level gate is unchanged: every tool still
requires a correct ``account_id`` + ``mobile_number`` match before
returning anything, via integration-hub.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker

from geneco_mcp.config import Settings
from geneco_mcp.protocol.models import JsonRpcId, rpc_error, rpc_result
from geneco_mcp.tools import all_tools, get_tool
from geneco_mcp.tools.registry import ToolContext

log = structlog.get_logger()

PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "geneco-mcp", "version": "0.1.0"}
SESSION_HEADER = "Mcp-Session-Id"

router = APIRouter()


def _tool_defs() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "inputSchema": spec.input_model.model_json_schema(),
        }
        for spec in all_tools()
    ]


async def _handle_tools_call(
    params: dict[str, Any],
    *,
    tenant_slug: str,
    settings: Settings,
    session_factory: async_sessionmaker,
) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    spec = get_tool(name) if isinstance(name, str) else None
    if spec is None:
        return {"content": [{"type": "text", "text": f"unknown tool: {name!r}"}], "isError": True}
    try:
        parsed_args = spec.input_model.model_validate(arguments)
    except ValidationError as exc:
        return {
            "content": [{"type": "text", "text": f"invalid arguments for {name}: {exc}"}],
            "isError": True,
        }
    async with session_factory() as session:
        ctx = ToolContext(session=session, encryption_key=settings.credential_encryption_key)
        result = await spec.handler(ctx, tenant_slug, parsed_args)
    return {
        "content": [{"type": "text", "text": json.dumps(result)}],
        "structuredContent": result,
        "isError": bool(result.get("error")),
    }


@router.post("/{tenant_slug}")
async def mcp_endpoint(tenant_slug: str, request: Request) -> Response:
    settings: Settings = request.app.state.settings
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(rpc_error(None, -32700, "parse error"))

    if not isinstance(payload, dict):
        return JSONResponse(rpc_error(None, -32600, "invalid request"))

    request_id: JsonRpcId = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
        return JSONResponse(
            rpc_result(request_id, result), headers={SESSION_HEADER: uuid.uuid4().hex}
        )

    if method == "notifications/initialized":
        # Notification: no id, no response body expected.
        return Response(status_code=202)

    if method == "tools/list":
        return JSONResponse(rpc_result(request_id, {"tools": _tool_defs()}))

    if method == "tools/call":
        result = await _handle_tools_call(
            params,
            tenant_slug=tenant_slug,
            settings=settings,
            session_factory=request.app.state.session_factory,
        )
        return JSONResponse(rpc_result(request_id, result))

    log.info("mcp.unknown_method", method=method, tenant_slug=tenant_slug)
    return JSONResponse(rpc_error(request_id, -32601, f"method not found: {method}"))
