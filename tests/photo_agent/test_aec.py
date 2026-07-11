from __future__ import annotations

import numpy as np
import pytest

from app.photo_agent.aec import (
    EchoCanceller,
    ReferenceCapturingSink,
    _LinearResampler,
    build_echo_canceller,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class RecordingProcessor:
    """Fake AEC backend: returns near - far so tests can assert alignment."""

    def __init__(self) -> None:
        self.calls: list[tuple[np.ndarray, np.ndarray | None]] = []

    def process(self, near: np.ndarray, far: np.ndarray | None = None):
        near = np.asarray(near, dtype=np.int16)
        rec_far = None if far is None else np.asarray(far, dtype=np.int16).copy()
        self.calls.append((near.copy(), rec_far))
        if far is None:
            return near
        return (near.astype(np.int32) - np.asarray(far, dtype=np.int32)).astype(np.int16)


def _pcm(values: list[int]) -> bytes:
    return np.array(values, dtype=np.int16).tobytes()


def test_resampler_downsamples_24k_to_16k_ratio() -> None:
    resampler = _LinearResampler(24000, 16000)
    total_in = 0
    total_out = 0
    for _ in range(10):
        chunk = np.arange(2400, dtype=np.int16)
        total_in += chunk.size
        total_out += resampler.process(chunk).size
    # 24k -> 16k is a 2/3 ratio.
    assert abs(total_out - total_in * 2 / 3) <= 2


def test_off_mode_passes_audio_through() -> None:
    canceller = EchoCanceller(enabled=False, gate_fallback=False)
    assert canceller.mode == "off"
    assert canceller.process_capture(_pcm([1, 2, 3])) == _pcm([1, 2, 3])


def test_gate_mode_drops_capture_while_playing_and_passes_when_idle() -> None:
    clock = FakeClock()
    canceller = EchoCanceller(
        enabled=True, gate_fallback=True, processor_factory=_raises, clock=clock
    )
    assert canceller.mode == "gate"

    canceller.push_reference(_pcm([500, 500]))  # speaker just played -> playing
    assert canceller.process_capture(_pcm([1, 2, 3])) == b""

    clock.now += 1.0  # past the cooldown window
    assert canceller.process_capture(_pcm([1, 2, 3])) == _pcm([1, 2, 3])


def _raises(sample_rate: int, stream_delay_ms: int):
    raise RuntimeError("no backend in this test")


def test_aec_mode_subtracts_reference_and_aligns_far_to_near() -> None:
    processor = RecordingProcessor()
    # ref_rate == mic_rate keeps the resampler out of this alignment assertion.
    canceller = EchoCanceller(
        mic_rate=16000, ref_rate=16000, processor=processor, gap_reset_ms=1_000_000
    )
    assert canceller.mode == "aec"

    canceller.push_reference(_pcm([10, 20, 30, 40]))
    cleaned = canceller.process_capture(_pcm([11, 22, 33, 44]))

    assert np.frombuffer(cleaned, dtype=np.int16).tolist() == [1, 2, 3, 4]
    near, far = processor.calls[-1]
    assert far.tolist() == [10, 20, 30, 40]


def test_aec_mode_zero_pads_missing_reference() -> None:
    processor = RecordingProcessor()
    canceller = EchoCanceller(
        mic_rate=16000, ref_rate=16000, processor=processor, gap_reset_ms=1_000_000
    )
    # Only two reference samples for a four-sample capture -> left-padded zeros.
    canceller.push_reference(_pcm([100, 200]))
    cleaned = canceller.process_capture(_pcm([100, 200, 300, 400]))

    assert np.frombuffer(cleaned, dtype=np.int16).tolist() == [100, 200, 200, 200]


def test_aec_mode_resets_stale_reference_after_capture_gap() -> None:
    processor = RecordingProcessor()
    clock = FakeClock()
    canceller = EchoCanceller(
        mic_rate=16000,
        ref_rate=16000,
        processor=processor,
        gap_reset_ms=250,
        clock=clock,
    )
    canceller.push_reference(_pcm([9, 9, 9, 9]))
    canceller.process_capture(_pcm([1, 1, 1, 1]))  # consumes some reference

    canceller.push_reference(_pcm([5, 5, 5, 5]))
    clock.now += 1.0  # long gap -> stale reference must be dropped
    canceller.process_capture(_pcm([2, 2, 2, 2]))

    _, far = processor.calls[-1]
    assert far.tolist() == [0, 0, 0, 0]


def test_reference_capturing_sink_taps_playback_then_plays() -> None:
    played: list[bytes] = []

    class Speaker:
        closed = False

        def __call__(self, pcm: bytes) -> None:
            played.append(pcm)

        def close(self) -> None:
            self.closed = True

    processor = RecordingProcessor()
    canceller = EchoCanceller(mic_rate=16000, ref_rate=16000, processor=processor)
    speaker = Speaker()
    sink = ReferenceCapturingSink(speaker, canceller)

    sink(_pcm([7, 7]))
    assert played == [_pcm([7, 7])]

    cleaned = canceller.process_capture(_pcm([10, 10]))
    assert np.frombuffer(cleaned, dtype=np.int16).tolist() == [3, 3]

    sink.close()
    assert speaker.closed is True


def test_build_echo_canceller_falls_back_when_backend_missing() -> None:
    canceller = build_echo_canceller(enabled=True, processor_factory=_raises)
    assert canceller.mode == "gate"


def test_real_webrtc_backend_cancels_echo() -> None:
    pytest.importorskip("pywebrtc_audio")

    rng = np.random.default_rng(0)
    sr = 16000
    n = sr * 6
    far = (rng.standard_normal(n) * 8000).astype(np.int16)
    delay = 80
    echo = np.zeros(n, dtype=np.float32)
    echo[delay:] = far[: n - delay].astype(np.float32) * 0.5
    near = echo.astype(np.int16)  # microphone hears only the speaker echo

    canceller = EchoCanceller(
        mic_rate=16000, ref_rate=16000, stream_delay_ms=int(delay / sr * 1000)
    )
    assert canceller.mode == "aec"

    chunk = 1600  # 100 ms, matching the live microphone
    cleaned = bytearray()
    for i in range(0, n - chunk, chunk):
        canceller.push_reference(far[i : i + chunk].tobytes())
        cleaned += canceller.process_capture(near[i : i + chunk].tobytes())

    out = np.frombuffer(bytes(cleaned), dtype=np.int16).astype(np.float64)
    ref = near[: out.size].astype(np.float64)
    skip = sr  # ignore the first second of AEC convergence
    erle = 10 * np.log10(
        (np.mean(ref[skip:] ** 2) + 1e-9) / (np.mean(out[skip:] ** 2) + 1e-9)
    )
    assert erle > 15.0, f"expected strong echo suppression, got {erle:.1f} dB"
