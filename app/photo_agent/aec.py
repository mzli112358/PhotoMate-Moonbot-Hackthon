"""Acoustic echo cancellation (AEC) front-end for the realtime audio pipeline.

The realtime Omni pipeline streams raw microphone PCM straight to the model and
plays the model's TTS back through the same device's speaker. Without echo
cancellation the microphone re-captures that TTS, the server VAD treats it as a
new user turn, and the agent talks over / interrupts itself.

This module inserts a WebRTC AEC3 stage between the microphone and
``append_audio``. The speaker sink taps every played chunk as the *reference*
(far) signal; each captured (near) chunk is then cleaned against it.

Design notes:
- The microphone runs at 16 kHz and the speaker at 24 kHz, so the reference is
  resampled to the microphone rate before it reaches the canceller.
- ``push_reference`` runs on the DashScope websocket/playback thread while
  ``process_capture`` runs on the asyncio audio loop, so the reference buffer is
  guarded by a lock.
- When the WebRTC backend is unavailable (for instance a wheel that is not built
  for the target platform) the canceller degrades to a half-duplex *gate*: the
  microphone is dropped while the speaker is playing, which still breaks the
  self-echo loop at the cost of barge-in.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Protocol

import numpy as np

LOGGER = logging.getLogger("photomate.photo_agent.aec")

MIC_RATE = 16000
REF_RATE = 24000
FRAME_MS = 10


class _Processor(Protocol):
    def process(self, near: np.ndarray, far: np.ndarray | None = None) -> Any: ...


def _default_processor_factory(sample_rate: int, stream_delay_ms: int) -> _Processor:
    """Build the WebRTC AEC3 backend (imported lazily so the dep stays optional)."""
    from pywebrtc_audio import AudioProcessor

    return AudioProcessor(
        sample_rate=sample_rate,
        num_channels=1,
        echo_cancellation=True,
        noise_suppression=True,
        high_pass_filter=True,
        auto_gain_control=False,
        stream_delay_ms=stream_delay_ms,
    )


class _LinearResampler:
    """Dependency-free linear resampler that stays continuous across chunks."""

    def __init__(self, in_rate: int, out_rate: int) -> None:
        self._step = in_rate / out_rate
        self._t = 0.0
        self._prev = 0.0
        self._primed = False

    def process(self, samples: np.ndarray) -> np.ndarray:
        if samples.size == 0:
            return np.zeros(0, dtype=np.int16)
        x = samples.astype(np.float64)
        if not self._primed:
            self._prev = float(x[0])
            self._primed = True
        buf = np.concatenate(([self._prev], x))
        length = x.size
        count = int(np.floor((length - 1 - self._t) / self._step)) + 1
        if count <= 0:
            self._t -= length
            self._prev = float(x[-1])
            return np.zeros(0, dtype=np.int16)
        ts = self._t + self._step * np.arange(count)
        out = np.interp(ts + 1.0, np.arange(buf.size), buf)
        self._t = (self._t + self._step * count) - length
        self._prev = float(x[-1])
        return np.clip(np.round(out), -32768, 32767).astype(np.int16)


class EchoCanceller:
    """Removes speaker echo from captured microphone audio before it is sent upstream.

    ``mode`` is one of ``"aec"`` (WebRTC echo cancellation), ``"gate"`` (drop the
    mic while the speaker plays) or ``"off"`` (pass-through).
    """

    def __init__(
        self,
        *,
        mic_rate: int = MIC_RATE,
        ref_rate: int = REF_RATE,
        frame_ms: int = FRAME_MS,
        stream_delay_ms: int = 120,
        enabled: bool = True,
        gate_fallback: bool = True,
        gate_cooldown_ms: int = 250,
        max_ref_ms: int = 400,
        gap_reset_ms: int = 250,
        processor: _Processor | None = None,
        processor_factory: Callable[[int, int], _Processor] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.mic_rate = mic_rate
        self.ref_rate = ref_rate
        self.frame_samples = mic_rate * frame_ms // 1000
        self._clock = clock
        self._gate_fallback = gate_fallback
        self._gate_cooldown = gate_cooldown_ms / 1000.0
        self._gap_reset = gap_reset_ms / 1000.0
        self._max_ref = int(mic_rate * max_ref_ms / 1000)
        self._lock = threading.Lock()
        self._ref = np.zeros(0, dtype=np.int16)
        self._resampler = _LinearResampler(ref_rate, mic_rate) if ref_rate != mic_rate else None
        self._last_ref_at = 0.0
        self._last_capture_at = 0.0
        self._processor = processor

        if enabled and self._processor is None:
            factory = processor_factory or _default_processor_factory
            try:
                self._processor = factory(mic_rate, stream_delay_ms)
            except Exception as exc:  # noqa: BLE001 - optional native dependency
                LOGGER.warning("aec_backend_unavailable", extra={"error": str(exc)})
                self._processor = None

        if self._processor is not None:
            self.mode = "aec"
        elif enabled and gate_fallback:
            self.mode = "gate"
        else:
            self.mode = "off"
        LOGGER.info("aec_mode", extra={"mode": self.mode, "stream_delay_ms": stream_delay_ms})

    @property
    def is_playing(self) -> bool:
        """True while (or shortly after) the speaker is emitting audio."""
        return (self._clock() - self._last_ref_at) < self._gate_cooldown

    def push_reference(self, pcm: bytes) -> None:
        """Record a played (far) chunk as the AEC reference signal."""
        if not pcm:
            return
        self._last_ref_at = self._clock()
        if self.mode != "aec":
            return
        samples = np.frombuffer(pcm, dtype=np.int16)
        if self._resampler is not None:
            samples = self._resampler.process(samples)
        if samples.size == 0:
            return
        with self._lock:
            self._ref = np.concatenate((self._ref, samples))
            if self._ref.size > self._max_ref:
                self._ref = self._ref[-self._max_ref :]

    def process_capture(self, pcm: bytes) -> bytes:
        """Return echo-cleaned capture audio, or ``b""`` when the chunk is gated."""
        if self.mode == "off":
            return pcm
        if self.mode == "gate":
            return b"" if self.is_playing else pcm

        now = self._clock()
        if self._last_capture_at and (now - self._last_capture_at) > self._gap_reset:
            # A gap in capture (e.g. VAD was off) leaves stale reference behind.
            with self._lock:
                self._ref = np.zeros(0, dtype=np.int16)
        self._last_capture_at = now

        near = np.frombuffer(pcm, dtype=np.int16)
        if near.size == 0:
            return pcm
        with self._lock:
            take = min(near.size, self._ref.size)
            far = self._ref[:take].copy()
            self._ref = self._ref[take:]
        if far.size < near.size:
            far = np.concatenate((np.zeros(near.size - far.size, dtype=np.int16), far))

        cleaned = np.asarray(self._processor.process(near, far), dtype=np.int16)
        if cleaned.size != near.size:
            cleaned = cleaned[: near.size]
        return cleaned.tobytes()

    def reset(self) -> None:
        with self._lock:
            self._ref = np.zeros(0, dtype=np.int16)
        self._last_capture_at = 0.0

    def close(self) -> None:
        self._processor = None
        self.reset()


class ReferenceCapturingSink:
    """Wraps the speaker sink so every played chunk also feeds the AEC reference."""

    def __init__(self, sink: Callable[[bytes], None], canceller: EchoCanceller) -> None:
        self._sink = sink
        self._canceller = canceller

    def __call__(self, pcm: bytes) -> None:
        self._canceller.push_reference(pcm)
        self._sink(pcm)

    def close(self) -> None:
        close = getattr(self._sink, "close", None)
        if close is not None:
            close()


def build_echo_canceller(
    *,
    enabled: bool = True,
    gate_fallback: bool = True,
    stream_delay_ms: int = 120,
    processor_factory: Callable[[int, int], _Processor] | None = None,
) -> EchoCanceller:
    """Construct an :class:`EchoCanceller`, degrading gracefully if AEC is unavailable."""
    canceller = EchoCanceller(
        enabled=enabled,
        gate_fallback=gate_fallback,
        stream_delay_ms=stream_delay_ms,
        processor_factory=processor_factory,
    )
    if enabled and canceller.mode != "aec":
        LOGGER.warning(
            "aec_degraded",
            extra={"mode": canceller.mode, "hint": "WebRTC AEC backend unavailable"},
        )
    return canceller
