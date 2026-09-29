"""Structured logging configuration with contextual request and correlation IDs."""

import contextvars
import logging
import sys
from typing import Any, Dict

# Context variable to track the current HTTP request ID across async tasks
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class ContextualFormatter(logging.Formatter):
    """Custom formatter that automatically injects request_id into every log record."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get()
        return super().format(record)


def setup_logging(debug: bool = False) -> None:
    """Configure root logger with structured timestamp and request ID tags."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s | %(levelname)-7s | [%(request_id)s] %(name)s: %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(ContextualFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Remove existing handlers to avoid duplicate log output
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve named logger with context."""
    return logging.getLogger(name)
