from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
import pytest

from app.photo_agent.fsm import FSMConfig, PhotoAgentFSM
from app.photo_agent.mocks import (
    MockCamera,
    MockDelivery,
    MockOmni,
    MockQualityChecker,
    MockWakeDetector,
)
from app.photo_agent.models import (
    CaptureResult,
    DeliveryResult,
    GuidanceTurn,
    PoseContext,
    PoseTurnState,
    QualityResult,
    State,
    WakeSignal,
)


GOOD_CAPTURE = CaptureResult("photo-1", Path("/tmp/photo-1.jpg"), True, np.ones((8, 8, 3)))
BAD_CAPTURE = CaptureResult("", Path("/tmp/missing.jpg"), False, error="camera failed")
GOOD_QUALITY = QualityResult(True, True, True)
BAD_QUALITY = QualityResult(True, False, True, "eyes_closed")
GOOD_DELIVERY = DeliveryResult("photo-1", "http://127.0.0.1:8000/api/photos/photo-1", True)
BAD_DELIVERY = DeliveryResult("photo-1", "", False, "frontend unavailable")


async def run_s3_capture(
    fsm: PhotoAgentFSM,
    *,
    speak: bool = True,
    text: str = "我拍好啦",
) -> CaptureResult:
    if fsm.context.pose_context is None:
        fsm.context.pose_context = PoseContext()
    if fsm.context.pose_turn is None or fsm.context.pose_turn.phase != "capturing":
        fsm.context.pose_turn = PoseTurnState(
            source="test",
            phase="capturing",
            pending_capture=True,
        )
    result, quality_ok = await fsm.run_capture_from_pose()
    await fsm.handle_pose_capture_result(
        {
            "ok": result.ok,
            "quality_ok": quality_ok,
            "photo_id": result.photo_id,
            "error": result.error,
        }
    )
    turn = fsm.context.pose_turn
    if speak and turn is not None and turn.phase == "speaking":
        await fsm.handle_pose_speech_done(text)
    return result


def build_fsm(
    *,
    wake_signals: list[WakeSignal] | None = None,
    captures: list[CaptureResult] | None = None,
    qualities: list[QualityResult] | None = None,
    deliveries: list[DeliveryResult] | None = None,
    omni: MockOmni | None = None,
    max_guidance_turns: int = 2,
    max_retake: int = 2,
    skip_quality_check: bool = False,
) -> tuple[PhotoAgentFSM, MockOmni, MockCamera, MockDelivery]:
    omni = omni or MockOmni()
    camera = MockCamera(captures=captures or [GOOD_CAPTURE])
    delivery = MockDelivery(results=deliveries or [GOOD_DELIVERY])
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector(wake_signals or []),
        omni=omni,
        camera=camera,
        quality_checker=MockQualityChecker(qualities or [GOOD_QUALITY]),
        delivery=delivery,
        config=FSMConfig(
            wake_consecutive_frames=2,
            max_guidance_turns=max_guidance_turns,
            max_retake=max_retake,
            operation_retries=1,
            skip_quality_check=skip_quality_check,
        ),
    )
    return fsm, omni, camera, delivery


@pytest.mark.asyncio
async def test_s1_requires_two_qualified_frames_then_connects_once() -> None:
    fsm, omni, _, _ = build_fsm(
        wake_signals=[
            WakeSignal(True, 1.0, True),
            WakeSignal(True, 3.1, True),
            WakeSignal(False, 0.0, False),
            WakeSignal(True, 3.2, True),
            WakeSignal(True, 3.4, True),
        ]
    )
    await fsm.start()

    for _ in range(5):
        await fsm.poll_wake()

    assert fsm.context.state is State.ASK_INTENT
    assert omni.count("connect") == 1
    assert omni.count("configure") == 1
    assert omni.count("prime_audio") == 1
    assert omni.count("create_response") == 1


@pytest.mark.asyncio
async def test_s1_retries_connection_once_then_returns_idle() -> None:
    omni = MockOmni(connect_failures=2)
    fsm, _, _, _ = build_fsm(
        omni=omni,
        wake_signals=[WakeSignal(True, 3.1, True), WakeSignal(True, 3.2, True)],
    )
    await fsm.start()
    await fsm.poll_wake()
    await fsm.poll_wake()

    assert fsm.context.state is State.IDLE
    assert omni.count("connect") == 2


@pytest.mark.asyncio
async def test_finished_session_requires_face_absence_before_rearming_s1() -> None:
    awake = WakeSignal(True, 3.2, True)
    fsm, omni, _, _ = build_fsm(
        wake_signals=[awake, awake, WakeSignal(False, 0.0, False), awake, awake]
    )
    fsm.context.session_id = "old-session"
    await fsm.finish_session("timeout")
    await fsm.start()

    await fsm.poll_wake()
    await fsm.poll_wake()
    assert omni.count("connect") == 0

    await fsm.poll_wake()
    await fsm.poll_wake()
    await fsm.poll_wake()
    assert omni.count("connect") == 1
    assert fsm.context.state is State.ASK_INTENT


@pytest.mark.asyncio
async def test_s2_uses_omni_intent_decisions_instead_of_asr_text() -> None:
    accept, _, _, _ = build_fsm()
    accept.context.state = State.ASK_INTENT

    # Accepting now opens the in-S2 device/mode picker before S3.
    await accept.handle_photo_intent("accept")
    assert accept.context.state is State.ASK_INTENT
    assert accept.context.s2_phase == "ask_device"
    await accept.handle_capture_device("insta")
    assert accept.context.s2_phase == "ask_mode"
    await accept.handle_capture_mode("photo")
    assert accept.context.state is State.POSE_GUIDANCE
    assert accept.context.capture_device == "insta"
    assert accept.context.capture_mode == "photo"

    decline, decline_omni, _, _ = build_fsm()
    decline.context.state = State.ASK_INTENT
    decline.context.session_id = "session-1"
    await decline.handle_photo_intent("deny")
    assert decline.context.state is State.IDLE
    assert decline_omni.count("create_response") == 1
    assert decline_omni.count("wait_response_done") == 1
    assert decline_omni.count("end_session") == 1


@pytest.mark.asyncio
async def test_s2_timeout_still_retries_once_then_returns_idle() -> None:
    timeout, timeout_omni, _, _ = build_fsm()
    timeout.context.state = State.ASK_INTENT
    timeout.context.session_id = "session-1"
    await timeout.handle_timeout()
    assert timeout.context.state is State.ASK_INTENT
    await timeout.handle_timeout()
    assert timeout.context.state is State.IDLE
    assert timeout_omni.count("create_response") == 1


@pytest.mark.asyncio
async def test_s2_timeout_does_not_renag_after_user_responds() -> None:
    fsm, omni, _, _ = build_fsm()
    fsm.context.state = State.ASK_INTENT
    fsm.context.s2_phase = "ask_intent"
    fsm.context.session_id = "session-1"

    # User speaks in response to the initial "要不要拍照" question.
    await fsm.handle_speech_started()
    assert fsm.context.user_responded is True

    # First silence window must NOT emit the re-ask fallback...
    await fsm.handle_timeout()
    assert omni.count("create_response") == 0
    assert fsm.context.state is State.ASK_INTENT

    # ...and a second full window ends the session gracefully instead of nagging.
    await fsm.handle_timeout()
    assert omni.count("create_response") == 0
    assert fsm.context.state is State.IDLE


@pytest.mark.asyncio
async def test_s2_and_s5_do_not_cancel_ask_prompt_on_speech_started() -> None:
    ask, ask_omni, _, _ = build_fsm()
    ask.context.state = State.ASK_INTENT
    ask.context.response_in_flight = True
    await ask.handle_speech_started()
    assert ask_omni.count("cancel_response") == 0

    review, review_omni, _, _ = build_fsm()
    review.context.state = State.REVIEW
    review.context.response_in_flight = True
    await review.handle_speech_started()
    assert review_omni.count("cancel_response") == 0


@pytest.mark.asyncio
async def test_s3_interval_starts_text_only_assessment_and_vad_interrupts() -> None:
    fsm, omni, camera, _ = build_fsm(max_guidance_turns=2)
    fsm.context.state = State.POSE_GUIDANCE

    assert await fsm.guidance_tick() is True
    assert fsm.context.response_in_flight is True
    assert fsm.context.pose_turn.phase == "assessing"
    assert await fsm.guidance_tick() is False
    assert camera.count("get_frame") == 1
    assert omni.count("append_image") == 1
    assert omni.count("commit_input") == 1
    create = [value for name, value in omni.calls if name == "create_response"][-1]
    assert create["output_audio"] is False
    assert fsm.context.pose_context.episode_id in create["instructions"]

    await fsm.handle_speech_started()

    assert omni.count("cancel_response") == 1
    assert fsm.context.pose_turn is None
    assert fsm.context.response_in_flight is False


@pytest.mark.asyncio
async def test_s3_audible_manual_speech_can_be_interrupted_without_capturing() -> None:
    fsm, omni, camera, _ = build_fsm()
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    fsm.context.pose_turn = PoseTurnState(
        source="interval",
        phase="speaking",
        capture_after_speech=True,
    )
    fsm.context.response_in_flight = True
    await omni.configure(enable_vad=True, output_audio=True)

    await fsm.handle_speech_started()

    assert omni.count("cancel_response") == 1
    assert omni.vad_enabled is True
    assert fsm.context.pose_turn is not None
    assert fsm.context.pose_turn.capture_after_speech is True
    assert fsm.context.response_in_flight is False
    assert camera.count("capture") == 0


@pytest.mark.asyncio
async def test_entering_s3_starts_a_fresh_pose_episode() -> None:
    fsm, _, _, _ = build_fsm()
    fsm.context.state = State.ASK_INTENT

    await fsm.handle_photo_intent("accept")
    await fsm.handle_capture_device("insta")
    await fsm.handle_capture_mode("photo")
    first_episode = fsm.context.pose_context.episode_id
    fsm.context.state = State.REVIEW
    await fsm.handle_review_intent("retake")

    assert fsm.context.pose_context.episode_id != first_episode


@pytest.mark.asyncio
async def test_s3_guidance_limit_is_a_speech_turn_not_another_assessment() -> None:
    fsm, omni, camera, _ = build_fsm(max_guidance_turns=1)
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.guidance_turns.append(GuidanceTurn(1.0, "interval", "继续保持"))

    assert await fsm.guidance_tick() is True

    response = [value for name, value in omni.calls if name == "create_response"][-1]
    assert response["output_audio"] is True
    assert "先帮你拍一张" in response["instructions"]
    assert fsm.context.pose_turn.phase == "speaking"
    assert camera.count("get_frame") == 0


@pytest.mark.asyncio
async def test_s3_capture_retries_then_quality_success_enters_review() -> None:
    fsm, omni, camera, delivery = build_fsm(captures=[BAD_CAPTURE, GOOD_CAPTURE])
    fsm.context.state = State.POSE_GUIDANCE

    result = await run_s3_capture(fsm)

    assert result.ok is True
    assert fsm.context.state is State.REVIEW
    assert camera.count("capture") == 2
    assert delivery.count("register_photo") == 1
    assert delivery.count("show") == 1
    assert omni.count("create_response") == 2  # 拍照完成播报 + 复核询问


@pytest.mark.asyncio
async def test_s3_capture_exhaustion_apologizes_and_returns_to_guidance() -> None:
    fsm, omni, camera, _ = build_fsm(captures=[BAD_CAPTURE, BAD_CAPTURE])
    fsm.context.state = State.POSE_GUIDANCE

    result = await run_s3_capture(fsm, speak=False)

    assert result.ok is False
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 1
    assert camera.count("capture") == 2
    assert omni.count("create_response") == 1  # 快门失败致歉


@pytest.mark.asyncio
async def test_s5_show_failure_retries_before_review_prompt() -> None:
    fsm, _, _, delivery = build_fsm()
    delivery._show_results = deque([False, True])
    fsm.context.state = State.POSE_GUIDANCE

    await run_s3_capture(fsm)

    assert fsm.context.state is State.REVIEW
    assert delivery.count("show") == 2


@pytest.mark.asyncio
async def test_s5_show_exhaustion_uses_voice_fallback() -> None:
    fsm, omni, _, delivery = build_fsm()
    delivery._show_results = deque([False, False])
    fsm.context.state = State.POSE_GUIDANCE

    await run_s3_capture(fsm)

    assert delivery.count("show") == 2
    assert omni.count("create_response") == 3  # 拍照完成播报 + 展示失败兜底 + 满意度询问


@pytest.mark.asyncio
async def test_s3_quality_failure_loops_and_honors_retake_limit() -> None:
    fsm, _, _, _ = build_fsm(
        captures=[GOOD_CAPTURE, GOOD_CAPTURE, GOOD_CAPTURE],
        qualities=[BAD_QUALITY, BAD_QUALITY, BAD_QUALITY],
        max_retake=2,
        skip_quality_check=False,
    )
    fsm.context.state = State.POSE_GUIDANCE

    await run_s3_capture(fsm, speak=False)
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 1
    await run_s3_capture(fsm, speak=False)
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 2
    await run_s3_capture(fsm)
    assert fsm.context.state is State.REVIEW
    assert fsm.context.retake_count == 2


@pytest.mark.asyncio
async def test_say_and_wait_restores_session_audio_after_text_only_turn() -> None:
    fsm, omni, _, _ = build_fsm()
    await omni.configure(enable_vad=False, output_audio=False)

    await fsm._say_and_wait("抱歉，我们再试一次。")

    assert omni.output_audio_enabled is True
    speech = [value for name, value in omni.calls if name == "create_response"][-1]
    assert speech["output_audio"] is True


@pytest.mark.asyncio
async def test_run_capture_skips_quality_check_by_default() -> None:
    fsm, _, _, _ = build_fsm(qualities=[BAD_QUALITY], skip_quality_check=True)
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_turn = PoseTurnState(source="test", phase="capturing", pending_capture=True)

    result, quality_ok = await fsm.run_capture_from_pose()

    assert result.ok is True
    assert quality_ok is True


@pytest.mark.asyncio
async def test_s5_review_routes_satisfied_retake_and_timeout() -> None:
    satisfied, _, _, _ = build_fsm()
    satisfied.context.state = State.REVIEW
    await satisfied.handle_review_intent("accept")
    assert satisfied.context.state is State.DELIVER

    retake, _, _, _ = build_fsm()
    retake.context.state = State.REVIEW
    await retake.handle_review_intent("retake")
    assert retake.context.state is State.POSE_GUIDANCE

    timeout, _, _, _ = build_fsm()
    timeout.context.state = State.REVIEW
    await timeout.handle_timeout()
    assert timeout.context.state is State.DELIVER


@pytest.mark.asyncio
async def test_s6_success_delivers_then_lingers_on_share_page() -> None:
    fsm, omni, _, delivery = build_fsm()
    fsm.context.state = State.DELIVER
    fsm.context.session_id = "session-1"
    fsm.context.photo_id = "photo-1"

    result = await fsm.run_delivery()

    assert result == GOOD_DELIVERY
    # Delivery announces then lingers on /post; the loop is NOT reset yet so the
    # guest keeps seeing the QR until the runtime's share window elapses.
    assert fsm.context.state is State.DELIVER
    assert fsm.context.session_id == "session-1"
    assert fsm.context.photo_id == "photo-1"
    assert fsm.context.photo_url == GOOD_DELIVERY.photo_url
    assert fsm.context.delivered_at > 0.0
    assert delivery.count("deliver") == 1
    assert omni.count("wait_response_done") == 1
    assert omni.count("end_session") == 0
    assert omni.count("close") == 0

    # When the runtime later ends the share window everything resets for the next loop.
    await fsm.finish_session("share_linger_timeout")
    assert fsm.context.state is State.IDLE
    assert fsm.context.session_id is None
    assert fsm.context.photo_id is None
    assert fsm.context.delivered_at == 0.0
    assert omni.count("end_session") == 1
    assert omni.count("close") == 1


@pytest.mark.asyncio
async def test_pose_readiness_is_ignored_during_active_capture() -> None:
    fsm, omni, camera, _ = build_fsm()
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_turn = PoseTurnState(source="test", phase="capturing", pending_capture=True)

    await fsm.handle_pose_readiness("ready")

    assert fsm.context.pose_turn.phase == "capturing"
    assert omni.count("create_response") == 0
    assert camera.count("capture") == 0


@pytest.mark.asyncio
async def test_s6_failure_retries_and_still_closes_and_resets() -> None:
    fsm, omni, _, delivery = build_fsm(deliveries=[BAD_DELIVERY, BAD_DELIVERY])
    fsm.context.state = State.DELIVER
    fsm.context.session_id = "session-1"
    fsm.context.photo_id = "photo-1"

    result = await fsm.run_delivery()

    assert result.ok is False
    assert delivery.count("deliver") == 2
    assert omni.count("create_response") == 1
    assert omni.count("wait_response_done") == 1
    assert omni.count("end_session") == 1
    assert omni.count("close") == 1
    assert fsm.context.state is State.IDLE


@pytest.mark.asyncio
async def test_mock_happy_path_s1_to_s6_has_no_session_leak() -> None:
    fsm, omni, _, _ = build_fsm(
        wake_signals=[WakeSignal(True, 3.1, True), WakeSignal(True, 3.2, True)]
    )
    await fsm.start()
    await fsm.poll_wake()
    await fsm.poll_wake()
    await fsm.handle_photo_intent("accept")
    await fsm.handle_capture_device("insta")
    await fsm.handle_capture_mode("photo")
    await fsm.handle_pose_readiness("ready")
    result, quality_ok = await fsm.run_capture_from_pose()
    await fsm.handle_pose_capture_result(
        {
            "ok": result.ok,
            "quality_ok": quality_ok,
            "photo_id": result.photo_id,
            "error": result.error,
        }
    )
    await fsm.handle_pose_speech_done("我拍好啦")
    await fsm.handle_review_intent("accept")
    delivery = await fsm.run_delivery()
    # Share page lingers after delivery; the runtime ends it to restart the loop.
    await fsm.finish_session("share_linger_timeout")

    assert delivery.ok is True
    assert fsm.context.state is State.IDLE
    assert fsm.background_task_count == 0
    assert omni.closed is True
