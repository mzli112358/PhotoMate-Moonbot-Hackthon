from __future__ import annotations

import importlib.util

import pytest


@pytest.mark.asyncio
async def test_system_fallback_uses_local_speech_command() -> None:
    spec = importlib.util.find_spec("app.photo_agent.fallback")
    assert spec is not None, "local fallback module is missing"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs) -> None:
        calls.append(command)

    notifier = module.SystemFallbackNotifier(command="/usr/bin/say", command_runner=runner)
    await notifier.notify("网络暂时不可用，请稍后再试")

    assert calls == [["/usr/bin/say", "网络暂时不可用，请稍后再试"]]
