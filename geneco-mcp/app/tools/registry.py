"""Tool registry: name -> ToolSpec.

Open/closed by design (mirrors sc-chatbot's ``tools/`` registry pattern in
chatbot-poc-projects): adding a new tool is a new handler module +
``@register(...)`` — nothing here or in ``protocol/router.py`` needs to
change.

Handlers receive a ``ToolContext`` rather than a concrete store: the D365
tools build their own ``CredentialStore`` from ``ctx.session`` and
``check_fee_waiver_status`` builds its own ``CustomApiCredentialStore`` the
same way. Keeping the shared contract store-agnostic is what lets a second
credential kind (the custom fee-waiver API) arrive as a new tool file
without editing the dispatcher in ``protocol/router.py``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Per-call dependencies handed to every tool handler: the request's DB
    session and the encryption key needed to decrypt whichever credential
    kind the tool actually uses."""

    session: AsyncSession
    encryption_key: str


ToolHandler = Callable[[ToolContext, str, BaseModel], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler


_REGISTRY: dict[str, ToolSpec] = {}


def register(
    name: str, *, description: str, input_model: type[BaseModel]
) -> Callable[[ToolHandler], ToolHandler]:
    def decorator(fn: ToolHandler) -> ToolHandler:
        if name in _REGISTRY:
            raise ValueError(f"tool {name!r} already registered")
        _REGISTRY[name] = ToolSpec(
            name=name, description=description, input_model=input_model, handler=fn
        )
        return fn

    return decorator


def all_tools() -> tuple[ToolSpec, ...]:
    return tuple(_REGISTRY.values())


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)
