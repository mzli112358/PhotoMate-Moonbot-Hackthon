from __future__ import annotations

import importlib.util
import io
import json


def test_json_logging_emits_context_and_redacts_secrets() -> None:
    spec = importlib.util.find_spec("app.photo_agent.observability")
    assert spec is not None, "structured logging module is missing"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    stream = io.StringIO()
    logger = module.configure_json_logging(stream=stream, logger_name="test.photo-agent")

    logger.info(
        "state_transition",
        extra={
            "from_state": "S1",
            "to_state": "S2",
            "session_id": "session-1",
            "api_key": "must-not-leak",
        },
    )
    payload = json.loads(stream.getvalue())

    assert payload["event"] == "state_transition"
    assert payload["from_state"] == "S1"
    assert payload["to_state"] == "S2"
    assert payload["session_id"] == "session-1"
    assert payload["api_key"] == "[REDACTED]"
    assert "must-not-leak" not in stream.getvalue()
