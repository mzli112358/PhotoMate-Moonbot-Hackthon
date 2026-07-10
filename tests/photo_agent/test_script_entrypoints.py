from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace

import pytest

from app.photo_agent.runtime import RuntimeConfig


def test_manual_script_runs_directly_from_repo_root() -> None:
    result = subprocess.run(
        [sys.executable, "manual/photo_agent/run_state.py", "--state", "S3", "--mode", "mock"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"ok": true' in result.stdout


def test_mock_cli_emits_structured_runtime_events() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.photo_agent.cli", "--mode", "mock"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"event": "state_transition"' in result.stdout
    assert '"event": "capture_result"' in result.stdout
    assert '"event": "delivery_result"' in result.stdout
    assert '"event": "resource_release"' in result.stdout


def test_omni_smoke_reports_missing_key_without_import_error(monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    result = subprocess.run(
        [sys.executable, "scripts/photo_agent/omni_smoke.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "DASHSCOPE_API_KEY missing" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


@pytest.mark.asyncio
async def test_device_smoke_reports_camera_permission_failure_without_raising(monkeypatch, capsys) -> None:
    from scripts.photo_agent import device_smoke

    class Camera:
        device_name = "camera:0"

        def __init__(self, *args, **kwargs):
            pass

        async def get_frame(self):
            raise RuntimeError("camera 0 cannot be opened")

        async def close(self):
            pass

    class Microphone:
        reads = 0
        device_name = "fake microphone"

        def __init__(self, *args, **kwargs):
            pass

        def read_chunk(self):
            self.reads += 1
            return b"pcm"

        def close(self):
            pass

    class Speaker:
        writes = 0
        device_name = "fake speaker"

        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, pcm):
            self.writes += 1

        def close(self):
            pass

    microphone = Microphone()
    speaker = Speaker()

    monkeypatch.setattr(device_smoke, "OpenCVCamera", Camera)
    monkeypatch.setattr(device_smoke, "PyAudioMicrophone", lambda *args, **kwargs: microphone)
    monkeypatch.setattr(device_smoke, "PyAudioSpeaker", lambda *args, **kwargs: speaker)
    monkeypatch.setattr(device_smoke, "list_audio_devices", lambda: [])

    code = await device_smoke.run(Namespace(camera=0, microphone=None, speaker=None))

    assert code == 3
    report = json.loads(capsys.readouterr().out)
    assert report["camera"]["error"] == "camera 0 cannot be opened"
    assert report["microphone"]["device"] == "fake microphone"
    assert report["speaker"]["device"] == "fake speaker"
    assert microphone.reads == 1
    assert speaker.writes == 1


@pytest.mark.asyncio
async def test_local_real_manual_entry_runs_only_requested_state(monkeypatch, capsys) -> None:
    from manual.photo_agent import run_state

    class Runtime:
        requested: str | None = None
        device_info = {
            "camera": "camera:0 (AVFoundation)",
            "microphone": "MacBook microphone",
            "speaker": "Bose headphones",
        }

        async def run_manual_state(self, state: str):
            self.requested = state
            return {"ok": True, "tested_state": state, "result_state": "S4"}

    runtime = Runtime()
    monkeypatch.setattr(run_state, "build_local_runtime", lambda config: runtime)
    monkeypatch.setattr(run_state, "load_runtime_config", lambda mode: RuntimeConfig(mode=mode, api_key="x"))

    code = await run_state.run(Namespace(state="S3", mode="local-real"))

    output = capsys.readouterr().out
    assert code == 0
    assert runtime.requested == "S3"
    assert "正常预期现象" in output
    assert "MacBook microphone" in output


@pytest.mark.asyncio
async def test_local_real_manual_entry_reports_preflight_failure(monkeypatch, capsys) -> None:
    from manual.photo_agent import run_state

    monkeypatch.setattr(
        run_state,
        "load_runtime_config",
        lambda mode: RuntimeConfig(mode=mode, api_key="x"),
    )
    monkeypatch.setattr(
        run_state,
        "build_local_runtime",
        lambda config: (_ for _ in ()).throw(RuntimeError("camera permission denied")),
    )

    code = await run_state.run(Namespace(state="S1", mode="local-real"))

    output = capsys.readouterr().out
    assert code == 4
    assert "camera permission denied" in output
    assert '"missing_real_dependencies"' in output


@pytest.mark.asyncio
async def test_s6_manual_entry_starts_photo_server(monkeypatch) -> None:
    from manual.photo_agent import run_state

    class Runtime:
        device_info = {"camera": "cam", "microphone": "mic", "speaker": "speaker"}

        async def run_manual_state(self, state: str):
            return {"ok": True, "tested_state": state, "result_state": "S0", "photo_url": "http://local/p"}

    class Server:
        started = False
        stopped = False

        def __init__(self, base_url: str):
            self.base_url = base_url

        async def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

    made: list[Server] = []
    monkeypatch.setattr(
        run_state,
        "load_runtime_config",
        lambda mode: RuntimeConfig(mode=mode, api_key="x"),
    )
    monkeypatch.setattr(run_state, "build_local_runtime", lambda config: Runtime())
    monkeypatch.setattr(
        run_state,
        "PhotoApiServer",
        lambda base_url: made.append(Server(base_url)) or made[-1],
    )

    code = await run_state.run(Namespace(state="S6", mode="local-real"))

    assert code == 0
    assert made[0].started is True
    assert made[0].stopped is True
