"""Explicit asyncio S1-S6 state orchestrator."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from app.photo_agent.interfaces import (
    CameraAdapter,
    DeliveryAdapter,
    OmniClient,
    QualityChecker,
    WakeDetector,
)
from app.photo_agent.models import (
    CaptureResult,
    DeliveryResult,
    GuidanceTurn,
    PoseContext,
    PoseTurnState,
    SessionContext,
    State,
)
from app.photo_agent.prompts import PromptSource, StaticPromptSource

LOGGER = logging.getLogger("photomate.photo_agent")
T = TypeVar("T")
_COACH_SILENCE_PCM = b"\x00\x00" * 1600

STATE_PROMPT_KEYS = {
    State.ASK_INTENT: "state.S2",
    State.POSE_GUIDANCE: "state.S3",
    State.REVIEW: "state.S5",
    State.DELIVER: "state.S6",
}


@dataclass(frozen=True)
class FSMConfig:
    dwell_threshold_s: float = 3.0
    wake_consecutive_frames: int = 2
    guidance_interval_s: float = 5.0
    max_guidance_turns: int = 8
    max_retake: int = 2
    operation_retries: int = 1
    skip_quality_check: bool = True


class PhotoAgentFSM:
    """Deterministic state owner; Omni supplies language and tool suggestions only."""

    def __init__(
        self,
        *,
        wake_detector: WakeDetector,
        omni: OmniClient,
        camera: CameraAdapter,
        quality_checker: QualityChecker,
        delivery: DeliveryAdapter,
        config: FSMConfig | None = None,
        prompts: PromptSource | None = None,
    ) -> None:
        self.wake_detector = wake_detector
        self.omni = omni
        self.camera = camera
        self.quality_checker = quality_checker
        self.delivery = delivery
        self.config = config or FSMConfig()
        self.prompts = prompts or StaticPromptSource()
        self.context = SessionContext(
            guidance_interval_s=self.config.guidance_interval_s,
            max_guidance_turns=self.config.max_guidance_turns,
            max_retake=self.config.max_retake,
        )
        self.guidance_limit_reached = False
        self._qualified_wake_frames = 0
        self._wake_rearm_required = False
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @property
    def background_task_count(self) -> int:
        return sum(not task.done() for task in self._background_tasks)

    def _transition(self, state: State, reason: str) -> None:
        old = self.context.state
        self.context.state = state
        LOGGER.info(
            "state_transition",
            extra={
                "from_state": old.value,
                "to_state": state.value,
                "reason": reason,
                "session_id": self.context.session_id,
                "photo_id": self.context.photo_id,
            },
        )

    async def _retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.config.operation_retries + 1):
            try:
                return await operation()
            except Exception as exc:  # noqa: BLE001 - adapter boundary
                last_error = exc
                LOGGER.warning("operation_retry", extra={"attempt": attempt + 1, "error": str(exc)})
        assert last_error is not None
        raise last_error

    async def start(self) -> None:
        if self.context.state is not State.IDLE:
            return
        self._qualified_wake_frames = 0
        self._transition(State.DETECT_INTENT, "service_started")

    async def poll_wake(self) -> None:
        if self.context.state is not State.DETECT_INTENT:
            return
        signal = await self.wake_detector.poll()
        if self.context.state is State.DETECT_INTENT and (
            signal.person_present or self._qualified_wake_frames
        ):
            LOGGER.info(
                "wake_poll",
                extra={
                    "person_present": signal.person_present,
                    "facing_robot": signal.facing_robot,
                    "dwell_seconds": round(signal.dwell_seconds, 2),
                    "qualified_frames": self._qualified_wake_frames,
                },
            )
        if self._wake_rearm_required:
            self._qualified_wake_frames = 0
            if signal.person_present:
                return
            self._wake_rearm_required = False
        if signal.is_awake(self.config.dwell_threshold_s):
            self._qualified_wake_frames += 1
        else:
            self._qualified_wake_frames = 0
        if self._qualified_wake_frames < self.config.wake_consecutive_frames:
            return
        try:
            session_id = await self._retry(self.omni.connect)
            self.context.session_id = session_id
            self.context.session_started_at = time.time()
            await self.omni.configure()
            await self.omni.prime_audio()
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("omni_connect_failed", extra={"error": str(exc)})
            self._transition(State.IDLE, "omni_connect_failed")
            return
        await self._enter(State.ASK_INTENT, "wake_qualified")
        await self.omni.create_response(self.prompts.get("action.S2.ask_initial"))

    async def _enter(self, state: State, reason: str) -> None:
        self._transition(state, reason)
        if state is State.POSE_GUIDANCE:
            self.context.pose_context = PoseContext()
            self.context.pose_turn = None
        prompt_key = STATE_PROMPT_KEYS.get(state)
        if prompt_key and self.context.session_id:
            await self.omni.inject_context(self.prompts.get(prompt_key))

    async def enter_manual_state(self, state: State) -> None:
        if state is State.IDLE:
            raise ValueError("manual state must be S1-S6")
        await self._enter(state, "manual_acceptance")

    async def handle_photo_intent(self, decision: str) -> None:
        if self.context.state is not State.ASK_INTENT:
            raise ValueError(f"photo intent is invalid in state {self.context.state.value}")
        if decision == "accept":
            self.guidance_limit_reached = False
            await self._enter(State.POSE_GUIDANCE, "user_accepted")
            return
        if decision == "deny":
            await self._say_and_wait(self.prompts.get("action.S2.decline"))
            await self._finish_session("user_declined")
            return
        raise ValueError(f"unsupported photo intent: {decision}")

    async def handle_pose_readiness(self, decision: str) -> None:
        if self.context.state is not State.POSE_GUIDANCE:
            raise ValueError(f"pose readiness is invalid in state {self.context.state.value}")
        if decision != "ready":
            raise ValueError(f"unsupported pose readiness: {decision}")
        turn = self.context.pose_turn
        if turn is not None and turn.phase == "speaking":
            LOGGER.warning(
                "pose_readiness_ignored_during_active_turn",
                extra={"phase": turn.phase, "session_id": self.context.session_id},
            )
            return
        if turn is not None and turn.phase == "assessing":
            # A user-VAD response reports readiness instead of report_pose_turn.
            # Mark the assessment complete so response.done advances to capture.
            turn.tool_result_received = True
            turn.pending_capture = True
            if self.context.pose_context is not None:
                self.context.pose_context.last_guidance_intent = "动作很好，我开拍啦！"
            return
        if turn is not None and turn.phase == "capturing":
            LOGGER.warning(
                "pose_readiness_ignored_during_capture",
                extra={"session_id": self.context.session_id},
            )
            return
        await self.start_pose_capture("user_ready")

    async def _configure_listening(self) -> None:
        """S3 idle: server VAD on for barge-in, tools enabled for user-driven reports."""
        await self.omni.configure(enable_vad=True, output_audio=True)

    async def _configure_tool_turn(self) -> None:
        """Internally-driven S3 turn (assessment/capture): VAD off so the local
        silence+frame buffer is not polluted, tools enabled for model reports."""
        await self.omni.configure(enable_vad=False, output_audio=True)

    async def _configure_pose_speech(self) -> None:
        """Audible S3 speech: keep session audio on but disable tools so the model speaks."""
        await self.omni.configure(enable_vad=True, output_audio=True, tools=[])

    async def retry_pose_speech(self, guidance_intent: str) -> None:
        turn = self.context.pose_turn
        if turn is None or turn.phase != "speaking":
            return
        await self._configure_pose_speech()
        instructions = (
            self.prompts.get("action.S3.captured")
            if turn.post_capture_speech
            else self.prompts.render("action.S3.speak_retry", guidance_intent=guidance_intent)
        )
        LOGGER.warning(
            "s3_speech_retry",
            extra={
                "guidance_intent": guidance_intent,
                "post_capture_speech": turn.post_capture_speech,
                "session_id": self.context.session_id,
            },
        )
        await self.omni.create_response(instructions, output_audio=True)

    async def start_pose_capture(self, source: str) -> None:
        """Begin in-S3 capture: model calls capture_photo, then speaks 我拍好啦."""
        if self.context.pose_context is None:
            self.context.pose_context = PoseContext()
        self.context.pose_turn = PoseTurnState(
            source=source,
            phase="capturing",
            pending_capture=True,
        )
        self.context.response_in_flight = True
        await self._configure_tool_turn()
        await self.omni.create_response(
            self.prompts.get("action.S3.capture"),
            output_audio=False,
        )

    async def handle_review_intent(self, decision: str) -> None:
        if self.context.state is not State.REVIEW:
            raise ValueError(f"review intent is invalid in state {self.context.state.value}")
        if decision == "retake":
            self.guidance_limit_reached = False
            await self._enter(State.POSE_GUIDANCE, "user_requested_retake")
            return
        if decision == "accept":
            await self._enter(State.DELIVER, "user_satisfied")
            return
        raise ValueError(f"unsupported review intent: {decision}")

    async def handle_timeout(self) -> None:
        if self.context.state is State.ASK_INTENT:
            if self.context.ask_timeout_count == 0:
                self.context.ask_timeout_count = 1
                await self.omni.create_response(self.prompts.get("action.S2.ask_retry"))
            else:
                await self._finish_session("timeout")
        elif self.context.state is State.REVIEW:
            await self._enter(State.DELIVER, "review_timeout_default_accept")

    async def _coach_guidance_response(self) -> None:
        """Start a text-only assessment bound to the current camera frame."""
        if self.context.pose_context is None:
            self.context.pose_context = PoseContext()
        self.context.pose_turn = PoseTurnState(source="interval")
        await self._configure_tool_turn()
        await self.omni.append_audio(_COACH_SILENCE_PCM)
        frame = await self.camera.get_frame()
        await self.omni.append_image(frame)
        await self.omni.commit_input()
        self.context.response_in_flight = True
        pose = self.context.pose_context
        guidance_phase = "intro" if pose.active_goal is None else "coach"
        instructions = self.prompts.render(
            "action.S3.assess",
            pose_context=pose.snapshot_for_prompt(),
            guidance_phase=guidance_phase,
        )
        await self.omni.create_response(instructions, output_audio=False)
        LOGGER.info(
            "s3_coach_turn_started",
            extra={
                "guidance_phase": guidance_phase,
                "episode_id": self.context.pose_context.episode_id,
                "frame_shape": getattr(frame, "shape", None),
            },
        )

    async def guidance_tick(self) -> bool:
        if self.context.state is not State.POSE_GUIDANCE or self.context.response_in_flight:
            return False
        if len(self.context.guidance_turns) >= self.context.max_guidance_turns:
            if not self.guidance_limit_reached:
                self.guidance_limit_reached = True
                await self._start_pose_speech(self.prompts.get("action.S3.guidance_limit"))
                return True
            return False
        await self._coach_guidance_response()
        return True

    async def _start_pose_speech(self, instructions: str) -> None:
        if self.context.pose_context is None:
            self.context.pose_context = PoseContext()
        self.context.pose_turn = PoseTurnState(source="interval", phase="speaking")
        self.context.response_in_flight = True
        await self._configure_pose_speech()
        await self.omni.create_response(instructions, output_audio=True)

    async def handle_speech_started(self) -> None:
        # S2/S5 ask a question first; only S3 allows the user to barge in mid-utterance.
        if self.context.state in (State.ASK_INTENT, State.REVIEW):
            return
        if self.context.response_in_flight:
            await self.omni.cancel_response()
            self.context.response_in_flight = False
            if self.context.state is State.POSE_GUIDANCE:
                turn = self.context.pose_turn
                # Keep the turn when a pre-capture confirmation was pending so a
                # late response.done can still advance to capturing.
                if turn is None or not turn.capture_after_speech:
                    self.context.pose_turn = None
                await self._configure_listening()

    def mark_pose_tool_result(self, *, complete: bool) -> None:
        turn = self.context.pose_turn
        if turn is None or turn.phase != "assessing":
            return
        turn.tool_result_received = True
        turn.pending_capture = turn.pending_capture or complete

    async def handle_pose_assessment_done(self) -> bool:
        turn = self.context.pose_turn
        pose = self.context.pose_context
        if turn is None or turn.phase != "assessing":
            return False
        if not turn.tool_result_received or pose is None:
            if turn.pending_tool_submit is not None:
                call_id, output = turn.pending_tool_submit
                turn.pending_tool_submit = None
                await self.omni.submit_tool_result(call_id, output, create_followup=False)
            self.context.pose_turn = None
            self.context.response_in_flight = False
            await self._configure_listening()
            return False
        if turn.pending_capture:
            turn.capture_after_speech = True
            turn.pending_capture = False
        turn.phase = "speaking"
        instructions = self.prompts.render(
            "action.S3.speak",
            guidance_intent=pose.last_guidance_intent,
            last_spoken_text=pose.last_spoken_text or "（尚无）",
            pose_context=pose.snapshot_for_prompt(),
            capture_after_speech="true" if turn.capture_after_speech else "false",
        )
        # Audible S3 responses keep server VAD enabled so user speech can barge in.
        await self._configure_pose_speech()
        if turn.pending_tool_submit is not None:
            call_id, output = turn.pending_tool_submit
            turn.pending_tool_submit = None
            await self.omni.submit_tool_result(call_id, output, create_followup=False)
        LOGGER.info(
            "s3_speech_turn_started",
            extra={
                "output_audio_enabled": self.omni.output_audio_enabled,
                "guidance_intent": pose.last_guidance_intent,
                "capture_after_speech": turn.capture_after_speech,
                "session_id": self.context.session_id,
            },
        )
        await self.omni.create_response(instructions, output_audio=True)
        return True

    async def handle_pose_speech_done(self, text: str = "") -> None:
        turn = self.context.pose_turn
        pose = self.context.pose_context
        if turn is None or turn.phase != "speaking" or pose is None:
            return
        pose.last_spoken_text = text
        pose.logical_turn += 1
        if not self.guidance_limit_reached:
            self.context.guidance_turns.append(GuidanceTurn(time.time(), turn.source, text))
        post_capture = turn.post_capture_speech
        capture_after_speech = turn.capture_after_speech
        self.context.pose_turn = None
        self.context.response_in_flight = False
        if post_capture and self.context.photo_id:
            await self._enter_review("pose_capture_complete")
            return
        if capture_after_speech:
            await self.start_pose_capture("goal_complete")
            return
        await self._configure_listening()

    async def handle_pose_capture_result(self, output: dict[str, Any]) -> bool:
        turn = self.context.pose_turn
        if turn is None or turn.phase != "capturing":
            return False
        if not output.get("ok"):
            turn.pending_capture = False
            self.context.pose_turn = None
            self.context.response_in_flight = False
            await self._say_and_wait(self.prompts.get("action.S3.capture_failed"))
            await self._configure_listening()
            return False
        if not output.get("quality_ok"):
            # Speak the retry hint as a tracked speech turn so its response.done
            # restores listening; resetting response_in_flight here would let the
            # guidance interval race a new assessment over the unfinished audio.
            turn.phase = "speaking"
            turn.pending_capture = False
            await self._configure_pose_speech()
            await self.omni.create_response(
                self.prompts.render(
                    "action.S3.quality_failed",
                    quality_reason="质量不足",
                ),
                output_audio=True,
            )
            return True
        turn.phase = "speaking"
        turn.pending_capture = False
        turn.post_capture_speech = True
        await self._configure_pose_speech()
        await self.omni.create_response(self.prompts.get("action.S3.captured"), output_audio=True)
        return True

    async def handle_response_done(self) -> None:
        """Finalize a non-S3 response (S2/S5/S6).

        S3 response completion is phase-aware and routed by the runtime to
        handle_pose_assessment_done / handle_pose_speech_done / capture handling.
        """
        self.context.response_in_flight = False

    async def run_capture_from_pose(self) -> tuple[CaptureResult, bool]:
        """Capture during S3 complete flow without a separate shoot state."""
        result: CaptureResult | None = None
        for attempt in range(self.config.operation_retries + 1):
            result = await self.camera.capture("photo")
            LOGGER.info(
                "capture_result",
                extra={
                    "attempt": attempt + 1,
                    "ok": result.ok,
                    "photo_id": result.photo_id or None,
                    "path": str(result.path) if result.ok else None,
                    "error": result.error,
                    "source": "s3_complete",
                },
            )
            if result.ok:
                break
            LOGGER.warning("capture_retry", extra={"attempt": attempt + 1, "error": result.error})
        assert result is not None
        if not result.ok:
            if self.context.retake_count < self.context.max_retake:
                self.context.retake_count += 1
            return result, False

        self.context.photo_id = result.photo_id
        self.context.photo_path = result.path
        self.delivery.register_photo(result.photo_id, result.path)
        if self.config.skip_quality_check:
            LOGGER.info(
                "quality_result",
                extra={"photo_id": result.photo_id, "ok": True, "reason": "skipped_for_demo"},
            )
            return result, True
        quality = self.quality_checker.check(result.frame)
        LOGGER.info(
            "quality_result",
            extra={"photo_id": result.photo_id, "ok": quality.ok, "reason": quality.reason},
        )
        if not quality.ok and self.context.retake_count < self.context.max_retake:
            self.context.retake_count += 1
            return result, False
        return result, True

    async def _enter_review(self, reason: str) -> None:
        await self._enter(State.REVIEW, reason)
        shown = False
        if self.context.photo_id:
            for attempt in range(self.config.operation_retries + 1):
                if await self.delivery.show(self.context.photo_id):
                    shown = True
                    break
                LOGGER.warning("show_retry", extra={"attempt": attempt + 1})
        if not shown:
            await self._say_and_wait(self.prompts.get("action.S5.show_failed"))
        await self.omni.create_response(self.prompts.get("action.S5.ask_review"))

    async def start_review(self, reason: str = "manual_review") -> None:
        if not self.context.photo_id:
            raise RuntimeError("review requires photo_id")
        await self._enter_review(reason)

    async def run_delivery(self) -> DeliveryResult:
        if self.context.state is not State.DELIVER or not self.context.photo_id:
            raise RuntimeError("delivery requires S6 and a photo_id")
        result: DeliveryResult | None = None
        try:
            for attempt in range(self.config.operation_retries + 1):
                result = await self.delivery.deliver(self.context.photo_id)
                LOGGER.info(
                    "delivery_result",
                    extra={
                        "attempt": attempt + 1,
                        "ok": result.ok,
                        "photo_id": result.photo_id,
                        "photo_url": result.photo_url or None,
                        "error": result.error,
                    },
                )
                if result.ok:
                    self.context.photo_url = result.photo_url
                    break
                LOGGER.warning("delivery_retry", extra={"attempt": attempt + 1, "error": result.error})
            assert result is not None
            if result.ok:
                await self._say_and_wait(self.prompts.get("action.S6.delivered"))
            else:
                await self._say_and_wait(
                    self.prompts.render(
                        "action.S6.delivery_failed", photo_id=self.context.photo_id
                    )
                )
            return result
        finally:
            await self._finish_session("delivered" if result and result.ok else "delivery_failed")

    async def _finish_session(self, reason: str) -> None:
        if self.context.session_id:
            # Stop audio producers before waiting on the WebSocket write lock.
            self.context.session_id = None
            try:
                await self.omni.end_session(reason)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("end_session_failed", extra={"error": str(exc)})
            finally:
                try:
                    await self.omni.close()
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("omni_close_failed", extra={"error": str(exc)})
        await self._cancel_background_tasks()
        self.context.reset()
        self.guidance_limit_reached = False
        self._qualified_wake_frames = 0
        self._wake_rearm_required = True
        LOGGER.info("session_reset", extra={"reason": reason})
        LOGGER.info(
            "resource_release",
            extra={"reason": reason, "background_task_count": self.background_task_count},
        )

    async def _say_and_wait(self, instructions: str, timeout: float = 10.0) -> None:
        vad = getattr(self.omni, "vad_enabled", True)
        await self.omni.configure(enable_vad=vad, output_audio=True, tools=[])
        await self.omni.create_response(instructions, output_audio=True)
        try:
            await self.omni.wait_response_done(timeout=timeout)
        except TimeoutError:
            LOGGER.warning("response_audio_timeout", extra={"instructions_kind": "session_closing"})

    async def finish_session(self, reason: str) -> None:
        await self._finish_session(reason)

    async def _cancel_background_tasks(self) -> None:
        tasks = [task for task in self._background_tasks if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._background_tasks.clear()

    async def close(self) -> None:
        try:
            await self._finish_session("shutdown")
        finally:
            try:
                await self.camera.close()
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("camera_close_failed", extra={"error": str(exc)})
