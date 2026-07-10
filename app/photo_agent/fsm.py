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
    SessionContext,
    State,
    UserIntent,
)
from app.photo_agent.prompts import PromptSource, StaticPromptSource

LOGGER = logging.getLogger("photomate.photo_agent")
T = TypeVar("T")

STATE_PROMPT_KEYS = {
    State.ASK_INTENT: "state.S2",
    State.POSE_GUIDANCE: "state.S3",
    State.SHOOT: "state.S4",
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


def classify_user_text(text: str) -> UserIntent:
    normalized = text.strip().lower()
    if any(token in normalized for token in ("不满意", "重拍", "再来一张")):
        return UserIntent.RETAKE
    if any(token in normalized for token in ("不用", "不要", "不了", "拒绝")):
        return UserIntent.DECLINE
    if any(token in normalized for token in ("满意", "可以的", "挺好", "很好")):
        return UserIntent.SATISFIED
    if any(token in normalized for token in ("拍吧", "可以拍", "好了", "ok", "准备好")):
        return UserIntent.READY
    if any(token in normalized for token in ("要", "好啊", "帮我拍", "来一张", "可以")):
        return UserIntent.ACCEPT
    return UserIntent.UNKNOWN


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
        prompt_key = STATE_PROMPT_KEYS.get(state)
        if prompt_key and self.context.session_id:
            await self.omni.inject_context(self.prompts.get(prompt_key))

    async def enter_manual_state(self, state: State) -> None:
        if state is State.IDLE:
            raise ValueError("manual state must be S1-S6")
        await self._enter(state, "manual_acceptance")

    async def handle_user_text(self, text: str) -> None:
        intent = classify_user_text(text)
        state = self.context.state
        if state is State.ASK_INTENT:
            if intent in (UserIntent.ACCEPT, UserIntent.READY):
                self.guidance_limit_reached = False
                await self._enter(State.POSE_GUIDANCE, "user_accepted")
            elif intent is UserIntent.DECLINE:
                await self._say_and_wait(self.prompts.get("action.S2.decline"))
                await self._finish_session("user_declined")
        elif state is State.POSE_GUIDANCE and intent in (UserIntent.READY, UserIntent.SATISFIED):
            await self._enter(State.SHOOT, "user_ready")
        elif state is State.REVIEW:
            if intent is UserIntent.RETAKE:
                self.guidance_limit_reached = False
                await self._enter(State.POSE_GUIDANCE, "user_requested_retake")
            elif intent in (UserIntent.SATISFIED, UserIntent.ACCEPT, UserIntent.READY):
                await self._enter(State.DELIVER, "user_satisfied")

    async def handle_timeout(self) -> None:
        if self.context.state is State.ASK_INTENT:
            if self.context.ask_timeout_count == 0:
                self.context.ask_timeout_count = 1
                await self.omni.create_response(self.prompts.get("action.S2.ask_retry"))
            else:
                await self._finish_session("timeout")
        elif self.context.state is State.REVIEW:
            await self._enter(State.DELIVER, "review_timeout_default_accept")

    async def guidance_tick(self) -> bool:
        if self.context.state is not State.POSE_GUIDANCE or self.context.response_in_flight:
            return False
        if len(self.context.guidance_turns) >= self.context.max_guidance_turns:
            if not self.guidance_limit_reached:
                self.guidance_limit_reached = True
                self.context.response_in_flight = True
                await self.omni.create_response(self.prompts.get("action.S3.guidance_limit"))
                return True
            return False
        frame = await self.camera.get_frame()
        await self.omni.append_image(frame)
        self.context.response_in_flight = True
        await self.omni.create_response(self.prompts.get("action.S3.guidance"))
        return True

    async def handle_speech_started(self) -> None:
        if self.context.response_in_flight:
            await self.omni.cancel_response()
            self.context.response_in_flight = False

    async def handle_response_done(self, text: str = "") -> None:
        if self.context.state is State.POSE_GUIDANCE and not self.guidance_limit_reached:
            self.context.guidance_turns.append(GuidanceTurn(time.time(), "interval", text))
        self.context.response_in_flight = False
        if (
            self.context.state is State.POSE_GUIDANCE
            and len(self.context.guidance_turns) >= self.context.max_guidance_turns
            and not self.guidance_limit_reached
        ):
            self.guidance_limit_reached = True
            self.context.response_in_flight = True
            await self.omni.create_response(self.prompts.get("action.S3.guidance_limit"))

    async def run_shoot(self) -> CaptureResult:
        if self.context.state is not State.SHOOT:
            raise RuntimeError(f"cannot shoot from {self.context.state.value}")
        await self.omni.create_response(self.prompts.get("action.S4.countdown"))
        try:
            await self.omni.wait_response_done(timeout=10.0)
        except TimeoutError:
            LOGGER.warning("countdown_audio_timeout")

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
                },
            )
            if result.ok:
                break
            LOGGER.warning("capture_retry", extra={"attempt": attempt + 1, "error": result.error})
        assert result is not None
        if not result.ok:
            if self.context.retake_count < self.context.max_retake:
                self.context.retake_count += 1
            await self._say_and_wait(self.prompts.get("action.S4.capture_failed"))
            await self._enter(State.POSE_GUIDANCE, "capture_failed")
            return result

        self.context.photo_id = result.photo_id
        self.context.photo_path = result.path
        self.delivery.register_photo(result.photo_id, result.path)
        quality = self.quality_checker.check(result.frame)
        LOGGER.info(
            "quality_result",
            extra={"photo_id": result.photo_id, "ok": quality.ok, "reason": quality.reason},
        )
        if not quality.ok and self.context.retake_count < self.context.max_retake:
            self.context.retake_count += 1
            await self.omni.create_response(
                self.prompts.render(
                    "action.S4.quality_failed",
                    quality_reason=quality.reason or "质量不足",
                )
            )
            await self._enter(State.POSE_GUIDANCE, "quality_failed")
            return result
        await self._enter_review("quality_ok" if quality.ok else "quality_limit_reached")
        return result

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
        await self.omni.create_response(instructions)
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
