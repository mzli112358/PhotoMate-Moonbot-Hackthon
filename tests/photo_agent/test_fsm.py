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
from app.photo_agent.models import CaptureResult, DeliveryResult, QualityResult, State, WakeSignal


GOOD_CAPTURE = CaptureResult("photo-1", Path("/tmp/photo-1.jpg"), True, np.ones((8, 8, 3)))
BAD_CAPTURE = CaptureResult("", Path("/tmp/missing.jpg"), False, error="camera failed")
GOOD_QUALITY = QualityResult(True, True, True)
BAD_QUALITY = QualityResult(True, False, True, "eyes_closed")
GOOD_DELIVERY = DeliveryResult("photo-1", "http://127.0.0.1:8000/api/photos/photo-1", True)
BAD_DELIVERY = DeliveryResult("photo-1", "", False, "frontend unavailable")


def build_fsm(
    *,
    wake_signals: list[WakeSignal] | None = None,
    captures: list[CaptureResult] | None = None,
    qualities: list[QualityResult] | None = None,
    deliveries: list[DeliveryResult] | None = None,
    omni: MockOmni | None = None,
    max_guidance_turns: int = 2,
    max_retake: int = 2,
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
async def test_s2_accept_decline_and_timeout_paths() -> None:
    accept, _, _, _ = build_fsm()
    accept.context.state = State.ASK_INTENT
    await accept.handle_user_text("好啊，帮我拍")
    assert accept.context.state is State.POSE_GUIDANCE

    decline, decline_omni, _, _ = build_fsm()
    decline.context.state = State.ASK_INTENT
    decline.context.session_id = "session-1"
    await decline.handle_user_text("不用了")
    assert decline.context.state is State.IDLE
    assert decline_omni.count("create_response") == 1
    assert decline_omni.count("wait_response_done") == 1
    assert decline_omni.count("end_session") == 1

    timeout, timeout_omni, _, _ = build_fsm()
    timeout.context.state = State.ASK_INTENT
    timeout.context.session_id = "session-1"
    await timeout.handle_timeout()
    assert timeout.context.state is State.ASK_INTENT
    await timeout.handle_timeout()
    assert timeout.context.state is State.IDLE
    assert timeout_omni.count("create_response") == 1


@pytest.mark.asyncio
async def test_s3_interval_is_gated_and_vad_interrupts() -> None:
    fsm, omni, camera, _ = build_fsm(max_guidance_turns=2)
    fsm.context.state = State.POSE_GUIDANCE

    assert await fsm.guidance_tick() is True
    assert fsm.context.response_in_flight is True
    assert await fsm.guidance_tick() is False
    await fsm.handle_speech_started()

    assert omni.count("cancel_response") == 1
    assert camera.count("get_frame") == 1
    assert omni.count("append_image") == 1
    # Server VAD owns commits; an explicit commit here races the server and is rejected.
    assert omni.count("commit_input") == 0

    await fsm.handle_response_done("往中间站一点")
    assert await fsm.guidance_tick() is True
    await fsm.handle_response_done("保持住")
    assert fsm.guidance_limit_reached is True
    assert omni.count("create_response") == 3  # 两轮引导 + 一次收敛询问

    await fsm.handle_user_text("可以拍了")
    assert fsm.context.state is State.SHOOT


@pytest.mark.asyncio
async def test_s4_capture_retries_then_quality_success_enters_review() -> None:
    fsm, omni, camera, delivery = build_fsm(captures=[BAD_CAPTURE, GOOD_CAPTURE])
    fsm.context.state = State.SHOOT

    result = await fsm.run_shoot()

    assert result.ok is True
    assert fsm.context.state is State.REVIEW
    assert camera.count("capture") == 2
    assert delivery.count("register_photo") == 1
    assert delivery.count("show") == 1
    assert omni.count("wait_response_done") == 1
    assert omni.count("create_response") == 2  # 倒数 + 复核询问


@pytest.mark.asyncio
async def test_s4_capture_exhaustion_apologizes_and_returns_to_guidance() -> None:
    fsm, omni, camera, _ = build_fsm(captures=[BAD_CAPTURE, BAD_CAPTURE])
    fsm.context.state = State.SHOOT

    result = await fsm.run_shoot()

    assert result.ok is False
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 1
    assert camera.count("capture") == 2
    assert omni.count("create_response") == 2  # 倒数 + 快门失败致歉


@pytest.mark.asyncio
async def test_s5_show_failure_retries_before_review_prompt() -> None:
    fsm, _, _, delivery = build_fsm()
    delivery._show_results = deque([False, True])
    fsm.context.state = State.SHOOT

    await fsm.run_shoot()

    assert fsm.context.state is State.REVIEW
    assert delivery.count("show") == 2


@pytest.mark.asyncio
async def test_s5_show_exhaustion_uses_voice_fallback() -> None:
    fsm, omni, _, delivery = build_fsm()
    delivery._show_results = deque([False, False])
    fsm.context.state = State.SHOOT

    await fsm.run_shoot()

    assert delivery.count("show") == 2
    assert omni.count("create_response") == 3  # 倒数 + 展示失败兜底 + 满意度询问


@pytest.mark.asyncio
async def test_s4_quality_failure_loops_and_honors_retake_limit() -> None:
    fsm, _, _, _ = build_fsm(
        captures=[GOOD_CAPTURE, GOOD_CAPTURE, GOOD_CAPTURE],
        qualities=[BAD_QUALITY, BAD_QUALITY, BAD_QUALITY],
        max_retake=2,
    )
    fsm.context.state = State.SHOOT

    await fsm.run_shoot()
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 1
    fsm.context.state = State.SHOOT
    await fsm.run_shoot()
    assert fsm.context.state is State.POSE_GUIDANCE
    assert fsm.context.retake_count == 2
    fsm.context.state = State.SHOOT
    await fsm.run_shoot()
    assert fsm.context.state is State.REVIEW
    assert fsm.context.retake_count == 2


@pytest.mark.asyncio
async def test_s5_review_routes_satisfied_retake_and_timeout() -> None:
    satisfied, _, _, _ = build_fsm()
    satisfied.context.state = State.REVIEW
    await satisfied.handle_user_text("满意")
    assert satisfied.context.state is State.DELIVER

    retake, _, _, _ = build_fsm()
    retake.context.state = State.REVIEW
    await retake.handle_user_text("不满意，重拍")
    assert retake.context.state is State.POSE_GUIDANCE

    timeout, _, _, _ = build_fsm()
    timeout.context.state = State.REVIEW
    await timeout.handle_timeout()
    assert timeout.context.state is State.DELIVER


@pytest.mark.asyncio
async def test_s6_success_returns_url_and_resets_everything() -> None:
    fsm, omni, _, delivery = build_fsm()
    fsm.context.state = State.DELIVER
    fsm.context.session_id = "session-1"
    fsm.context.photo_id = "photo-1"
    fsm.context.retake_count = 2

    result = await fsm.run_delivery()

    assert result == GOOD_DELIVERY
    assert fsm.context.state is State.IDLE
    assert fsm.context.session_id is None
    assert fsm.context.photo_id is None
    assert fsm.context.retake_count == 0
    assert delivery.count("deliver") == 1
    assert omni.count("wait_response_done") == 1
    assert omni.count("end_session") == 1
    assert omni.count("close") == 1


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
    await fsm.handle_user_text("要")
    await fsm.handle_user_text("拍吧")
    await fsm.run_shoot()
    await fsm.handle_user_text("满意")
    delivery = await fsm.run_delivery()

    assert delivery.ok is True
    assert fsm.context.state is State.IDLE
    assert fsm.background_task_count == 0
    assert omni.closed is True
