"""Deterministic adapters used by automated tests and mock demos."""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from app.photo_agent.models import CaptureResult, DeliveryResult, QualityResult, WakeSignal


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def record(self, name: str, value: Any = None) -> None:
        self.calls.append((name, value))

    def count(self, name: str) -> int:
        return sum(call_name == name for call_name, _ in self.calls)


class MockWakeDetector(_Recorder):
    def __init__(self, signals: list[WakeSignal]) -> None:
        super().__init__()
        self._signals = deque(signals)

    async def poll(self) -> WakeSignal:
        self.record("poll")
        if self._signals:
            return self._signals.popleft()
        return WakeSignal(False, 0.0, False)


class MockCamera(_Recorder):
    def __init__(
        self,
        *,
        captures: list[CaptureResult] | None = None,
        frames: list[Any] | None = None,
    ) -> None:
        super().__init__()
        self._captures = deque(captures or [])
        self._frames = deque(frames or [np.ones((8, 8, 3), dtype=np.uint8)])
        self.closed = False

    async def get_frame(self) -> Any:
        self.record("get_frame")
        if len(self._frames) > 1:
            return self._frames.popleft()
        return self._frames[0]

    async def capture(self, mode: str = "photo") -> CaptureResult:
        self.record("capture", mode)
        if self._captures:
            return self._captures.popleft()
        return CaptureResult("", Path("/tmp/missing.jpg"), False, error="no mock capture")

    async def close(self) -> None:
        self.record("close")
        self.closed = True


class MockQualityChecker(_Recorder):
    def __init__(self, results: list[QualityResult]) -> None:
        super().__init__()
        self._results = deque(results)

    def check(self, image: Any) -> QualityResult:
        self.record("check")
        if len(self._results) > 1:
            return self._results.popleft()
        return self._results[0]


class MockDelivery(_Recorder):
    def __init__(
        self,
        *,
        results: list[DeliveryResult],
        show_results: list[bool] | None = None,
    ) -> None:
        super().__init__()
        self._results = deque(results)
        self._show_results = deque(show_results or [True])

    def register_photo(self, photo_id: str, path: Path) -> None:
        self.record("register_photo", (photo_id, path))

    async def show(self, photo_id: str) -> bool:
        self.record("show", photo_id)
        if len(self._show_results) > 1:
            return self._show_results.popleft()
        return self._show_results[0]

    async def deliver(self, photo_id: str) -> DeliveryResult:
        self.record("deliver", photo_id)
        if len(self._results) > 1:
            return self._results.popleft()
        return self._results[0]


class MockOmni(_Recorder):
    def __init__(self, *, connect_failures: int = 0) -> None:
        super().__init__()
        self.connect_failures = connect_failures
        self.closed = False
        self.session_id = "session-mock"
        self.events: deque[dict[str, Any]] = deque()
        self._enable_vad = True
        self._output_audio_enabled = True

    @property
    def vad_enabled(self) -> bool:
        return self._enable_vad

    @property
    def output_audio_enabled(self) -> bool:
        return self._output_audio_enabled

    async def configure(
        self,
        *,
        enable_vad: bool = True,
        output_audio: bool = True,
        tools: list[dict[str, Any]] | None = None,
    ) -> None:
        self._enable_vad = enable_vad
        self._output_audio_enabled = output_audio
        self.record(
            "configure",
            {
                "enable_vad": enable_vad,
                "output_audio": output_audio,
                "tools": [] if tools is not None and len(tools) == 0 else "default",
            },
        )

    async def connect(self) -> str:
        self.record("connect")
        if self.connect_failures > 0:
            self.connect_failures -= 1
            raise ConnectionError("mock connect failure")
        self.closed = False
        return self.session_id

    async def prime_audio(self) -> None:
        self.record("prime_audio")

    async def append_audio(self, pcm: bytes) -> None:
        self.record("append_audio", len(pcm))

    async def append_image(self, frame: Any) -> None:
        self.record("append_image", getattr(frame, "shape", None))

    async def commit_input(self) -> None:
        self.record("commit_input")

    async def inject_context(self, text: str) -> None:
        self.record("inject_context", text)

    async def create_response(self, instructions: str, *, output_audio: bool = True) -> None:
        self.record(
            "create_response",
            {"instructions": instructions, "output_audio": output_audio},
        )

    async def update_instructions(self, instructions: str) -> None:
        self.record("update_instructions", instructions)

    async def wait_response_done(self, timeout: float) -> None:
        self.record("wait_response_done", timeout)

    async def cancel_response(self) -> None:
        self.record("cancel_response")

    async def submit_tool_result(
        self,
        call_id: str,
        output: dict[str, Any],
        *,
        create_followup: bool = True,
    ) -> None:
        self.record("submit_tool_result", (call_id, output, create_followup))

    async def next_event(self, timeout: float | None = None) -> dict[str, Any]:
        if self.events:
            return self.events.popleft()
        await asyncio.sleep(timeout or 0)
        raise TimeoutError("no mock event")

    async def end_session(self, reason: str) -> None:
        self.record("end_session", reason)

    async def close(self) -> None:
        self.record("close")
        self.closed = True
