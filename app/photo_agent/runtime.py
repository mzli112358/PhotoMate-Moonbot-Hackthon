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
    model: str = "qwen3.5-omni-flash-2026-03-15"
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
    ) -> None:
        self.fsm = fsm
        self.omni = fsm.omni
        self.microphone = microphone
        self.resources = resources or []
        self.dispatcher = FunctionCallDispatcher(fsm)
        self._stopped = asyncio.Event()
        self._last_guidance_at = 0.0
        self._state_seen = fsm.context.state
        self._state_since = time.monotonic()

    async def handle_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "speech_started":
            await self.fsm.handle_speech_started()
        elif event_type == "response_created":
            self.fsm.context.response_in_flight = True
        elif event_type == "response_done":
            await self.fsm.handle_response_done()
        elif event_type == "user_text":
            await self.fsm.handle_user_text(str(event.get("text") or ""))
            self._track_state()
        elif event_type == "tool_call":
            call = event["tool_call"]
            output = await self.dispatcher.dispatch(call)
            await self.omni.submit_tool_result(call.call_id, output)
            self._track_state()
        elif event_type in ("error", "disconnected"):
            LOGGER.error("omni_event", extra={"event": event})

    async def _audio_loop(self) -> None:
        if self.microphone is None:
            return
        while not self._stopped.is_set():
            if not self.fsm.context.session_id:
                await asyncio.sleep(0.05)
                continue
            chunk = await asyncio.to_thread(self.microphone.read_chunk)
            await self.omni.append_audio(chunk)

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
            if self.microphone is not None:
                await asyncio.to_thread(self.microphone.close)
            await self.fsm.close()
            for resource in self.resources:
                close = getattr(resource, "close", None)
                if close:
                    await asyncio.to_thread(close)

    def stop(self) -> None:
        self._stopped.set()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_self_check(config: RuntimeConfig) -> dict:
    real = config.mode == "local-real"
    return {
        "git_branch": _git_value("branch", "--show-current"),
        "git_commit": _git_value("rev-parse", "--short", "HEAD"),
        "mode": config.mode,
        "state": "S0",
        "model": config.model,
        "api_host": config.workspace_host,
        "api_key_present": bool(config.api_key),
        "camera": config.camera_index,
        "microphone": config.microphone_index if config.microphone_index is not None else "default",
        "speaker": config.speaker_index if config.speaker_index is not None else "default",
        "photo_dir": str(config.photo_dir),
        "base_url": config.base_url,
        "adapters": {
            "omni": "real" if real else "mock",
            "camera": "real" if real else "mock",
            "audio_input": "real" if real else "mock",
            "audio_output": "real" if real else "mock",
            "delivery": "local-real" if real else "mock",
        },
        "missing_real_dependencies": [] if real else ["Omni", "camera", "microphone", "speaker"],
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
    return PhotoAgentRuntime(fsm, microphone=microphone, resources=[speaker])


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
