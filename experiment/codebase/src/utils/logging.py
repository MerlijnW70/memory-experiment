"""Structured logging utilities.

Provides a thin wrapper around standard logging with JSON-structured output
and request-context enrichment.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from src.config import APP_NAME, LOG_LEVEL


_logger: Optional[logging.Logger] = None
_log_buffer: list[dict[str, Any]] = []


def get_logger() -> logging.Logger:
    """Return the application logger, creating it on first call."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(APP_NAME)
        _logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            _logger.addHandler(handler)
    return _logger


def log_event(
    event: str,
    level: str = "info",
    **extra: Any,
) -> dict[str, Any]:
    """Log a structured event.

    The event is both emitted via the standard logger and appended to an
    internal buffer that can be inspected in tests.

    Args:
        event: Short description of what happened.
        level: Log level as a lowercase string.
        **extra: Additional key-value pairs to include in the log entry.

    Returns:
        The structured log entry dict.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": APP_NAME,
        "event": event,
        "level": level,
        **extra,
    }
    _log_buffer.append(entry)

    logger = get_logger()
    log_fn = getattr(logger, level, logger.info)
    log_fn(json.dumps(entry, default=str))

    return entry


def get_log_buffer() -> list[dict[str, Any]]:
    """Return the internal log buffer. Useful for test assertions."""
    return list(_log_buffer)


def clear_log_buffer() -> None:
    """Clear the internal log buffer. Called in test teardown."""
    _log_buffer.clear()
