from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

_STANDARD_FIELDS = set(logging.makeLogRecord({}).__dict__)
_SECRET_MARKERS = ("api_key", "apikey", "token", "secret", "password", "authorization")


def _redact(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {nested_key: _redact(str(nested_key), nested_value) for nested_key, nested_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(key, item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and key not in {"message", "asctime"}:
                payload[key] = _redact(key, value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_json_logging(
    *,
    stream: TextIO | None = None,
    logger_name: str = "photomate",
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
