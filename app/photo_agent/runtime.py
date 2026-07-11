"""Mock and local-real runtime composition."""

from __future__ import annotations

import subprocess
import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from app.photo_agent.fsm import FSMConfig, PhotoAgentFSM
from app.photo_agent.dispatcher import FunctionCallDispatcher
from app.photo_agent.mocks import MockCamera, MockDelivery, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import (
    CaptureResult,
    DeliveryResult,
    PoseTurnState,
    QualityResult,
    State,
    WakeSignal,
)
from app.photo_agent.prompts import PromptRegistry, PromptSource, StaticPromptSource

LOGGER = logging.getLogger("photomate.photo_agent.runtime")


def _is_recoverable_omni_error(error: dict) -> bool:
    message = str(error.get("message", "")).lower()
    return "append image before append audio" in message


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str = "mock"
    model: str = "qwen3.5-omni-flash-realtime"
    workspace_host: str = "llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com"
    api_key: str = ""
    voice: str = "Tina"
    camera_index: int = 0
    camera_rotation_deg: int = 0
    microphone_index: int | None = None
    speaker_index: int | None = None
    photo_dir: Path = Path("data/photos")
    base_url: str = "http://127.0.0.1:8000"
    guidance_interval_s: float = 5.0
    skip_quality_check: bool = True


class PhotoAgentRuntime:
    def __init__(
        self,
        fsm: PhotoAgentFSM,
        microphone: object | None = None,
        resources: list[object] | None = None,
        device_info: dict[str, str] | None = None,
        fallback_notifier: object | None = None,
        prompt_source: PromptSource | None = None,
    ) -> None:
        self.fsm = fsm
        self.omni = fsm.omni
        self.microphone = microphone
        self.resources = resources or []
        self.device_info = device_info or {}
        if fallback_notifier is None:
            from app.photo_agent.fallback import NullFallbackNotifier

            fallback_notifier = NullFallbackNotifier()
        self.fallback_notifier = fallback_notifier
        self.dispatcher = FunctionCallDispatcher(fsm)
        self.prompt_source = prompt_source or getattr(fsm, "prompts", StaticPromptSource())
        self.active_prompt_version = self.prompt_source.version
        self._stopped = asyncio.Event()
        self._last_guidance_at = 0.0
        self._state_seen = fsm.context.state
        self._state_since = time.monotonic()
        self._wall_clock = time.time
        self.session_max_s = 115 * 60.0
        # How long the finished share page stays up before the next loop starts.
        self.share_linger_s = 60.0
        self._pending_assistant_text = ""

    async def handle_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "speech_started":
            LOGGER.info(
                "speech_started",
                extra={
                    "state": self.fsm.context.state.value,
                    "response_in_flight": self.fsm.context.response_in_flight,
                    "session_id": self.fsm.context.session_id,
                },
            )
            await self.fsm.handle_speech_started()
            if self.fsm.context.state is State.POSE_GUIDANCE:
                self._pending_assistant_text = ""
            elif self.fsm.context.state is State.ASK_INTENT:
                # Restart the ask fallback window whenever the user speaks, so a
                # responsive user is never interrupted by the re-ask prompt.
                self._state_since = time.monotonic()
        elif event_type == "response_created":
            self.fsm.context.response_in_flight = True
            turn = self.fsm.context.pose_turn
            if self.fsm.context.state is State.POSE_GUIDANCE and turn is None:
                turn = PoseTurnState(source="user_vad")
                self.fsm.context.pose_turn = turn
            if self.fsm.context.state is State.POSE_GUIDANCE and turn is not None:
                if turn.phase == "assessing":
                    turn.assessment_response_id = event.get("response_id")
                elif turn.phase == "capturing":
                    turn.capture_response_id = event.get("response_id")
                elif turn.phase == "speaking":
                    turn.speech_response_id = event.get("response_id")
            LOGGER.info(
                "response_created",
                extra={
                    "response_id": event.get("response_id"),
                    "session_id": self.fsm.context.session_id,
                },
            )
        elif event_type == "assistant_text":
            turn = self.fsm.context.pose_turn
            expected_id = turn.speech_response_id if turn and turn.phase == "speaking" else None
            response_id = event.get("response_id")
            if (
                event.get("source") != "text"
                and (not expected_id or not response_id or response_id == expected_id)
            ):
                self._pending_assistant_text += str(event.get("text") or "")
        elif event_type == "response_done":
            turn = self.fsm.context.pose_turn
            LOGGER.info(
                "response_done",
                extra={
                    "state": self.fsm.context.state.value,
                    "session_id": self.fsm.context.session_id,
                    "response_id": event.get("response_id"),
                    "pose_phase": turn.phase if turn else None,
                },
            )
            response_id = event.get("response_id")
            if self.fsm.context.state is State.POSE_GUIDANCE and turn is not None:
                known_ids = {
                    turn.assessment_response_id,
                    turn.capture_response_id,
                    turn.speech_response_id,
                } - {None}
                is_assessment = response_id == turn.assessment_response_id or (
                    not known_ids and turn.phase == "assessing"
                )
                is_capture = response_id == turn.capture_response_id or (
                    not known_ids and turn.phase == "capturing"
                )
                is_speech = response_id == turn.speech_response_id or (
                    not known_ids and turn.phase == "speaking"
                )
                if is_assessment:
                    self._pending_assistant_text = ""
                    started_speech = await self.fsm.handle_pose_assessment_done()
                    if not started_speech:
                        self._last_guidance_at = time.monotonic()
                elif is_capture:
                    # A capture response.done can arrive after capture_photo has
                    # already started the post-capture speech. In that case it
                    # belongs to the old response and must not finish speech.
                    if turn.phase == "capturing":
                        self._pending_assistant_text = ""
                        self.fsm.context.response_in_flight = False
                        LOGGER.warning(
                            "capture_tool_missing",
                            extra={"session_id": self.fsm.context.session_id},
                        )
                        self.fsm.context.pose_turn = None
                        await self.fsm.omni.configure(enable_vad=True, output_audio=True)
                        self._last_guidance_at = time.monotonic()
                elif is_speech:
                    if (
                        event.get("audio_delta_count") == 0
                        and turn.phase == "speaking"
                        and not turn.speech_retry_used
                        and (pose := self.fsm.context.pose_context) is not None
                        and (turn.post_capture_speech or pose.last_guidance_intent)
                    ):
                        turn.speech_retry_used = True
                        self._pending_assistant_text = ""
                        await self.fsm.retry_pose_speech(
                            pose.last_guidance_intent or "我拍好啦"
                        )
                        self._track_state()
                        return
                    text = self._pending_assistant_text
                    self._pending_assistant_text = ""
                    await self.fsm.handle_pose_speech_done(text)
                    self._last_guidance_at = time.monotonic()
                    self._track_state()
                elif known_ids:
                    LOGGER.warning(
                        "stale_response_done",
                        extra={
                            "response_id": response_id,
                            "assessment_response_id": turn.assessment_response_id,
                            "capture_response_id": turn.capture_response_id,
                            "speech_response_id": turn.speech_response_id,
                            "pose_phase": turn.phase,
                        },
                    )
            elif self.fsm.context.state is not State.POSE_GUIDANCE:
                await self.fsm.handle_response_done()
        elif event_type == "tool_call":
            call = event["tool_call"]
            LOGGER.info(
                "function_call",
                extra={
                    "function_name": call.name,
                    "call_id": call.call_id,
                    "arguments": call.arguments,
                    "session_id": self.fsm.context.session_id,
                },
            )
            intent_call = self.dispatcher.is_intent_call(call)
            pose_call = call.name == "report_pose_turn"
            capture_call = call.name == "capture_photo"
            turn = self.fsm.context.pose_turn
            event_response_id = event.get("response_id")
            user_vad_capture_request = bool(
                capture_call
                and turn is not None
                and turn.source == "user_vad"
                and turn.phase == "assessing"
            )
            pose_response_mismatch = bool(
                pose_call
                and turn
                and turn.assessment_response_id
                and event_response_id
                and turn.assessment_response_id != event_response_id
            )
            if pose_call and (turn is None or turn.phase != "assessing"):
                output = {"ok": False, "error": "no_active_pose_assessment"}
            elif (
                capture_call
                and self.fsm.context.state is State.POSE_GUIDANCE
                and (turn is None or turn.phase != "capturing")
                and not user_vad_capture_request
            ):
                output = {"ok": False, "error": "no_active_pose_capture"}
            elif pose_response_mismatch:
                output = {"ok": False, "error": "stale_pose_response"}
            else:
                output = (
                    self.dispatcher.validate_intent(call)
                    if intent_call
                    else await self.dispatcher.dispatch(call)
                )
            LOGGER.info(
                "function_call_result",
                extra={"function_name": call.name, "call_id": call.call_id, "output": output},
            )
            if capture_call and self.fsm.context.state is State.POSE_GUIDANCE and turn is not None:
                await self.omni.submit_tool_result(call.call_id, output, create_followup=False)
                if not output.get("deferred"):
                    await self.fsm.handle_pose_capture_result(output)
            elif pose_call and turn is not None:
                if turn.pending_tool_submit is not None:
                    old_call_id, old_output = turn.pending_tool_submit
                    await self.omni.submit_tool_result(
                        old_call_id, old_output, create_followup=False
                    )
                turn.pending_tool_submit = (call.call_id, output)
                if output["ok"]:
                    self.fsm.mark_pose_tool_result(complete=bool(output["complete"]))
            else:
                await self.omni.submit_tool_result(
                    call.call_id,
                    output,
                    create_followup=not intent_call or not output["ok"],
                )
            if intent_call and output["ok"]:
                await self.dispatcher.apply_intent(call)
            self._track_state()
        elif event_type == "error":
            error = event.get("error", {})
            if _is_recoverable_omni_error(error):
                LOGGER.warning("omni_recoverable_error", extra={"event": event})
                if "append image before append audio" in str(error.get("message", "")).lower():
                    await self.omni.prime_audio()
            else:
                LOGGER.error("omni_event", extra={"event": event})
                try:
                    await self.fallback_notifier.notify(
                        "实时语音服务暂时不可用，本次服务已安全结束，请稍后再试。"
                    )
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("fallback_notification_failed", extra={"error": str(exc)})
                await self.fsm.finish_session("omni_error")
                self._track_state()
        elif event_type == "disconnected":
            LOGGER.error("omni_event", extra={"event": event})
            try:
                await self.fallback_notifier.notify(
                    "实时语音服务暂时不可用，本次服务已安全结束，请稍后再试。"
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("fallback_notification_failed", extra={"error": str(exc)})
            await self.fsm.finish_session("omni_disconnected")
            self._track_state()

    async def _audio_loop(self) -> None:
        if self.microphone is None:
            return
        while not self._stopped.is_set():
            if not self.fsm.context.session_id:
                await asyncio.sleep(0.05)
                continue
            try:
                # PyAudio reads one 100 ms chunk. Keeping that bounded read in this
                # task avoids an orphan executor thread when the session is cancelled.
                chunk = self.microphone.read_chunk()
                if not self.fsm.context.session_id:
                    continue
                # When server VAD is off we are not expecting mic-driven turns (S3
                # coach frames, or the S6 share-page linger); streaming mic audio
                # would only pollute the buffer, so skip it.
                if hasattr(self.omni, "vad_enabled") and not self.omni.vad_enabled:
                    await asyncio.sleep(0.05)
                    continue
                await self.omni.append_audio(chunk)
                await asyncio.sleep(0)
            except Exception as exc:  # noqa: BLE001 - live device boundary
                if not self.fsm.context.session_id:
                    continue
                LOGGER.warning(
                    "audio_stream_failed",
                    extra={"session_id": self.fsm.context.session_id, "error": str(exc)},
                )
                await asyncio.sleep(0.05)

    async def _frame_loop(self) -> None:
        while not self._stopped.is_set():
            state_val = self.fsm.context.state.value
            vad_on = getattr(self.omni, "vad_enabled", True)
            should_feed = (
                self.fsm.context.session_id
                and (
                    state_val in ("S2", "S5")
                    or (state_val == "S3" and vad_on)
                )
            )
            if should_feed:
                try:
                    frame = await self.fsm.camera.get_frame()
                    await self.omni.append_image(frame)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("frame_feed_failed", extra={"error": str(exc)})
            await asyncio.sleep(1.0)

    def _track_state(self) -> None:
        if self.fsm.context.state is not self._state_seen:
            self._state_seen = self.fsm.context.state
            self._state_since = time.monotonic()
            if self._state_seen is State.POSE_GUIDANCE:
                self._last_guidance_at = 0.0

    async def _control_step(self) -> None:
        from app.photo_agent.models import State

        await self.sync_prompt_version()
        state = self.fsm.context.state
        if (
            self.fsm.context.session_id
            and self.fsm.context.session_started_at > 0
            and self._wall_clock() - self.fsm.context.session_started_at >= self.session_max_s
        ):
            LOGGER.warning(
                "session_limit_reached",
                extra={"session_id": self.fsm.context.session_id, "limit_s": self.session_max_s},
            )
            await self.fsm.finish_session("session_limit")
            self._track_state()
            return
        if state is State.IDLE:
            await self.fsm.start()
        elif state is State.DETECT_INTENT:
            await self.fsm.poll_wake()
        elif state is State.POSE_GUIDANCE:
            now = time.monotonic()
            if now - self._last_guidance_at >= self.fsm.context.guidance_interval_s:
                await self.fsm.guidance_tick()
        elif (
            state is State.ASK_INTENT
            and not self.fsm.context.response_in_flight
            and time.monotonic() - self._state_since >= 12.0
        ):
            await self.fsm.handle_timeout()
            self._state_since = time.monotonic()
        elif state is State.REVIEW and time.monotonic() - self._state_since >= 15.0:
            await self.fsm.handle_timeout()
        elif state is State.DELIVER:
            now = time.monotonic()
            if self.fsm.context.delivered_at <= 0.0:
                if now - self._state_since >= 2.0:
                    await self.fsm.run_delivery()
            elif now - self.fsm.context.delivered_at >= self.share_linger_s:
                # Share window elapsed: reset and start the next patrol loop.
                await self.fsm.finish_session("share_linger_timeout")
        self._track_state()

    async def sync_prompt_version(self) -> None:
        if (
            not self.fsm.context.session_id
            or self.fsm.context.response_in_flight
            or self.active_prompt_version == self.prompt_source.version
        ):
            return
        await self.omni.update_instructions(self.prompt_source.get("system.base"))
        self.active_prompt_version = self.prompt_source.version

    async def run_forever(self) -> None:
        audio_task = asyncio.create_task(self._audio_loop(), name="photo-agent-audio")
        frame_task = asyncio.create_task(self._frame_loop(), name="photo-agent-frames")
        try:
            while not self._stopped.is_set():
                await self._control_step()
                if self.fsm.context.session_id and hasattr(self.omni, "next_event"):
                    try:
                        event = await self.omni.next_event(timeout=0.1)
                    except TimeoutError:
                        continue
                    await self.handle_event(event)
                else:
                    await asyncio.sleep(0.1)
        finally:
            self._stopped.set()
            for task in (audio_task, frame_task):
                task.cancel()
            await asyncio.gather(audio_task, frame_task, return_exceptions=True)
            await self._cleanup_resources()

    def stop(self) -> None:
        self._stopped.set()

    async def _cleanup_resources(self) -> None:
        async def close_sync_resource(name: str, resource: object | None) -> None:
            if resource is None:
                return
            close = getattr(resource, "close", None)
            if close is None:
                return
            try:
                await asyncio.to_thread(close)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("resource_close_failed", extra={"resource": name, "error": str(exc)})

        await close_sync_resource("microphone", self.microphone)
        try:
            await self.fsm.close()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("fsm_close_failed", extra={"error": str(exc)})
        for index, resource in enumerate(self.resources):
            await close_sync_resource(f"resource_{index}", resource)

    async def _connect_manual_session(self, state: State) -> None:
        session_id = await self.omni.connect()
        self.fsm.context.session_id = session_id
        self.fsm.context.session_started_at = self._wall_clock()
        await self.omni.configure()
        self.active_prompt_version = self.prompt_source.version
        await self.omni.prime_audio()
        await self.fsm.enter_manual_state(state)
        self._track_state()

    async def _prepare_manual_photo(self) -> DeliveryResult:
        capture = await self.fsm.camera.capture("photo")
        if not capture.ok:
            return DeliveryResult("", "", False, capture.error or "capture_failed")
        self.fsm.delivery.register_photo(capture.photo_id, capture.path)
        self.fsm.context.photo_id = capture.photo_id
        self.fsm.context.photo_path = capture.path
        return await self.fsm.delivery.deliver(capture.photo_id)

    async def _run_until_states(
        self, stop_states: set[State], timeout: float | None = None
    ) -> State:
        audio_task = asyncio.create_task(self._audio_loop(), name="manual-photo-agent-audio")
        frame_task = asyncio.create_task(self._frame_loop(), name="manual-photo-agent-frames")
        deadline = None if timeout is None else time.monotonic() + timeout
        try:
            while deadline is None or time.monotonic() < deadline:
                await self._control_step()
                if self.fsm.context.state in stop_states:
                    return self.fsm.context.state
                if self.fsm.context.session_id and hasattr(self.omni, "next_event"):
                    try:
                        event = await self.omni.next_event(timeout=0.1)
                    except TimeoutError:
                        continue
                    await self.handle_event(event)
                    if self.fsm.context.state in stop_states:
                        return self.fsm.context.state
                else:
                    await asyncio.sleep(0.1)
            raise TimeoutError(f"manual state timed out after {timeout}s")
        finally:
            self._stopped.set()
            for task in (audio_task, frame_task):
                task.cancel()
            await asyncio.gather(audio_task, frame_task, return_exceptions=True)

    async def run_manual_state(self, state: str, timeout: float | None = None) -> dict[str, object]:
        requested = State(state)
        result: dict[str, object] = {"ok": False, "tested_state": state}
        try:
            if requested is State.DETECT_INTENT:
                await self.fsm.start()
                final_state = await self._run_until_states({State.ASK_INTENT, State.IDLE}, timeout)
            else:
                await self._connect_manual_session(requested)
                if requested is State.ASK_INTENT:
                    await self.omni.create_response(
                        self.prompt_source.get("action.S2.ask_initial")
                    )
                    final_state = await self._run_until_states({State.POSE_GUIDANCE, State.IDLE}, timeout)
                elif requested is State.POSE_GUIDANCE:
                    final_state = await self._run_until_states({State.REVIEW}, timeout)
                elif requested is State.REVIEW:
                    preview = await self._prepare_manual_photo()
                    if not preview.ok:
                        return {**result, "error": preview.error}
                    await self.fsm.start_review("manual_review")
                    result["photo_url"] = preview.photo_url
                    final_state = await self._run_until_states({State.DELIVER, State.POSE_GUIDANCE}, timeout)
                elif requested is State.DELIVER:
                    preview = await self._prepare_manual_photo()
                    if not preview.ok:
                        return {**result, "error": preview.error}
                    delivery = await self.fsm.run_delivery()
                    result["photo_url"] = delivery.photo_url
                    final_state = State.IDLE
                else:
                    raise ValueError(f"unsupported manual state: {state}")
            result.update({"ok": True, "result_state": final_state.value})
            return result
        except Exception as exc:  # noqa: BLE001 - manual acceptance boundary
            result["error"] = str(exc)
            result["result_state"] = self.fsm.context.state.value
            return result
        finally:
            await self._cleanup_resources()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_self_check(
    config: RuntimeConfig,
    *,
    device_info: dict[str, str] | None = None,
    missing_real_dependencies: list[str] | None = None,
) -> dict:
    real = config.mode == "local-real"
    hardware_reserved = config.mode == "hardware-real"
    devices = device_info or {}
    if config.mode == "mock" and not devices:
        devices = {
            "camera": "mock camera fixture",
            "microphone": "mock microphone fixture",
            "speaker": "mock speaker fixture",
        }
    elif hardware_reserved and not devices:
        devices = {
            "camera": "reserved Jetson/Insta360 adapter",
            "microphone": "reserved robot audio input adapter",
            "speaker": "reserved robot audio output adapter",
        }
    if missing_real_dependencies is None:
        if real:
            missing_real_dependencies = []
        elif hardware_reserved:
            missing_real_dependencies = ["Jetson deployment", "Insta360 SDK", "robot audio", "Galbot integration"]
        else:
            missing_real_dependencies = ["Omni", "camera", "microphone", "speaker"]
    adapter_mode = "real" if real else "reserved" if hardware_reserved else "mock"
    return {
        "git_branch": _git_value("branch", "--show-current"),
        "git_commit": _git_value("rev-parse", "--short", "HEAD"),
        "mode": config.mode,
        "state": "S0",
        "model": config.model,
        "api_host": config.workspace_host,
        "api_key_present": bool(config.api_key),
        "camera": devices.get("camera", f"camera:{config.camera_index}"),
        "microphone": devices.get(
            "microphone",
            f"microphone:{config.microphone_index}" if config.microphone_index is not None else "default input",
        ),
        "speaker": devices.get(
            "speaker",
            f"speaker:{config.speaker_index}" if config.speaker_index is not None else "default output",
        ),
        "photo_dir": str(config.photo_dir),
        "base_url": config.base_url,
        "adapters": {
            "omni": adapter_mode,
            "camera": adapter_mode,
            "audio_input": adapter_mode,
            "audio_output": adapter_mode,
            "delivery": "local-real" if real else adapter_mode,
        },
        "missing_real_dependencies": missing_real_dependencies,
    }


def build_local_runtime(
    config: RuntimeConfig,
    *,
    camera_factory: Callable[..., object] | None = None,
    microphone_factory: Callable[..., object] | None = None,
    speaker_factory: Callable[..., object] | None = None,
    prompt_source: PromptSource | None = None,
) -> PhotoAgentRuntime:
    if config.mode != "local-real":
        raise ValueError("build_local_runtime requires mode=local-real")
    if not config.api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is required for local-real mode")

    from app.photo_agent.audio import (
        PyAudioMicrophone,
        PyAudioSpeaker,
        resolve_audio_device_indices,
    )
    from app.photo_agent.camera import FaceWakeDetector, OpenCVCamera, OpenCVQualityChecker
    from app.photo_agent.delivery import FileDeliveryAdapter, GLOBAL_PHOTO_STORE
    from app.photo_agent.fallback import SystemFallbackNotifier
    from app.photo_agent.omni import DashscopeOmniClient, OmniSettings
    from app.photo_agent.storage import build_storage_uploader
    from app.config import CONFIG_DIR, ROOT_DIR

    camera_builder = camera_factory or OpenCVCamera
    microphone_builder = microphone_factory or PyAudioMicrophone
    speaker_builder = speaker_factory or PyAudioSpeaker
    camera = None
    speaker = None
    microphone = None
    try:
        camera = camera_builder(
            config.camera_index,
            config.photo_dir,
            rotation_deg=config.camera_rotation_deg,
        )
        open_camera = getattr(camera, "open", None)
        if open_camera:
            open_camera()
        microphone_index, speaker_index = resolve_audio_device_indices(
            microphone_index=config.microphone_index,
            speaker_index=config.speaker_index,
        )
        speaker = speaker_builder(device_index=speaker_index)
        microphone = microphone_builder(device_index=microphone_index)
    except Exception:
        if microphone is not None and getattr(microphone, "close", None):
            microphone.close()
        if speaker is not None and getattr(speaker, "close", None):
            speaker.close()
        if camera is not None and getattr(camera, "close_sync", None):
            camera.close_sync()
        raise
    assert camera is not None and speaker is not None and microphone is not None
    prompts = prompt_source or PromptRegistry(
        CONFIG_DIR / "photo_agent_prompts.yaml",
        ROOT_DIR / "data" / "photo_agent_prompt_history",
    )
    omni = DashscopeOmniClient(
        OmniSettings(
            api_key=config.api_key,
            workspace_host=config.workspace_host,
            model=config.model,
            voice=config.voice,
        ),
        audio_sink=speaker,
        prompt_source=prompts,
    )
    fsm = PhotoAgentFSM(
        wake_detector=FaceWakeDetector(camera),
        omni=omni,
        camera=camera,
        quality_checker=OpenCVQualityChecker(),
        delivery=FileDeliveryAdapter(GLOBAL_PHOTO_STORE, config.base_url),
        config=FSMConfig(
            guidance_interval_s=config.guidance_interval_s,
            skip_quality_check=config.skip_quality_check,
        ),
        prompts=prompts,
        storage=build_storage_uploader(),
    )
    return PhotoAgentRuntime(
        fsm,
        microphone=microphone,
        resources=[speaker],
        device_info={
            "camera": str(getattr(camera, "device_name", f"camera:{config.camera_index}")),
            "microphone": str(getattr(microphone, "device_name", "default input")),
            "speaker": str(getattr(speaker, "device_name", "default output")),
        },
        fallback_notifier=SystemFallbackNotifier(),
        prompt_source=prompts,
    )


async def _finish_mock_s3_capture(fsm: PhotoAgentFSM) -> None:
    await fsm.start_pose_capture("mock")
    result, quality_ok = await fsm.run_capture_from_pose()
    await fsm.handle_pose_capture_result(
        {
            "ok": result.ok,
            "quality_ok": quality_ok,
            "photo_id": result.photo_id,
            "error": result.error,
        }
    )
    if result.ok and quality_ok:
        await fsm.handle_pose_speech_done("我拍好啦")


async def run_mock_demo(config: RuntimeConfig) -> DeliveryResult:
    fsm, _ = _build_mock_fsm(config)
    await fsm.start()
    await fsm.poll_wake()
    await fsm.poll_wake()
    await fsm.handle_photo_intent("accept")
    await fsm.handle_capture_device("insta")
    await fsm.handle_capture_mode("photo")
    await _finish_mock_s3_capture(fsm)
    await fsm.handle_review_intent("accept")
    result = await fsm.run_delivery()
    # The real runtime lingers on the share page for share_linger_s before looping;
    # the synchronous mock collapses that to an immediate reset.
    await fsm.finish_session("mock_demo_complete")
    return result


def _build_mock_fsm(config: RuntimeConfig) -> tuple[PhotoAgentFSM, DeliveryResult]:
    capture = CaptureResult(
        "mock-photo",
        Path("/tmp/mock-photo.jpg"),
        True,
        np.ones((16, 16, 3), dtype=np.uint8),
    )
    delivery_result = DeliveryResult(
        "mock-photo", f"{config.base_url.rstrip('/')}/api/photos/mock-photo", True
    )
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector(
            [WakeSignal(True, 3.1, True), WakeSignal(True, 3.2, True)]
        ),
        omni=MockOmni(),
        camera=MockCamera(captures=[capture]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[delivery_result]),
        config=FSMConfig(
            wake_consecutive_frames=2,
            guidance_interval_s=config.guidance_interval_s,
        ),
    )
    return fsm, delivery_result


async def run_mock_state(config: RuntimeConfig, state: str) -> dict[str, object]:
    fsm, delivery_result = _build_mock_fsm(config)
    if state == "S1":
        await fsm.start()
        await fsm.poll_wake()
        await fsm.poll_wake()
    elif state == "S2":
        fsm.context.state = State.ASK_INTENT
        fsm.context.session_id = "session-mock"
        await fsm.handle_photo_intent("accept")
        await fsm.handle_capture_device("insta")
        await fsm.handle_capture_mode("photo")
    elif state == "S3":
        fsm.context.state = State.POSE_GUIDANCE
        fsm.context.session_id = "session-mock"
        await fsm.guidance_tick()
        await _finish_mock_s3_capture(fsm)
    elif state == "S5":
        fsm.context.state = State.REVIEW
        fsm.context.session_id = "session-mock"
        fsm.context.photo_id = "mock-photo"
        await fsm.handle_review_intent("accept")
    elif state == "S6":
        fsm.context.state = State.DELIVER
        fsm.context.session_id = "session-mock"
        fsm.context.photo_id = "mock-photo"
        delivery_result = await fsm.run_delivery()
        # Collapse the real share-page linger to an immediate loop reset for the
        # synchronous acceptance harness (S6 -> S0).
        await fsm.finish_session("mock_share_linger")
    else:
        raise ValueError(f"unknown state: {state}")
    return {
        "ok": True,
        "tested_state": state,
        "result_state": fsm.context.state.value,
        "photo_url": delivery_result.photo_url if state == "S6" else None,
    }
