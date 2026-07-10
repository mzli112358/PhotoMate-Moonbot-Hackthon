from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.photo_agent.prompts import PromptRegistry
from app.photo_agent.runtime import RuntimeConfig
from app.photo_agent.test_controller import (
    EventHub,
    PhotoAgentTestController,
    TestAlreadyRunningError,
    TestRunStore,
    annotate_preview,
)


class FakeCamera:
    def latest_frame(self):
        return np.full((120, 160, 3), 80, dtype=np.uint8)


class FakeRuntime:
    def __init__(self, gate: asyncio.Event, *, result: dict | None = None) -> None:
        self.gate = gate
        self.result = result or {"ok": True, "tested_state": "S2", "result_state": "S3"}
        self.device_info = {"camera": "fake cam", "microphone": "fake mic", "speaker": "fake speaker"}
        self.fsm = SimpleNamespace(
            context=SimpleNamespace(
                state=SimpleNamespace(value="S2"),
                session_id="session-1",
                photo_id=None,
                photo_url=None,
            ),
            camera=FakeCamera(),
        )
        self.active_prompt_version = "prompt-v1"
        self.cleaned = False

    async def run_manual_state(self, state: str):
        try:
            await self.gate.wait()
            return {**self.result, "tested_state": state}
        finally:
            self.cleaned = True


def make_controller(tmp_path: Path, runtime: FakeRuntime) -> PhotoAgentTestController:
    prompts = PromptRegistry(tmp_path / "prompts.yaml", tmp_path / "history")
    runs = TestRunStore(tmp_path / "runs.json", max_runs=2)
    return PhotoAgentTestController(
        prompt_registry=prompts,
        run_store=runs,
        config_loader=lambda **kwargs: RuntimeConfig(mode="local-real", api_key="in-memory-key"),
        runtime_builder=lambda config, prompt_source: runtime,
    )


@pytest.mark.asyncio
async def test_controller_allows_only_one_active_module_and_records_completion(tmp_path: Path) -> None:
    gate = asyncio.Event()
    runtime = FakeRuntime(gate)
    controller = make_controller(tmp_path, runtime)

    started = await controller.start("S2", microphone_index=1, speaker_index=4)

    assert started["active"] is True
    assert started["selected_state"] == "S2"
    assert started["devices"]["camera"] == "fake cam"
    with pytest.raises(TestAlreadyRunningError):
        await controller.start("S3")

    gate.set()
    await controller.wait_until_idle(timeout=1)

    status = controller.status()
    assert status["active"] is False
    assert status["last_result"]["result_state"] == "S3"
    assert runtime.cleaned is True
    assert TestRunStore(tmp_path / "runs.json").list()[0]["state"] == "S2"


@pytest.mark.asyncio
async def test_stop_cancels_active_module_and_releases_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime(asyncio.Event())
    controller = make_controller(tmp_path, runtime)
    await controller.start("S3")

    stopped = await controller.stop()

    assert stopped["active"] is False
    assert runtime.cleaned is True
    assert controller.status()["stop_reason"] == "operator_stop"


@pytest.mark.asyncio
async def test_event_hub_replays_backlog_then_streams_new_events() -> None:
    hub = EventHub(max_events=3)
    await hub.publish({"type": "state", "value": "S1"})
    await hub.publish({"type": "state", "value": "S2"})
    stream = hub.subscribe(after=1)

    replay = await anext(stream)
    await hub.publish({"type": "quality", "ok": True})
    live = await anext(stream)
    await stream.aclose()

    assert replay["seq"] == 2
    assert replay["value"] == "S2"
    assert live["seq"] == 3
    assert live["type"] == "quality"


def test_run_store_is_persistent_and_bounded(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"
    store = TestRunStore(path, max_runs=2)
    store.add({"state": "S1", "ok": True})
    store.add({"state": "S2", "ok": True})
    store.add({"state": "S3", "ok": False})

    assert [item["state"] for item in TestRunStore(path, max_runs=2).list()] == ["S3", "S2"]
    assert len(json.loads(path.read_text(encoding="utf-8"))) == 2


def test_preview_annotation_draws_face_state_and_quality() -> None:
    frame = np.zeros((120, 180, 3), dtype=np.uint8)

    annotated = annotate_preview(
        frame, faces=[(20, 25, 50, 60)], state="S3", quality={"ok": True}
    )

    assert annotated.shape == frame.shape
    assert annotated[25, 20].any()
    assert annotated.sum() > frame.sum()


@pytest.mark.asyncio
async def test_preview_jpeg_uses_active_runtime_camera(tmp_path: Path) -> None:
    runtime = FakeRuntime(asyncio.Event())
    controller = make_controller(tmp_path, runtime)
    await controller.start("S2")

    jpeg = await controller.preview_jpeg()
    await controller.stop()

    assert jpeg.startswith(b"\xff\xd8")
    assert jpeg.endswith(b"\xff\xd9")


@pytest.mark.asyncio
async def test_controller_reports_saved_and_active_prompt_versions(tmp_path: Path) -> None:
    runtime = FakeRuntime(asyncio.Event())
    controller = make_controller(tmp_path, runtime)
    await controller.start("S2")
    current = controller.prompt_registry.snapshot()
    saved = controller.prompt_registry.save(
        {"action.S2.ask_initial": "new question"}, expected_version=current.version
    )

    status = controller.status()
    await controller.stop()

    assert status["saved_prompt_version"] == saved.version
    assert status["active_prompt_version"] == "prompt-v1"


@pytest.mark.asyncio
async def test_controller_streams_runtime_logs_and_tracks_quality(tmp_path: Path) -> None:
    runtime = FakeRuntime(asyncio.Event())
    controller = make_controller(tmp_path, runtime)
    await controller.start("S4")

    logging.getLogger("photomate.photo_agent").warning(
        "quality_result",
        extra={"photo_id": "photo-1", "ok": False, "reason": "blur", "api_key": "secret"},
    )
    await asyncio.sleep(0.02)

    stream = controller.events.subscribe(after=1)
    event = await anext(stream)
    await stream.aclose()
    status = controller.status()
    await controller.stop()

    assert event["type"] == "runtime_log"
    assert event["event"] == "quality_result"
    assert event["api_key"] == "[REDACTED]"
    assert status["last_quality"] == {"photo_id": "photo-1", "ok": False, "reason": "blur"}
