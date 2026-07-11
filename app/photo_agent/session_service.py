"""Process-internal live session that drives the S1-S6 pipeline for the kiosk UI.

Unlike the test console (operator picks one state), this owns a single long-lived
``PhotoAgentRuntime`` running ``run_forever()`` and broadcasts a state snapshot
whenever the FSM advances, so the browser can follow the flow via SSE.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Callable

import cv2
import numpy as np

from app.photo_agent.camera import detect_faces
from app.photo_agent.delivery import GLOBAL_DOWNLOAD_REGISTRY
from app.photo_agent.prompts import PromptSource
from app.photo_agent.runtime import RuntimeConfig
from app.photo_agent.test_controller import (
    PREVIEW_FRAME_INTERVAL_S,
    EventHub,
    annotate_preview,
)

LOGGER = logging.getLogger("photomate.photo_agent.session")

# Short voice hints shown on the kiosk per stage; purely presentational.
_STATE_HINTS: dict[str, list[str]] = {
    "S0": [],
    "S1": ["需要拍照", "暂时不用"],
    "S3": ["可以拍了", "换个动作"],
    "S5": ["再来一张", "文件获取"],
    "S6": ["扫码保存", "打印一张"],
}
_S2_PHASE_HINTS: dict[str, list[str]] = {
    "ask_intent": ["需要拍照", "暂时不用"],
    "ask_device": ["我的手机", "影石Link"],
    "ask_mode": ["一键拍照", "录像"],
    "done": [],
}


class LiveSessionService:
    def __init__(
        self,
        *,
        prompt_source: PromptSource,
        config_loader: Callable[..., RuntimeConfig],
        runtime_builder: Callable[..., Any],
        event_hub: EventHub | None = None,
        face_detector: Callable[[np.ndarray], Any] | None = None,
        base_url: str = "http://127.0.0.1:8000",
    ) -> None:
        self.prompt_source = prompt_source
        self.config_loader = config_loader
        self.runtime_builder = runtime_builder
        self.events = event_hub or EventHub()
        self.face_detector = face_detector or detect_faces
        self.base_url = base_url.rstrip("/")
        self._lock = asyncio.Lock()
        self._runtime: Any | None = None
        self._run_task: asyncio.Task[Any] | None = None
        self._watch_task: asyncio.Task[Any] | None = None
        self._started_at: str | None = None
        self._error: str | None = None
        self._last_key: str | None = None
        self._last_quality: dict[str, Any] | None = None

    @property
    def active(self) -> bool:
        return self._run_task is not None and not self._run_task.done()

    async def start(
        self,
        *,
        camera_index: int | None = None,
        microphone_index: int | None = None,
        speaker_index: int | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            if self.active:
                return self.snapshot()
            config = self.config_loader(mode="local-real")
            overrides = {
                name: value
                for name, value in {
                    "camera_index": camera_index,
                    "microphone_index": microphone_index,
                    "speaker_index": speaker_index,
                }.items()
                if value is not None
            }
            if overrides:
                config = replace(config, **overrides)
            self.base_url = config.base_url.rstrip("/")
            runtime = self.runtime_builder(config, prompt_source=self.prompt_source)
            self._runtime = runtime
            self._started_at = datetime.now(UTC).isoformat()
            self._error = None
            self._last_key = None
            self._last_quality = None
            self._run_task = asyncio.create_task(self._run(runtime), name="photo-agent-session")
            self._watch_task = asyncio.create_task(self._watch(), name="photo-agent-session-watch")
            await asyncio.sleep(0)
            await self.events.publish(
                {"type": "session_started", "devices": dict(getattr(runtime, "device_info", {}))}
            )
            await self._publish_snapshot(force=True)
            return self.snapshot()

    async def _run(self, runtime: Any) -> None:
        try:
            await runtime.run_forever()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - live session boundary
            self._error = str(exc)
            LOGGER.error("session_run_failed", extra={"error": str(exc)})
            await self.events.publish({"type": "session_error", "error": str(exc)})

    async def _watch(self) -> None:
        try:
            while True:
                await self._publish_snapshot()
                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            raise

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            runtime = self._runtime
            if runtime is not None:
                runtime.stop()
            for task in (self._watch_task, self._run_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(t for t in (self._watch_task, self._run_task) if t is not None),
                return_exceptions=True,
            )
            self._watch_task = None
            self._run_task = None
            self._runtime = None
            await self.events.publish({"type": "session_stopped"})
            await self._publish_snapshot(force=True)
            return self.snapshot()

    def _context(self) -> Any | None:
        return getattr(getattr(self._runtime, "fsm", None), "context", None)

    def download_url_for(self, photo_id: str) -> str:
        registry_url = GLOBAL_DOWNLOAD_REGISTRY.get(photo_id)
        return registry_url or f"{self.base_url}/api/photos/{photo_id}"

    def snapshot(self) -> dict[str, Any]:
        ctx = self._context()
        active = self.active
        if ctx is None:
            return {
                "active": active,
                "state": "S0",
                "s2_phase": "ask_intent",
                "device": None,
                "mode": None,
                "photo_id": None,
                "photo_url": None,
                "download_url": None,
                "qr_url": None,
                "transcript": "",
                "hints": [],
                "voice_state": "idle",
                "session_id": None,
                "error": self._error,
                "devices": dict(getattr(self._runtime, "device_info", {}) or {}),
            }
        state = ctx.state.value
        pose = ctx.pose_context
        photo_id = ctx.photo_id
        download_url = self.download_url_for(photo_id) if photo_id else None
        transcript = pose.last_spoken_text if pose else ""
        return {
            "active": active,
            "state": state,
            "s2_phase": ctx.s2_phase,
            "device": ctx.capture_device,
            "mode": ctx.capture_mode,
            "photo_id": photo_id,
            "photo_url": f"/api/photos/{photo_id}" if photo_id else None,
            "download_url": download_url,
            "qr_url": f"/api/photo-agent/qr/{photo_id}.png" if photo_id else None,
            "transcript": transcript,
            "hints": self._hints(state, ctx.s2_phase),
            "voice_state": self._voice_state(ctx),
            "session_id": ctx.session_id,
            "error": self._error,
            "devices": dict(getattr(self._runtime, "device_info", {}) or {}),
        }

    @staticmethod
    def _hints(state: str, s2_phase: str) -> list[str]:
        if state == "S2":
            return _S2_PHASE_HINTS.get(s2_phase, [])
        return _STATE_HINTS.get(state, [])

    @staticmethod
    def _voice_state(ctx: Any) -> str:
        if not ctx.session_id:
            return "idle"
        return "responding" if ctx.response_in_flight else "listening"

    async def _publish_snapshot(self, *, force: bool = False) -> None:
        snap = self.snapshot()
        key = json.dumps(
            {
                k: snap[k]
                for k in (
                    "active",
                    "state",
                    "s2_phase",
                    "device",
                    "mode",
                    "photo_id",
                    "download_url",
                    "transcript",
                    "voice_state",
                )
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if force or key != self._last_key:
            self._last_key = key
            await self.events.publish({"type": "state", "snapshot": snap})

    async def preview_jpeg(self) -> bytes:
        runtime = self._runtime
        camera = getattr(getattr(runtime, "fsm", None), "camera", None)
        runtime_state = self.snapshot().get("state")
        frame = None
        if camera is not None:
            get_frame = getattr(camera, "get_frame", None)
            latest_frame = getattr(camera, "latest_frame", None)
            try:
                if runtime_state != "S1" and callable(get_frame):
                    frame = await get_frame()
                elif callable(latest_frame):
                    frame = latest_frame()
                    if frame is None and callable(get_frame):
                        frame = await get_frame()
                elif callable(get_frame):
                    frame = await get_frame()
            except Exception:  # noqa: BLE001 - live device boundary
                frame = latest_frame() if callable(latest_frame) else None
        if frame is None:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(
                frame, "CAMERA OFFLINE", (170, 190), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (80, 140, 255), 2, cv2.LINE_AA,
            )
        else:
            faces: list[tuple[int, int, int, int]] = []
            if runtime_state == "S1":
                faces = [
                    tuple(int(value) for value in face) for face in self.face_detector(frame)
                ]
            frame = annotate_preview(
                frame, faces=faces, state=runtime_state or "--", quality=self._last_quality
            )
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
        if not ok:
            raise RuntimeError("preview frame could not be encoded")
        return encoded.tobytes()


PREVIEW_INTERVAL_S = PREVIEW_FRAME_INTERVAL_S
