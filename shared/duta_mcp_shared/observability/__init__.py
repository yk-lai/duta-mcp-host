"""Observability primitives shared across duta-mcp-host's sub-apps.

At process start (in the top-level app's lifespan):

    from duta_mcp_shared.observability import configure_logging
    configure_logging(log_level=..., log_format=..., service=..., env=...)

In application code:

    import structlog
    from duta_mcp_shared.observability import log_context

    logger = structlog.get_logger()

    async with log_context({"tenant_slug": tenant_slug}):
        logger.info("mcp tool call")
"""

from duta_mcp_shared.observability.context import (
    REQUEST_ID,
    bind_context,
    clear_context,
    get_current_context,
    log_context,
    unbind_context,
)
from duta_mcp_shared.observability.logging import configure as configure_logging
from duta_mcp_shared.observability.logging import is_configured as is_logging_configured

__all__ = [
    "configure_logging",
    "is_logging_configured",
    "log_context",
    "bind_context",
    "unbind_context",
    "clear_context",
    "get_current_context",
    "REQUEST_ID",
]
