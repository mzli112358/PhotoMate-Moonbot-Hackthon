from __future__ import annotations

import json
import asyncio
import inspect
from collections import deque

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
        model="qwen3.5-omni-flash-realtime",
        workspace_host="workspace.cn-beijing.maas.aliyuncs.com",
        api_key="super-secret-value",
    )

    assert "device_info" in inspect.signature(build_self_check).parameters
    report = build_self_check(
        config,
        device_info={
            "camera": "camera:0 (AVFoundation)",
            "microphone": "MacBook microphone",
            "speaker": "Bose headphones",
        },
    )
    serialized = json.dumps(report)

    assert report["api_key_present"] is True
    assert "super-secret-value" not in serialized
    assert report["adapters"]["omni"] == "real"
    assert report["camera"] == "camera:0 (AVFoundation)"
    assert report["microphone"] == "MacBook microphone"
    assert report["speaker"] == "Bose headphones"


def test_mock_self_check_labels_fixture_devices() -> None:
    report = build_self_check(RuntimeConfig(mode="mock"))

    assert report["camera"] == "mock camera fixture"
    assert report["microphone"] == "mock microphone fixture"
    assert report["speaker"] == "mock speaker fixture"


def test_hardware_real_self_check_is_explicitly_reserved() -> None:
    report = build_self_check(RuntimeConfig(mode="hardware-real"))

    assert set(report["adapters"].values()) == {"reserved"}
    assert report["camera"] == "reserved Jetson/Insta360 adapter"
    assert "Insta360 SDK" in report["missing_real_dependencies"]


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


@pytest.mark.asyncio
async def test_audio_loop_recovers_after_transient_device_error() -> None:
    class Microphone:
        reads = 0

        def read_chunk(self) -> bytes:
            self.reads += 1
            if self.reads == 1:
                raise OSError("temporary microphone error")
            return b"pcm"

    microphone = Microphone()
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.session_id = "session-1"
    runtime = PhotoAgentRuntime(fsm, microphone=microphone)

    task = asyncio.create_task(runtime._audio_loop())
    await asyncio.sleep(0.15)
    runtime.stop()
    await task

    assert microphone.reads >= 2
    assert omni.count("append_audio") >= 1


@pytest.mark.asyncio
async def test_audio_loop_does_not_leave_a_blocking_executor_read_on_shutdown(monkeypatch) -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.session_id = "session-1"
    runtime: PhotoAgentRuntime

    class Microphone:
        def read_chunk(self) -> bytes:
            runtime.stop()
            return b"pcm"

    runtime = PhotoAgentRuntime(fsm, microphone=Microphone())

    async def forbidden_to_thread(*args, **kwargs):
        runtime.stop()
        raise AssertionError("microphone reads must not outlive the audio task")

    monkeypatch.setattr(asyncio, "to_thread", forbidden_to_thread)

    await runtime._audio_loop()

    assert omni.count("append_audio") == 1


@pytest.mark.asyncio
async def test_audio_loop_drops_chunk_if_session_closes_during_microphone_read() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.session_id = "session-1"
    runtime: PhotoAgentRuntime

    class Microphone:
        def read_chunk(self) -> bytes:
            fsm.context.session_id = None
            runtime.stop()
            return b"stale-pcm"

    runtime = PhotoAgentRuntime(fsm, microphone=Microphone())

    await runtime._audio_loop()

    assert omni.count("append_audio") == 0


@pytest.mark.asyncio
async def test_cleanup_releases_all_resources_even_when_one_close_fails() -> None:
    class Microphone:
        def read_chunk(self) -> bytes:
            return b"pcm"

        def close(self) -> None:
            raise OSError("microphone close failed")

    class Resource:
        closed = False

        def close(self) -> None:
            self.closed = True

    camera = MockCamera(captures=[])
    omni = MockOmni()
    resource = Resource()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=camera,
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.session_id = "session-1"
    runtime = PhotoAgentRuntime(fsm, microphone=Microphone(), resources=[resource])
    runtime.stop()

    await runtime.run_forever()

    assert camera.closed is True
    assert omni.closed is True
    assert resource.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", ["error", "disconnected"])
async def test_omni_failure_closes_session_and_returns_idle(event_type: str) -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.session_id = "session-1"
    assert "fallback_notifier" in inspect.signature(PhotoAgentRuntime).parameters

    class Notifier:
        messages: list[str] = []

        async def notify(self, message: str) -> None:
            self.messages.append(message)

    notifier = Notifier()
    runtime = PhotoAgentRuntime(fsm, fallback_notifier=notifier)

    await runtime.handle_event({"type": event_type, "error": {"code": "network"}})

    assert fsm.context.state is State.IDLE
    assert omni.count("end_session") == 1
    assert omni.count("close") == 1
    assert notifier.messages == ["实时语音服务暂时不可用，本次服务已安全结束，请稍后再试。"]


@pytest.mark.asyncio
async def test_session_near_120_minute_limit_is_recycled() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.session_id = "session-1"
    fsm.context.session_started_at = 100.0
    runtime = PhotoAgentRuntime(fsm)
    runtime.session_max_s = 6900.0
    runtime._wall_clock = lambda: 7101.0

    await runtime._control_step()

    assert fsm.context.state is State.IDLE
    assert omni.count("end_session") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested", "events", "expected"),
    [
        ("S1", [], "S2"),
        ("S2", [{"type": "user_text", "text": "要"}], "S3"),
        ("S3", [{"type": "user_text", "text": "拍吧"}], "S4"),
        ("S4", [], "S5"),
        ("S5", [{"type": "user_text", "text": "满意"}], "S6"),
        ("S6", [], "S0"),
    ],
)
async def test_real_manual_runner_isolates_each_state(
    tmp_path, requested: str, events: list[dict], expected: str
) -> None:
    photo = tmp_path / "manual.jpg"
    photo.write_bytes(b"manual")
    omni = MockOmni()
    omni.events = deque(events)
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector(
            [WakeSignal(True, 3.1, True), WakeSignal(True, 3.2, True)]
        ),
        omni=omni,
        camera=MockCamera(captures=[CaptureResult("manual", photo, True, frame=object())]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(
            results=[DeliveryResult("manual", "http://local/api/photos/manual", True)]
        ),
    )
    runtime = PhotoAgentRuntime(fsm)

    result = await runtime.run_manual_state(requested, timeout=0.3)

    assert result["ok"] is True, result
    assert result["tested_state"] == requested
    assert result["result_state"] == expected
