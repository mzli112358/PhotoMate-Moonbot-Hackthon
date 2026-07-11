"""Single-user controller for browser-driven Photo Agent module tests."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from collections import deque
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import cv2
import numpy as np

from app.photo_agent.camera import detect_faces
from app.photo_agent.prompts import PromptRegistry
from app.photo_agent.observability import JsonFormatter
from app.photo_agent.runtime import RuntimeConfig


def annotate_preview(
    frame: np.ndarray,
    *,
    faces: list[tuple[int, int, int, int]],
    state: str,
    quality: dict[str, Any] | None,
) -> np.ndarray:
    annotated = frame.copy()
    for x, y, width, height in faces:
        cv2.rectangle(annotated, (x, y), (x + width, y + height), (102, 225, 220), 2)
        cv2.putText(
            annotated, "FACE", (x, max(18, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
            (102, 225, 220), 1, cv2.LINE_AA,
        )
    cv2.putText(
        annotated, state, (24, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
        (52, 101, 255), 2, cv2.LINE_AA,
    )
    quality_label = "QUALITY --" if quality is None else f"QUALITY {'PASS' if quality.get('ok') else 'RETRY'}"
    cv2.putText(
        annotated, quality_label, (24, annotated.shape[0] - 22), cv2.FONT_HERSHEY_SIMPLEX,
        0.55, (102, 225, 220), 1, cv2.LINE_AA,
    )
    return annotated


PREVIEW_FRAME_INTERVAL_S = 1 / 15


class TestControllerError(RuntimeError):
    __test__ = False

    pass


class TestAlreadyRunningError(TestControllerError):
    __test__ = False

    pass


class EventHub:
    def __init__(self, *, max_events: int = 500) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._seq = 0
        self._lock = asyncio.Lock()

    async def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._seq += 1
            item = {
                "seq": self._seq,
                "ts": datetime.now(UTC).isoformat(),
                **event,
            }
            self._events.append(item)
            for queue in tuple(self._subscribers):
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(item)
            return item

    async def subscribe(self, *, after: int = 0) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            backlog = [event for event in self._events if event["seq"] > after]
            self._subscribers.add(queue)
        try:
            for event in backlog:
                yield event
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


class TestRunStore:
    __test__ = False

    def __init__(self, path: Path, *, max_runs: int = 50) -> None:
        self.path = path
        self.max_runs = max_runs

    def list(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return value if isinstance(value, list) else []

    def add(self, run: dict[str, Any]) -> None:
        runs = [run, *self.list()][: self.max_runs]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, prefix=f".{self.path.name}.", delete=False
        ) as handle:
            json.dump(runs, handle, ensure_ascii=False, indent=2, default=str)
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)


class _BrowserLogHandler(logging.Handler):
    def __init__(self, controller: "PhotoAgentTestController", loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(logging.INFO)
        self.controller = controller
        self.loop = loop
        self.formatter = JsonFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = json.loads(self.format(record))
            if payload.get("event") == "quality_result":
                self.controller._last_quality = {
                    key: payload.get(key) for key in ("photo_id", "ok", "reason")
                }
            event = {"type": "runtime_log", **payload}
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.controller.events.publish(event))
            )
        except Exception:
            self.handleError(record)


class PhotoAgentTestController:
    VALID_STATES = {"S1", "S2", "S3", "S5", "S6"}

    def __init__(
        self,
        *,
        prompt_registry: PromptRegistry,
        run_store: TestRunStore,
        config_loader: Callable[..., RuntimeConfig],
        runtime_builder: Callable[..., Any],
        event_hub: EventHub | None = None,
        face_detector: Callable[[np.ndarray], Any] | None = None,
    ) -> None:
        self.prompt_registry = prompt_registry
        self.run_store = run_store
        self.config_loader = config_loader
        self.runtime_builder = runtime_builder
        self.events = event_hub or EventHub()
        if face_detector is None:
            face_detector = detect_faces
        self.face_detector = face_detector
        self._lock = asyncio.Lock()
        self._runtime: Any | None = None
        self._task: asyncio.Task[Any] | None = None
        self._selected_state: str | None = None
        self._started_at: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._stop_reason: str | None = None
        self._last_quality: dict[str, Any] | None = None
        self._log_handler: _BrowserLogHandler | None = None
        self._logger_previous_level: int | None = None

    async def start(
        self,
        state: str,
        *,
        camera_index: int | None = None,
        microphone_index: int | None = None,
        speaker_index: int | None = None,
    ) -> dict[str, Any]:
        if state not in self.VALID_STATES:
            raise ValueError(f"unknown state: {state}")
        async with self._lock:
            if self._task is not None and not self._task.done():
                raise TestAlreadyRunningError(f"{self._selected_state} is already running")
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
            runtime = self.runtime_builder(config, prompt_source=self.prompt_registry)
            self._runtime = runtime
            self._selected_state = state
            self._started_at = datetime.now(UTC).isoformat()
            self._last_result = None
            self._last_quality = None
            self._stop_reason = None
            self._attach_logs()
            self._task = asyncio.create_task(self._run(runtime, state), name=f"photo-agent-test-{state}")
            # Let the runtime enter its cleanup-protected boundary before start returns.
            await asyncio.sleep(0)
            await self.events.publish(
                {
                    "type": "test_started",
                    "state": state,
                    "devices": dict(getattr(runtime, "device_info", {})),
                }
            )
            return self.status()

    async def _run(self, runtime: Any, state: str) -> None:
        started_at = self._started_at
        try:
            result = await runtime.run_manual_state(state)
            self._last_result = dict(result)
            self._stop_reason = "completed"
            await self.events.publish({"type": "test_completed", "state": state, "result": result})
        except asyncio.CancelledError:
            self._stop_reason = "operator_stop"
            await self.events.publish({"type": "test_stopped", "state": state})
            raise
        except Exception as exc:  # noqa: BLE001 - test boundary
            self._last_result = {"ok": False, "tested_state": state, "error": str(exc)}
            self._stop_reason = "failed"
            await self.events.publish(
                {"type": "test_failed", "state": state, "error": str(exc)}
            )
        finally:
            self._detach_logs()
            finished_at = datetime.now(UTC).isoformat()
            self.run_store.add(
                {
                    "state": state,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "stop_reason": self._stop_reason,
                    "result": self._last_result,
                    "prompt_version": getattr(runtime, "active_prompt_version", None),
                    "devices": dict(getattr(runtime, "device_info", {})),
                }
            )

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            task = self._task
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                self._stop_reason = "operator_stop"
            return self.status()

    def _attach_logs(self) -> None:
        self._detach_logs()
        logger = logging.getLogger("photomate")
        self._logger_previous_level = logger.level
        logger.setLevel(logging.INFO)
        self._log_handler = _BrowserLogHandler(self, asyncio.get_running_loop())
        logger.addHandler(self._log_handler)

    def _detach_logs(self) -> None:
        if self._log_handler is None:
            return
        logger = logging.getLogger("photomate")
        logger.removeHandler(self._log_handler)
        self._log_handler.close()
        if self._logger_previous_level is not None:
            logger.setLevel(self._logger_previous_level)
        self._log_handler = None

    async def wait_until_idle(self, *, timeout: float = 5.0) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while self._task is not None and not self._task.done():
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("test controller did not become idle")
            await asyncio.sleep(0.01)

    def status(self) -> dict[str, Any]:
        active = self._task is not None and not self._task.done()
        context = getattr(getattr(self._runtime, "fsm", None), "context", None)
        runtime_state = getattr(getattr(context, "state", None), "value", None)
        return {
            "active": active,
            "selected_state": self._selected_state,
            "runtime_state": runtime_state,
            "started_at": self._started_at,
            "stop_reason": self._stop_reason,
            "devices": dict(getattr(self._runtime, "device_info", {})),
            "saved_prompt_version": self.prompt_registry.version,
            "active_prompt_version": getattr(self._runtime, "active_prompt_version", None),
            "session_id": getattr(context, "session_id", None),
            "photo_id": getattr(context, "photo_id", None),
            "photo_url": getattr(context, "photo_url", None),
            "last_quality": self._last_quality,
            "last_result": self._last_result,
        }

    async def preview_jpeg(self) -> bytes:
        camera = getattr(getattr(self._runtime, "fsm", None), "camera", None)
        runtime_state = self.status().get("runtime_state")
        frame = None
        if camera is not None and self._runtime is not None:
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
            except Exception:
                frame = latest_frame() if callable(latest_frame) else None
        if frame is None:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(
                frame,
                "CAMERA OFFLINE",
                (170, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (80, 140, 255),
                2,
                cv2.LINE_AA,
            )
        else:
            state = runtime_state or "--"
            faces: list[tuple[int, int, int, int]] = []
            if runtime_state == "S1":
                faces = [
                    tuple(int(value) for value in face)
                    for face in self.face_detector(frame)
                ]
            frame = annotate_preview(
                frame,
                faces=faces,
                state=state,
                quality=self._last_quality,
            )
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
        if not ok:
            raise RuntimeError("preview frame could not be encoded")
        return encoded.tobytes()
