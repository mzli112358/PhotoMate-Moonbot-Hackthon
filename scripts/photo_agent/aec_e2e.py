#!/usr/bin/env python3
"""End-to-end validation for the realtime echo-cancellation front-end.

This drives the *production* audio path used by the live runtime:

    model TTS (24 kHz)  ->  ReferenceCapturingSink  ->  push_reference (resample)
    microphone (16 kHz) ->  EchoCanceller.process_capture  ->  append_audio

against a simulated acoustic room (delay + attenuation + mild nonlinearity +
noise) that mixes the speaker echo back into the microphone, including a
double-talk segment where the user speaks while the agent is speaking.

It reports:
  * ERLE  (echo return loss enhancement) over echo-only segments -- higher is
    better; > 15 dB means the self-echo loop is effectively broken.
  * user-speech preservation during double-talk -- the fraction of user energy
    that survives cancellation.

No microphone or speaker hardware is required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.photo_agent.aec import ReferenceCapturingSink, build_echo_canceller  # noqa: E402

MIC_RATE = 16000
REF_RATE = 24000


def _speech_like(
    rng: np.random.Generator,
    n: int,
    rate: int,
    seed_scale: float,
    f0: float = 140.0,
) -> np.ndarray:
    """Voiced, harmonic signal (fundamental + formant-shaped harmonics + syllable AM).

    Harmonic structure matters: a noise-like proxy would be removed by the noise
    suppressor, which would make the double-talk measurement meaningless.
    """
    t = np.arange(n) / rate
    vibrato = 1.0 + 0.01 * np.sin(2 * np.pi * 5.0 * t)  # gentle pitch wobble
    phase = 2 * np.pi * np.cumsum(f0 * vibrato) / rate
    formants = (500.0, 1500.0, 2600.0)
    sig = np.zeros(n, dtype=np.float64)
    for k in range(1, int((rate / 2) / f0)):
        fk = k * f0
        if fk >= rate / 2:
            break
        amp = 1.0 / k  # natural spectral rolloff
        for fc in formants:  # boost harmonics near formant peaks
            amp += 0.6 * np.exp(-((fk - fc) ** 2) / (2 * 220.0 ** 2)) / k
        sig += amp * np.sin(k * phase)
    envelope = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3.0 * t))  # ~3 syllables/sec
    sig *= envelope
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * seed_scale
    return sig.astype(np.float32)


def _linear_resample(x: np.ndarray, in_rate: int, out_rate: int) -> np.ndarray:
    n_out = int(round(len(x) * out_rate / in_rate))
    xp = np.arange(len(x))
    fp = x.astype(np.float64)
    ts = np.linspace(0, len(x) - 1, n_out)
    return np.interp(ts, xp, fp).astype(np.float32)


def run(args: argparse.Namespace) -> int:
    rng = np.random.default_rng(args.seed)
    seconds = args.seconds

    # --- Agent TTS at the speaker's native 24 kHz ---
    n_ref = int(seconds * REF_RATE)
    # Agent voice (higher pitch) vs. user voice (lower pitch) so they're distinct.
    tts_24k = (_speech_like(rng, n_ref, REF_RATE, 0.6, f0=210.0) * 12000).astype(np.int16)

    # --- Acoustic room: what the microphone hears at 16 kHz ---
    n_mic = int(seconds * MIC_RATE)
    tts_acoustic = _linear_resample(tts_24k.astype(np.float32), REF_RATE, MIC_RATE)[:n_mic]
    delay = int(args.delay_ms / 1000 * MIC_RATE)
    echo = np.zeros(n_mic, dtype=np.float32)
    echo[delay:] = tts_acoustic[: n_mic - delay] * args.echo_gain
    # Mild loudspeaker nonlinearity + sensor noise so cancellation isn't trivial.
    echo = np.tanh(echo / 9000.0) * 9000.0
    echo += rng.standard_normal(n_mic).astype(np.float32) * 60.0

    # --- User speaks only in the middle third (double-talk against the echo) ---
    user = _speech_like(rng, n_mic, MIC_RATE, args.user_gain, f0=115.0) * 12000.0
    dt_start, dt_end = n_mic // 3, 2 * n_mic // 3
    user_mask = np.zeros(n_mic, dtype=np.float32)
    user_mask[dt_start:dt_end] = 1.0
    user_active = user * user_mask

    near = (echo + user_active).astype(np.int16)

    # --- Production components ---
    canceller = build_echo_canceller(
        enabled=not args.disable_aec, stream_delay_ms=args.delay_ms
    )
    played: list[bytes] = []
    sink = ReferenceCapturingSink(lambda pcm: played.append(pcm), canceller)
    print(f"AEC mode: {canceller.mode}")

    # --- Step through the conversation in 100 ms frames, real-time ordering ---
    ref_step = REF_RATE // 10  # 2400 samples
    mic_step = MIC_RATE // 10  # 1600 samples
    cleaned = bytearray()
    steps = min(n_ref // ref_step, n_mic // mic_step)
    for k in range(steps):
        sink(tts_24k[k * ref_step : (k + 1) * ref_step].tobytes())
        out = canceller.process_capture(
            near[k * mic_step : (k + 1) * mic_step].tobytes()
        )
        cleaned += out if out else b"\x00\x00" * mic_step  # gated -> silence

    out_sig = np.frombuffer(bytes(cleaned), dtype=np.int16).astype(np.float64)
    m = min(len(out_sig), n_mic)
    out_sig, near_f = out_sig[:m], near[:m].astype(np.float64)
    user_f = user_active[:m].astype(np.float64)

    warm = MIC_RATE  # ignore first second of AEC convergence
    echo_only = np.zeros(m, dtype=bool)
    echo_only[warm:dt_start] = True
    echo_only[dt_end:] = True
    dt = np.zeros(m, dtype=bool)
    dt[max(warm, dt_start) : dt_end] = True

    def rms(x: np.ndarray) -> float:
        return float(np.sqrt(np.mean(x ** 2) + 1e-9))

    in_echo, out_echo = rms(near_f[echo_only]), rms(out_sig[echo_only])
    erle = 20 * np.log10(in_echo / out_echo)

    # Energy-based double-talk metric (correlation is unreliable on harmonic tones).
    user_rms = rms(user_f[dt])
    out_dt_rms = rms(out_sig[dt])
    dt_throughput = out_dt_rms / user_rms  # ~1.0 means the barge-in passes through

    print("--- results ---")
    print(f"ERLE (echo-only, self-voice):   {erle:6.1f} dB   (>15 dB breaks the loop)")
    print(f"echo amplitude reduction:       {in_echo / out_echo:6.1f}x")
    print(f"double-talk user throughput:    {dt_throughput:6.2f}   (barge-in loudness that survives)")

    # The product-critical objective is killing the self-echo loop.
    ok = args.disable_aec or erle > 15.0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=9.0)
    parser.add_argument("--delay-ms", type=int, default=90, help="acoustic echo delay hint")
    parser.add_argument("--echo-gain", type=float, default=0.4, help="speaker->mic coupling")
    parser.add_argument("--user-gain", type=float, default=0.75, help="user loudness (barge-in)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--disable-aec", action="store_true", help="baseline without AEC")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
