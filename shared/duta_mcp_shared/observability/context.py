"""Per-request logging context using structlog contextvars.

Context is async-safe: each asyncio Task gets its own copy via Python's
contextvars module. Bound values are automatically merged into every log
entry by the merge_contextvars processor in the structlog pipeline.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog

REQUEST_ID = "request_id"


def bind_context(**kwargs: Any) -> None:
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()


def get_current_context() -> dict[str, Any]:
    return structlog.contextvars.get_contextvars()


@asynccontextmanager
async def log_context(context: dict[str, Any]) -> AsyncIterator[None]:
    """Bind context variables for the duration of an async block.

    Uses selective unbind (not clear_all) so that outer context managers
    are unaffected when an inner one exits. This makes nesting safe.
    """
    structlog.contextvars.bind_contextvars(**context)
    try:
        yield
    finally:
        structlog.contextvars.unbind_contextvars(*context.keys())
