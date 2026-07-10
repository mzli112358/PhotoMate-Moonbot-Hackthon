from __future__ import annotations

import importlib.util


def test_photo_agent_models_module_exists() -> None:
    spec = importlib.util.find_spec("app.photo_agent.models")

    assert spec is not None, "S1-S6 data contract module is not implemented"


def test_photo_agent_runtime_modules_exist() -> None:
    required = (
        "app.photo_agent.interfaces",
        "app.photo_agent.mocks",
        "app.photo_agent.fsm",
        "app.photo_agent.camera",
        "app.photo_agent.delivery",
        "app.photo_agent.omni",
        "app.photo_agent.runtime",
    )

    missing = [name for name in required if importlib.util.find_spec(name) is None]
    assert missing == [], f"photo agent modules are not implemented: {missing}"
