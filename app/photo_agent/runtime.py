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
from app.photo_agent.models import CaptureResult, DeliveryResult, QualityResult, State, WakeSignal

LOGGER = logging.getLogger("photomate.photo_agent.runtime")


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str = "mock"
    model: str = "qwen3.5-omni-flash-realtime"
    workspace_host: str = "llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com"
    api_key: str = ""
    voice: str = "Tina"
    camera_index: int = 0
    microphone_index: int | None = None
    speaker_index: int | None = None
    photo_dir: Path = Path("data/photos")
    base_url: str = "http://127.0.0.1:8000"
    guidance_interval_s: float = 5.0


class PhotoAgentRuntime:
    def __init__(
        self,
        fsm: PhotoAgentFSM,
        microphone: object | None = None,
        resources: list[object] | None = None,
        device_info: dict[str, str] | None = None,
        fallback_notifier: object | None = None,
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
        self._stopped = asyncio.Event()
        self._last_guidance_at = 0.0
        self._state_seen = fsm.context.state
        self._state_since = time.monotonic()
        self._wall_clock = time.time
        self.session_max_s = 115 * 60.0

    async def handle_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "speech_started":
            await self.fsm.handle_speech_started()
        elif event_type == "response_created":
            self.fsm.context.response_in_flight = True
            LOGGER.info(
                "response_created",
                extra={
                    "response_id": event.get("response_id"),
                    "session_id": self.fsm.context.session_id,
                },
            )
        elif event_type == "response_done":
            await self.fsm.handle_response_done()
        elif event_type == "user_text":
            await self.fsm.handle_user_text(str(event.get("text") or ""))
            self._track_state()
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
            output = await self.dispatcher.dispatch(call)
            LOGGER.info(
                "function_call_result",
                extra={"function_name": call.name, "call_id": call.call_id, "output": output},
            )
            await self.omni.submit_tool_result(call.call_id, output)
            self._track_state()
        elif event_type in ("error", "disconnected"):
            LOGGER.error("omni_event", extra={"event": event})
            try:
                await self.fallback_notifier.notify(
                    "实时语音服务暂时不可用，本次服务已安全结束，请稍后再试。"
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("fallback_notification_failed", extra={"error": str(exc)})
            await self.fsm.finish_session(f"omni_{event_type}")
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
                await self.omni.append_audio(chunk)
                await asyncio.sleep(0)
            except Exception as exc:  # noqa: BLE001 - live device boundary
                LOGGER.warning(
                    "audio_stream_failed",
                    extra={"session_id": self.fsm.context.session_id, "error": str(exc)},
                )
                await asyncio.sleep(0.05)

    async def _frame_loop(self) -> None:
        while not self._stopped.is_set():
            if self.fsm.context.session_id and self.fsm.context.state.value in ("S2", "S3", "S5"):
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

    async def _control_step(self) -> None:
        from app.photo_agent.models import State

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
                if await self.fsm.guidance_tick():
                    self._last_guidance_at = now
        elif state is State.ASK_INTENT and time.monotonic() - self._state_since >= 12.0:
            await self.fsm.handle_timeout()
            self._state_since = time.monotonic()
        elif state is State.REVIEW and time.monotonic() - self._state_since >= 15.0:
            await self.fsm.handle_timeout()
        elif state is State.SHOOT and time.monotonic() - self._state_since >= 2.0:
            await self.fsm.run_shoot()
        elif state is State.DELIVER and time.monotonic() - self._state_since >= 2.0:
            await self.fsm.run_delivery()
        self._track_state()

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

    async def _run_until_states(self, stop_states: set[State], timeout: float) -> State:
        audio_task = asyncio.create_task(self._audio_loop(), name="manual-photo-agent-audio")
        frame_task = asyncio.create_task(self._frame_loop(), name="manual-photo-agent-frames")
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
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

    async def run_manual_state(self, state: str, timeout: float = 60.0) -> dict[str, object]:
        requested = State(state)
        result: dict[str, object] = {"ok": False, "tested_state": state}
        try:
            if requested is State.DETECT_INTENT:
                await self.fsm.start()
                final_state = await self._run_until_states({State.ASK_INTENT, State.IDLE}, timeout)
            else:
                await self._connect_manual_session(requested)
                if requested is State.ASK_INTENT:
                    await self.omni.create_response("嗨～需要我帮你拍张照吗？只说这一句。")
                    final_state = await self._run_until_states({State.POSE_GUIDANCE, State.IDLE}, timeout)
                elif requested is State.POSE_GUIDANCE:
                    final_state = await self._run_until_states({State.SHOOT}, timeout)
                elif requested is State.SHOOT:
                    await self.fsm.run_shoot()
                    final_state = self.fsm.context.state
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
) -> PhotoAgentRuntime:
    if config.mode != "local-real":
        raise ValueError("build_local_runtime requires mode=local-real")
    if not config.api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is required for local-real mode")

    from app.photo_agent.audio import PyAudioMicrophone, PyAudioSpeaker
    from app.photo_agent.camera import FaceWakeDetector, OpenCVCamera, OpenCVQualityChecker
    from app.photo_agent.delivery import FileDeliveryAdapter, GLOBAL_PHOTO_STORE
    from app.photo_agent.fallback import SystemFallbackNotifier
    from app.photo_agent.omni import DashscopeOmniClient, OmniSettings

    camera_builder = camera_factory or OpenCVCamera
    microphone_builder = microphone_factory or PyAudioMicrophone
    speaker_builder = speaker_factory or PyAudioSpeaker
    camera = None
    speaker = None
    microphone = None
    try:
        camera = camera_builder(config.camera_index, config.photo_dir)
        open_camera = getattr(camera, "open", None)
        if open_camera:
            open_camera()
        speaker = speaker_builder(device_index=config.speaker_index)
        microphone = microphone_builder(device_index=config.microphone_index)
    except Exception:
        if microphone is not None and getattr(microphone, "close", None):
            microphone.close()
        if speaker is not None and getattr(speaker, "close", None):
            speaker.close()
        if camera is not None and getattr(camera, "close_sync", None):
            camera.close_sync()
        raise
    assert camera is not None and speaker is not None and microphone is not None
    omni = DashscopeOmniClient(
        OmniSettings(
            api_key=config.api_key,
            workspace_host=config.workspace_host,
            model=config.model,
            voice=config.voice,
        ),
        audio_sink=speaker,
    )
    fsm = PhotoAgentFSM(
        wake_detector=FaceWakeDetector(camera),
        omni=omni,
        camera=camera,
        quality_checker=OpenCVQualityChecker(),
        delivery=FileDeliveryAdapter(GLOBAL_PHOTO_STORE, config.base_url),
        config=FSMConfig(guidance_interval_s=config.guidance_interval_s),
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
    )


async def run_mock_demo(config: RuntimeConfig) -> DeliveryResult:
    fsm, _ = _build_mock_fsm(config)
    await fsm.start()
    await fsm.poll_wake()
    await fsm.poll_wake()
    await fsm.handle_user_text("要")
    await fsm.handle_user_text("拍吧")
    await fsm.run_shoot()
    await fsm.handle_user_text("满意")
    return await fsm.run_delivery()


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
        await fsm.handle_user_text("要")
    elif state == "S3":
        fsm.context.state = State.POSE_GUIDANCE
        fsm.context.session_id = "session-mock"
        await fsm.guidance_tick()
        await fsm.handle_response_done("往中间站一点")
        await fsm.handle_user_text("拍吧")
    elif state == "S4":
        fsm.context.state = State.SHOOT
        fsm.context.session_id = "session-mock"
        await fsm.run_shoot()
    elif state == "S5":
        fsm.context.state = State.REVIEW
        fsm.context.session_id = "session-mock"
        fsm.context.photo_id = "mock-photo"
        await fsm.handle_user_text("满意")
    elif state == "S6":
        fsm.context.state = State.DELIVER
        fsm.context.session_id = "session-mock"
        fsm.context.photo_id = "mock-photo"
        delivery_result = await fsm.run_delivery()
    else:
        raise ValueError(f"unknown state: {state}")
    return {
        "ok": True,
        "tested_state": state,
        "result_state": fsm.context.state.value,
        "photo_url": delivery_result.photo_url if state == "S6" else None,
    }
