from __future__ import annotations

from argparse import Namespace

import pytest

from app.photo_agent import cli
from app.photo_agent.runtime import RuntimeConfig


@pytest.mark.asyncio
async def test_local_real_cli_prints_opened_device_names(monkeypatch, capsys) -> None:
    class Runtime:
        device_info = {
            "camera": "camera:0 (AVFoundation)",
            "microphone": "MacBook microphone",
            "speaker": "Bose headphones",
        }

    runtime = Runtime()
    called = False

    async def fake_run_local(config, opened_runtime, *, serve_photos):
        nonlocal called
        called = opened_runtime is runtime

    monkeypatch.setattr(
        cli,
        "load_runtime_config",
        lambda mode: RuntimeConfig(mode=mode, api_key="test-key"),
    )
    monkeypatch.setattr(cli, "build_local_runtime", lambda config: runtime)
    monkeypatch.setattr(cli, "_run_local", fake_run_local)

    code = await cli.async_main(Namespace(mode="local-real", no_photo_server=True))

    output = capsys.readouterr().out
    assert code == 0
    assert called is True
    assert "MacBook microphone" in output
    assert "Bose headphones" in output


@pytest.mark.asyncio
async def test_local_real_cli_reports_preflight_failure_without_traceback(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "load_runtime_config",
        lambda mode: RuntimeConfig(mode=mode, api_key="test-key"),
    )
    monkeypatch.setattr(
        cli,
        "build_local_runtime",
        lambda config: (_ for _ in ()).throw(RuntimeError("camera permission denied")),
    )

    code = await cli.async_main(Namespace(mode="local-real", no_photo_server=True))

    output = capsys.readouterr().out
    assert code == 4
    assert "camera permission denied" in output
    assert '"missing_real_dependencies"' in output
