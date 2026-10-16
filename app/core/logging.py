"""Structured JSON and text logging configuration with Request-ID correlation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from flask import Flask, g, has_request_context, request


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with HTTP request correlation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if has_request_context():
            payload["request_id"] = getattr(g, "request_id", None)
            payload["method"] = request.method
            payload["path"] = request.path
            payload["remote_addr"] = request.remote_addr

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging(app: Flask) -> None:
    """Configure application logging level and formatter (text or structured JSON)."""
    log_level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    app.logger.setLevel(log_level)

    log_format = str(app.config.get("LOG_FORMAT", "text")).lower()
    if log_format == "json":
        for handler in app.logger.handlers:
            handler.setFormatter(StructuredJSONFormatter())
