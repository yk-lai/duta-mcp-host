"""Structlog configuration with stdlib bridge.

Provides a single structured logging pipeline for all log sources:
- structlog-native calls in application code
- stdlib logging calls from uvicorn, httpx, and other libraries

All logs flow through the same processor chain and are emitted as JSON
(production) or human-readable (local dev) to stdout.
"""

import logging
from collections.abc import MutableMapping
from typing import Any, Literal

import structlog

_configured = False

DEFAULT_THIRD_PARTY_LOG_LEVELS: dict[str, str] = {
    "httpx": "WARNING",
    "httpcore": "ERROR",
    "urllib3.connectionpool": "WARNING",
    "asyncio": "WARNING",
    "uvicorn.access": "INFO",
    "uvicorn.error": "ERROR",
}

_JSON_SAFE_TYPES = (str, int, float, bool, type(None), list, dict)

_STDLIB_FIELDS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "getMessage",
        "exc_info", "exc_text", "stack_info", "message", "taskName",
    }
)


class StructlogLoggingHandler(logging.Handler):
    """Forwards all stdlib logging records into the structlog pipeline.

    The handler owns a dedicated structlog logger wrapped around a
    ``PrintLogger``. This output path is fixed at construction time and is
    immune to subsequent ``structlog.configure()`` calls by other modules
    in the process (e.g., when a sub-app configures structlog to use
    ``stdlib.LoggerFactory``). Without this isolation, an emit could
    re-enter stdlib logging and recurse through this same handler until
    the process runs out of memory.
    """

    def __init__(self, logger: Any, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self._logger = logger

    def emit(self, record: logging.LogRecord) -> None:
        logger = self._logger.bind(logger=record.name)

        extra: dict[str, Any] = {
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        for key, value in record.__dict__.items():
            if key not in _STDLIB_FIELDS:
                extra[key] = value

        if record.exc_info:
            extra["exc_info"] = record.exc_info

        log_method = getattr(logger, record.levelname.lower(), logger.info)
        log_method(record.getMessage(), **extra)


def _add_service_context(default_service: str, env: str | None) -> structlog.typing.Processor:
    """Injects service and env into every log entry.

    Honours an existing ``service`` in ``event_dict`` (normally bound via
    ``structlog.contextvars.bind_contextvars`` at the request/task scope) so
    the same process can emit logs tagged for multiple sub-apps. Falls back
    to ``default_service`` when nothing is bound.
    """

    def processor(
        _logger: Any,
        _method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("service", default_service)
        if env:
            event_dict.setdefault("env", env)
        return event_dict

    return processor


def _sanitize_for_json(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Converts non-JSON-serializable values to strings."""
    for key in list(event_dict):
        if not isinstance(event_dict[key], _JSON_SAFE_TYPES):
            event_dict[key] = str(event_dict[key])
    return event_dict


def configure(
    log_level: str = "INFO",
    log_format: Literal["json", "human"] = "json",
    service: str = "duta-mcp-host",
    env: str | None = None,
    third_party_log_levels: dict[str, str] | None = None,
) -> None:
    """Configure structured logging. Safe to call multiple times."""
    global _configured

    level = getattr(logging, log_level.upper(), logging.INFO)

    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_service_context(service, env),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer("message"),
    ]

    if log_format == "json":
        processors.append(_sanitize_for_json)
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    bridge_logger = structlog.wrap_logger(
        structlog.PrintLogger(),
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    bridge = StructlogLoggingHandler(bridge_logger, level=level)
    root_logger.addHandler(bridge)
    root_logger.setLevel(level)

    effective_levels = {**DEFAULT_THIRD_PARTY_LOG_LEVELS, **(third_party_log_levels or {})}
    for logger_name, logger_level in effective_levels.items():
        lib_logger = logging.getLogger(logger_name)
        lib_logger.setLevel(getattr(logging, logger_level.upper(), logging.INFO))
        lib_logger.propagate = True

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    _configured = True


def is_configured() -> bool:
    return _configured
