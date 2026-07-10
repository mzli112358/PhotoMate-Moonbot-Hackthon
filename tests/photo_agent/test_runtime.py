from __future__ import annotations

import json
import asyncio

import pytest

from app.photo_agent.dispatcher import FunctionCallDispatcher
from app.photo_agent.fsm import FSMConfig, PhotoAgentFSM
from app.photo_agent.mocks import MockCamera, MockDelivery, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import CaptureResult, DeliveryResult, QualityResult, State, ToolCall, WakeSignal
from app.photo_agent.runtime import (
    PhotoAgentRuntime,
    RuntimeConfig,
    build_local_runtime,
    build_self_check,
    run_mock_demo,
    run_mock_state,
)


def test_startup_self_check_redacts_api_key() -> None:
    config = RuntimeConfig(
        mode="local-real",
        model="qwen3.5-omni-flash-2026-03-15",
        workspace_host="workspace.cn-beijing.maas.aliyuncs.com",
        api_key="super-secret-value",
    )

    report = build_self_check(config)
    serialized = json.dumps(report)

    assert report["api_key_present"] is True
    assert "super-secret-value" not in serialized
    assert report["adapters"]["omni"] == "real"


def test_local_runtime_fails_before_opening_devices_when_key_missing() -> None:
    opened = False

    def forbidden(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("device should not open")

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        build_local_runtime(
            RuntimeConfig(mode="local-real", api_key=""),
            camera_factory=forbidden,
            microphone_factory=forbidden,
            speaker_factory=forbidden,
        )

    assert opened is False


def test_local_runtime_releases_camera_when_audio_open_fails() -> None:
    class Camera:
        closed = False

        def __init__(self, *args, **kwargs):
            pass

        def open(self):
            pass

        def close_sync(self):
            self.closed = True

    camera = Camera()

    def camera_factory(*args, **kwargs):
        return camera

    def failing_speaker(*args, **kwargs):
        raise RuntimeError("speaker failed")

    with pytest.raises(RuntimeError, match="speaker failed"):
        build_local_runtime(
            RuntimeConfig(mode="local-real", api_key="test-key"),
            camera_factory=camera_factory,
            microphone_factory=lambda **kwargs: object(),
            speaker_factory=failing_speaker,
        )

    assert camera.closed is True


@pytest.mark.asyncio
async def test_mock_demo_runs_s1_to_s6_and_returns_photo_url() -> None:
    result = await run_mock_demo(RuntimeConfig(mode="mock"))

    assert result.ok is True
    assert result.photo_url.endswith("/api/photos/mock-photo")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected"),
    [("S1", "S2"), ("S2", "S3"), ("S3", "S4"), ("S4", "S5"), ("S5", "S6"), ("S6", "S0")],
)
async def test_each_mock_state_has_an_isolated_acceptance_path(state: str, expected: str) -> None:
    result = await run_mock_state(RuntimeConfig(mode="mock"), state)

    assert result["ok"] is True
    assert result["result_state"] == expected


@pytest.mark.asyncio
async def test_dispatcher_executes_capture_and_rejects_unknown(tmp_path) -> None:
    capture = CaptureResult("p1", tmp_path / "p1.jpg", True, frame=None)
    capture.path.write_bytes(b"jpeg")
    delivery_result = DeliveryResult("p1", "http://local/api/photos/p1", True)
    omni = MockOmni()
    delivery = MockDelivery(results=[delivery_result])
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([WakeSignal(False, 0, False)]),
        omni=omni,
        camera=MockCamera(captures=[capture]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=delivery,
        config=FSMConfig(wake_consecutive_frames=1),
    )
    fsm.context.state = State.SHOOT
    dispatcher = FunctionCallDispatcher(fsm)

    captured = await dispatcher.dispatch(ToolCall("capture_photo", {"mode": "photo"}, "c1"))
    unknown = await dispatcher.dispatch(ToolCall("launch_missile", {}, "c2"))

    assert captured["ok"] is True
    assert captured["photo_id"] == "p1"
    assert unknown == {"ok": False, "error": "unsupported_tool:launch_missile"}


@pytest.mark.asyncio
async def test_runtime_routes_server_events_to_fsm_and_tool_result(tmp_path) -> None:
    capture = CaptureResult("p1", tmp_path / "p1.jpg", True, frame=None)
    capture.path.write_bytes(b"jpeg")
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[capture]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p1", "http://local/api/photos/p1", True)]),
    )
    runtime = PhotoAgentRuntime(fsm)
    fsm.context.state = State.POSE_GUIDANCE

    await runtime.handle_event({"type": "speech_started"})
    await runtime.handle_event(
        {"type": "tool_call", "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "c1")}
    )

    assert fsm.context.state is State.REVIEW
    assert omni.count("submit_tool_result") == 1


@pytest.mark.asyncio
async def test_user_ready_waits_for_omni_tool_call_before_capture(tmp_path) -> None:
    capture = CaptureResult("p1", tmp_path / "p1.jpg", True, frame=None)
    capture.path.write_bytes(b"jpeg")
    camera = MockCamera(captures=[capture])
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=MockOmni(),
        camera=camera,
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p1", "http://local/api/photos/p1", True)]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event({"type": "user_text", "text": "拍吧"})

    assert fsm.context.state is State.SHOOT
    assert camera.count("capture") == 0


@pytest.mark.asyncio
async def test_audio_loop_waits_until_omni_session_exists() -> None:
    class Microphone:
        reads = 0

        def read_chunk(self) -> bytes:
            self.reads += 1
            return b"pcm"

    microphone = Microphone()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=MockOmni(),
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    runtime = PhotoAgentRuntime(fsm, microphone=microphone)

    task = asyncio.create_task(runtime._audio_loop())
    await asyncio.sleep(0.02)
    runtime.stop()
    await task

    assert microphone.reads == 0
