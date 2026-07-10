from __future__ import annotations

import subprocess
import sys
from argparse import Namespace

import pytest


def test_manual_script_runs_directly_from_repo_root() -> None:
    result = subprocess.run(
        [sys.executable, "manual/photo_agent/run_state.py", "--state", "S3", "--mode", "mock"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"ok": true' in result.stdout


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

    class Audio:
        def __init__(self, *args, **kwargs):
            pass

        def read_chunk(self):
            return b"pcm"

        def __call__(self, pcm):
            pass

        def close(self):
            pass

    monkeypatch.setattr(device_smoke, "OpenCVCamera", Camera)
    monkeypatch.setattr(device_smoke, "PyAudioMicrophone", Audio)
    monkeypatch.setattr(device_smoke, "PyAudioSpeaker", Audio)
    monkeypatch.setattr(device_smoke, "list_audio_devices", lambda: [])

    code = await device_smoke.run(Namespace(camera=0, microphone=None, speaker=None))

    assert code == 3
    assert "camera 0 cannot be opened" in capsys.readouterr().out
