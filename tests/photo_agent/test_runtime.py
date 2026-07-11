from __future__ import annotations

import json
import asyncio
import inspect
from collections import deque
from pathlib import Path

import pytest

from app.photo_agent.dispatcher import FunctionCallDispatcher
from app.photo_agent.fsm import FSMConfig, PhotoAgentFSM
from app.photo_agent.mocks import MockCamera, MockDelivery, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import (
    CaptureResult,
    DeliveryResult,
    PoseContext,
    PoseGoal,
    PoseTurnState,
    QualityResult,
    State,
    ToolCall,
    WakeSignal,
)
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
    [("S1", "S2"), ("S2", "S3"), ("S3", "S5"), ("S5", "S6"), ("S6", "S0")],
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
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    fsm.context.pose_turn = PoseTurnState(
        source="test",
        phase="capturing",
        pending_capture=True,
    )
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
    fsm.context.pose_context = PoseContext()
    fsm.context.pose_turn = PoseTurnState(
        source="test",
        phase="capturing",
        pending_capture=True,
    )

    await runtime.handle_event({"type": "speech_started"})
    await runtime.handle_event(
        {"type": "tool_call", "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "c1")}
    )
    await runtime.handle_event({"type": "response_created", "response_id": "speech-1"})
    await runtime.handle_event(
        {"type": "assistant_text", "response_id": "speech-1", "text": "我拍好啦"}
    )
    await runtime.handle_event({"type": "response_done", "response_id": "speech-1"})

    assert fsm.context.state is State.REVIEW
    assert omni.count("submit_tool_result") == 1


@pytest.mark.asyncio
async def test_user_ready_is_reported_by_omni_function_call_before_capture(tmp_path) -> None:
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
    fsm.context.pose_context = PoseContext()
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event({"type": "response_created", "response_id": "user-vad-1"})
    await runtime.handle_event(
        {
            "type": "tool_call",
            "response_id": "user-vad-1",
            "tool_call": ToolCall("report_pose_readiness", {"decision": "ready"}, "ready-1"),
        }
    )
    await runtime.handle_event({"type": "response_done", "response_id": "user-vad-1"})

    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.phase == "speaking"
    assert fsm.context.pose_turn.capture_after_speech is True
    assert camera.count("capture") == 0
    assert fsm.omni.count("submit_tool_result") == 1

    await runtime.handle_event({"type": "response_created", "response_id": "ready-speech"})
    await runtime.handle_event(
        {
            "type": "assistant_text",
            "response_id": "ready-speech",
            "text": "好的，保持一下，我马上拍照。",
        }
    )
    await runtime.handle_event({"type": "response_done", "response_id": "ready-speech"})

    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.phase == "capturing"
    capture_prompt = [value for name, value in fsm.omni.calls if name == "create_response"][-1]
    assert capture_prompt["output_audio"] is False
    assert "capture_photo" in capture_prompt["instructions"]


@pytest.mark.asyncio
async def test_direct_capture_tool_from_user_vad_is_deferred_into_safe_capture_flow() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event({"type": "response_created", "response_id": "user-vad-direct"})
    await runtime.handle_event(
        {
            "type": "tool_call",
            "response_id": "user-vad-direct",
            "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "direct-capture"),
        }
    )

    submitted = [value for name, value in omni.calls if name == "submit_tool_result"][-1]
    assert submitted[1]["ok"] is True
    assert submitted[1]["deferred"] is True
    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.pending_capture is True

    await runtime.handle_event({"type": "response_done", "response_id": "user-vad-direct"})

    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.phase == "speaking"
    assert fsm.context.pose_turn.capture_after_speech is True


@pytest.mark.asyncio
async def test_duplicate_pose_turn_submits_previous_tool_result_first() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    fsm.context.pose_turn = PoseTurnState(source="interval", phase="assessing")
    runtime = PhotoAgentRuntime(fsm)

    for call in (
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "双手比心",
                "success_criteria": "组成心形",
                "progress": "not_started",
                "visual_observation": "第一次",
                "user_feedback_summary": "无",
                "guidance_intent": "一起比心",
                "completion_reason": "none",
            },
            "pose-first",
        ),
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "partial",
                "visual_observation": "第二次",
                "user_feedback_summary": "无",
                "guidance_intent": "手再高一点",
                "completion_reason": "none",
            },
            "pose-second",
        ),
    ):
        await runtime.handle_event({"type": "tool_call", "tool_call": call})

    submitted = [value for name, value in omni.calls if name == "submit_tool_result"]
    assert len(submitted) == 1
    assert submitted[0][0] == "pose-first"
    assert fsm.context.pose_turn.pending_tool_submit[0] == "pose-second"


@pytest.mark.asyncio
async def test_s3_pose_turn_saves_context_then_speaks_and_counts_once() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)
    await fsm.guidance_tick()

    await runtime.handle_event(
        {
            "type": "tool_call",
            "tool_call": ToolCall(
                "report_pose_turn",
                {
                    "goal_action": "create",
                    "active_goal": {
                        "description": "双手在胸前比心",
                        "success_criteria": ["双手可见", "组成心形"],
                    },
                    "progress": "not_started",
                    "visual_observation": "用户自然站立",
                    "guidance_intent": "邀请用户一起比心",
                },
                "pose-call-1",
            ),
        }
    )
    assert omni.count("submit_tool_result") == 0

    await runtime.handle_event({"type": "response_done", "response_id": "assess-1"})

    submitted = [value for name, value in omni.calls if name == "submit_tool_result"][-1]
    assert submitted[2] is False
    call_names = [name for name, _ in omni.calls]
    assert call_names.index("configure") < call_names.index("submit_tool_result")
    speech_configure = [value for name, value in omni.calls if name == "configure"][-1]
    assert speech_configure["tools"] == []

    speech = [value for name, value in omni.calls if name == "create_response"][-1]
    assert speech["output_audio"] is True
    assert "邀请用户一起比心" in speech["instructions"]
    assert omni.vad_enabled is True
    assert omni.output_audio_enabled is True
    assert fsm.context.pose_turn.phase == "speaking"
    assert len(fsm.context.guidance_turns) == 0

    await runtime.handle_event(
        {
            "type": "assistant_text",
            "response_id": "speech-1",
            "text": "我们一起比个心吧！",
        }
    )
    await runtime.handle_event({"type": "response_done", "response_id": "speech-1"})

    assert fsm.context.pose_context.last_spoken_text == "我们一起比个心吧！"
    assert fsm.context.pose_context.logical_turn == 1
    assert len(fsm.context.guidance_turns) == 1
    assert fsm.context.pose_turn is None
    assert fsm.context.response_in_flight is False
    assert omni.vad_enabled is True
    assert omni.output_audio_enabled is True


@pytest.mark.asyncio
async def test_completed_pose_captures_in_s3_then_enters_review(tmp_path: Path) -> None:
    capture = CaptureResult("p-complete", tmp_path / "p-complete.jpg", True, frame=object())
    capture.path.write_bytes(b"jpeg")
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[capture]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p-complete", "http://local/api/photos/p-complete", True)]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)
    await fsm.guidance_tick()

    for call in (
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "active_goal": {
                    "description": "双手比心",
                    "success_criteria": ["组成明显心形"],
                },
                "progress": "not_started",
                "visual_observation": "尚未开始",
                "guidance_intent": "邀请用户比心",
            },
            "create-goal",
        ),
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "complete",
                "progress": "achieved",
                "visual_observation": "已经组成心形",
                "guidance_intent": "确认动作完成并请用户保持",
                "completion_reason": "visual_goal_achieved",
            },
            "complete-goal",
        ),
    ):
        await runtime.handle_event({"type": "tool_call", "tool_call": call})

    assert fsm.context.state is State.POSE_GUIDANCE
    await runtime.handle_event({"type": "response_done", "response_id": "assess-complete"})
    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.phase == "speaking"
    assert fsm.context.pose_turn.capture_after_speech is True

    pre_capture_speech = [value for name, value in omni.calls if name == "create_response"][-1]
    assert pre_capture_speech["output_audio"] is True
    assert "确认动作完成并请用户保持" in pre_capture_speech["instructions"]

    await runtime.handle_event({"type": "response_created", "response_id": "pre-capture-speech"})
    await runtime.handle_event(
        {
            "type": "assistant_text",
            "response_id": "pre-capture-speech",
            "text": "太棒了，保持这个姿势，我马上拍照。",
        }
    )
    await runtime.handle_event({"type": "response_done", "response_id": "pre-capture-speech"})

    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.phase == "capturing"

    capture_prompt = [value for name, value in omni.calls if name == "create_response"][-1]
    assert "capture_photo" in capture_prompt["instructions"]

    await runtime.handle_event({"type": "response_created", "response_id": "capture-response"})
    await runtime.handle_event(
        {
            "type": "tool_call",
            "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "capture-1"),
            "response_id": "capture-response",
        }
    )

    assert fsm.context.photo_id == "p-complete"
    assert fsm.context.pose_turn.phase == "speaking"
    assert fsm.context.pose_turn.post_capture_speech is True
    captured_prompt = [value for name, value in omni.calls if name == "create_response"][-1]
    assert captured_prompt["output_audio"] is True
    assert "我拍好啦" in captured_prompt["instructions"]

    # The text-only capture response can finish after capture_photo has already
    # created the post-capture speech. It must not be mistaken for speech.done.
    await runtime.handle_event({"type": "response_done", "response_id": "capture-response"})
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.pose_turn.phase == "speaking"

    await runtime.handle_event(
        {"type": "assistant_text", "response_id": "speech-captured", "text": "我拍好啦"}
    )
    await runtime.handle_event({"type": "response_created", "response_id": "speech-captured"})
    await runtime.handle_event({"type": "response_done", "response_id": "speech-captured"})

    assert fsm.context.state is State.REVIEW
    assert fsm.context.pose_turn is None


@pytest.mark.asyncio
async def test_s3_user_vad_can_replace_the_active_pose_goal() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext(
        active_goal=PoseGoal("pose-1", "双手比心", ["双手组成心形"])
    )
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event({"type": "response_created", "response_id": "vad-assess"})
    assert fsm.context.pose_turn.source == "user_vad"

    await runtime.handle_event(
        {
            "type": "tool_call",
            "tool_call": ToolCall(
                "report_pose_turn",
                {
                    "goal_action": "replace",
                    "active_goal": {
                        "description": "举起右手比耶",
                        "success_criteria": ["右手做出V字"],
                    },
                    "progress": "not_started",
                    "visual_observation": "用户要求换动作",
                    "user_feedback_summary": "用户说不想比心",
                    "replace_reason": "用户明确要求更换",
                    "guidance_intent": "回应用户并邀请其比耶",
                },
                "vad-replace",
            ),
        }
    )
    await runtime.handle_event({"type": "response_done", "response_id": "vad-assess"})
    await runtime.handle_event({"type": "response_created", "response_id": "vad-speech"})
    await runtime.handle_event(
        {"type": "assistant_text", "response_id": "vad-speech", "text": "好呀，那我们一起比个耶！"}
    )
    await runtime.handle_event({"type": "response_done", "response_id": "vad-speech"})

    assert fsm.context.pose_context.active_goal.description == "举起右手比耶"
    assert fsm.context.pose_context.goal_history[0].status == "replaced"
    assert fsm.context.guidance_turns[-1].prompt_source == "user_vad"


@pytest.mark.asyncio
async def test_s3_ignores_response_done_from_a_cancelled_pose_turn() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)
    await fsm.guidance_tick()
    await runtime.handle_event(
        {"type": "assistant_text", "response_id": "cancelled", "text": "不应保存"}
    )

    await runtime.handle_event({"type": "speech_started"})
    await runtime.handle_event({"type": "response_done", "response_id": "cancelled"})

    assert fsm.context.guidance_turns == []
    assert runtime._pending_assistant_text == ""
    assert omni.output_audio_enabled is True


@pytest.mark.asyncio
async def test_s3_rejects_pose_tool_without_an_active_assessment_turn() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event(
        {
            "type": "tool_call",
            "response_id": "stale-response",
            "tool_call": ToolCall(
                "report_pose_turn",
                {
                    "goal_action": "create",
                    "goal_description": "双手比心",
                    "success_criteria": "双手组成心形",
                    "progress": "not_started",
                    "visual_observation": "过期结果",
                    "guidance_intent": "过期引导",
                    "completion_reason": "none",
                },
                "stale-call",
            ),
        }
    )

    submitted = [value for name, value in omni.calls if name == "submit_tool_result"][-1]
    assert submitted[1] == {"ok": False, "error": "no_active_pose_assessment"}
    assert fsm.context.pose_context.active_goal is None


@pytest.mark.asyncio
async def test_s3_ignores_response_done_from_an_old_response() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)
    await fsm.guidance_tick()
    await runtime.handle_event({"type": "response_created", "response_id": "current-assess"})

    await runtime.handle_event({"type": "response_done", "response_id": "old-assess"})

    assert fsm.context.pose_turn.phase == "assessing"
    assert fsm.context.response_in_flight is True


@pytest.mark.asyncio
async def test_invalid_omni_intent_call_is_rejected_without_state_transition() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event(
        {
            "type": "tool_call",
            "tool_call": ToolCall("report_review_intent", {"decision": "accept"}, "bad-1"),
        }
    )

    assert fsm.context.state is State.POSE_GUIDANCE
    assert [value for name, value in omni.calls if name == "submit_tool_result"] == [
        ("bad-1", {"ok": False, "error": "invalid_state:S3"}, True)
    ]


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
async def test_recoverable_append_image_error_does_not_close_session() -> None:
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
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event(
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Error append image before append audio.",
            },
        }
    )

    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.session_id == "session-1"
    assert omni.count("prime_audio") == 1
    assert omni.count("end_session") == 0


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
        (
            "S2",
            [
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_photo_intent", {"decision": "accept"}, "intent-1"
                    ),
                },
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_capture_device", {"device": "insta"}, "device-1"
                    ),
                },
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_capture_mode", {"mode": "photo"}, "mode-1"
                    ),
                },
            ],
            "S3",
        ),
        (
            "S3",
            [
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_pose_turn",
                        {
                            "goal_action": "create",
                            "active_goal": {
                                "description": "双手比心",
                                "success_criteria": ["组成心形"],
                            },
                            "progress": "not_started",
                            "visual_observation": "用户站立",
                            "guidance_intent": "一起比个心吧",
                        },
                        "pose-create",
                    ),
                },
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_pose_turn",
                        {
                            "goal_action": "complete",
                            "progress": "achieved",
                            "visual_observation": "动作已达标",
                            "guidance_intent": "保持住，准备拍照",
                            "completion_reason": "visual_goal_achieved",
                        },
                        "pose-complete",
                    ),
                },
                {"type": "response_done", "response_id": "assess-complete"},
                {"type": "response_created", "response_id": "pre-capture-speech"},
                {
                    "type": "assistant_text",
                    "response_id": "pre-capture-speech",
                    "text": "保持住，准备拍照",
                },
                {"type": "response_done", "response_id": "pre-capture-speech"},
                {"type": "response_created", "response_id": "capture-1"},
                {
                    "type": "tool_call",
                    "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "cap-1"),
                    "response_id": "capture-1",
                },
                {"type": "response_created", "response_id": "speech-1"},
                {
                    "type": "assistant_text",
                    "response_id": "speech-1",
                    "text": "我拍好啦",
                },
                {"type": "response_done", "response_id": "speech-1"},
            ],
            "S5",
        ),
        (
            "S5",
            [
                {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        "report_review_intent", {"decision": "accept"}, "review-1"
                    ),
                }
            ],
            "S6",
        ),
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

    result = await runtime.run_manual_state(requested, timeout=1.0 if requested == "S3" else 0.3)

    assert result["ok"] is True, result
    assert result["tested_state"] == requested
    assert result["result_state"] == expected


@pytest.mark.asyncio
async def test_empty_speech_response_triggers_one_retry() -> None:
    omni = MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext(last_guidance_intent="邀请用户一起比心")
    fsm.context.pose_turn = PoseTurnState(source="interval", phase="speaking")
    runtime = PhotoAgentRuntime(fsm)

    await runtime.handle_event(
        {"type": "response_done", "response_id": "speech-1", "audio_delta_count": 0}
    )

    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.speech_retry_used is True
    retry = [value for name, value in omni.calls if name == "create_response"][-1]
    assert "邀请用户一起比心" in retry["instructions"]
    assert omni.count("create_response") == 1
    assert len(fsm.context.guidance_turns) == 0
