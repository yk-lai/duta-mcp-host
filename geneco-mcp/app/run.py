"""Standalone dev entrypoint: ``python -m geneco_mcp.run``.

Configures the shared structlog pipeline before uvicorn starts so
``uvicorn.access``/``uvicorn.error`` route through it from the first
request (mirrors chatbot-poc-projects/sc-chatbot's ``run.py``).
"""

from __future__ import annotations

import uvicorn
from duta_mcp_shared.observability import configure_logging

from geneco_mcp.config import Settings

if __name__ == "__main__":
    settings = Settings()
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,  # type: ignore[arg-type]
        service="geneco-mcp",
        env=settings.env,
    )
    uvicorn.run(
        "geneco_mcp.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,
        reload=settings.env == "local",
    )
