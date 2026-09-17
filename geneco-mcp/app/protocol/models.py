"""JSON-RPC 2.0 envelope helpers.

Deliberately not a strict request model with validation errors surfaced as
HTTP 4xx: a malformed request should come back as a JSON-RPC error object
(``rpc_error``) so a non-conforming client still gets a body it can parse,
matching the "honest error the model/caller can read" convention used
throughout duta-ilmu's tool endpoints.
"""

from __future__ import annotations

from typing import Any

JsonRpcId = int | str | None


def rpc_result(request_id: JsonRpcId, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: JsonRpcId, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
