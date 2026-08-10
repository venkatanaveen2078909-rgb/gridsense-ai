"""
Structured JSON logging for GRIDSENSE.
Every log line is a valid JSON object — machine-parseable by Datadog, CloudWatch, ELK.

Usage:
    from app.logging_config import get_logger
    log = get_logger(__name__)
    log.info("cycle complete", extra={"asset_id": "INV-01", "faults": 3})
"""
from __future__ import annotations
import logging
import json
import sys
import os
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    RESERVED = {"message", "timestamp", "level", "logger", "exc_info"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }

        # Extra fields attached via log.info("msg", extra={"k": v})
        for k, v in record.__dict__.items():
            if k.startswith("_") or k in logging.LogRecord.__dict__ or k in self.RESERVED:
                continue
            payload[k] = v

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    return handler


_LOG_LEVEL = os.getenv("GRIDSENSE_LOG_LEVEL", "INFO").upper()

logging.basicConfig(handlers=[_build_handler()], level=_LOG_LEVEL, force=True)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger backed by the JSON formatter."""
    return logging.getLogger(name)
