from __future__ import annotations

import logging
import re
from typing import Any, Literal

LOGGER = logging.getLogger("photomate.photo_agent")

AudioKind = Literal["input", "output"]

# Scored keyword lists for automatic device selection on macOS setups.
_INPUT_PREFER: tuple[tuple[str, int], ...] = (
    ("macbook", 100),
    ("mac book", 100),
    ("macbook air麦克风", 100),
    ("macbook pro microphone", 100),
    ("macbook air microphone", 100),
    ("imac", 95),
    ("built-in", 90),
    ("built in", 90),
    ("internal", 85),
    ("内建", 90),
    ("麦克风", 40),
)
_INPUT_AVOID: tuple[tuple[str, int], ...] = (
    ("bose", 60),
    ("headphone", 50),
    ("headphones", 50),
    ("耳机", 50),
    ("hdmi", 40),
    ("display", 30),
    ("aggregate", 35),
    ("external", 15),
)
_OUTPUT_PREFER: tuple[tuple[str, int], ...] = (
    ("headphone", 100),
    ("headphones", 100),
    ("耳机", 100),
    ("airpod", 95),
    ("airpods", 95),
    ("bose", 90),
    ("bluetooth", 70),
    ("usb audio", 65),
    ("external headphones", 80),
)
_OUTPUT_AVOID: tuple[tuple[str, int], ...] = (
    ("macbook pro speakers", 80),
    ("macbook air speakers", 80),
    ("built-in output", 70),
    ("built in output", 70),
    ("内建输出", 70),
    ("speakers", 25),
    ("hdmi", 50),
    ("display", 45),
    ("aggregate", 35),
    ("microphone", 20),
)


def _module_or_default(module: Any | None) -> Any:
    if module is not None:
        return module
    import pyaudio

    return pyaudio


def _device_name(instance: Any, device_index: int | None, kind: str) -> str:
    try:
        if device_index is not None:
            info = instance.get_device_info_by_index(device_index)
        elif kind == "input":
            info = instance.get_default_input_device_info()
        else:
            info = instance.get_default_output_device_info()
        return str(info.get("name", f"default {kind}"))
    except Exception:  # noqa: BLE001 - device metadata is best effort
        return f"default {kind}" if device_index is None else f"{kind}:{device_index}"


class PyAudioMicrophone:
    def __init__(
        self,
        device_index: int | None = None,
        *,
        rate: int = 16000,
        chunk_frames: int = 1600,
        pyaudio_module: Any | None = None,
    ) -> None:
        self.module = _module_or_default(pyaudio_module)
        self.chunk_frames = chunk_frames
        self.instance = self.module.PyAudio()
        self.device_name = _device_name(self.instance, device_index, "input")
        kwargs = {
            "format": self.module.paInt16,
            "channels": 1,
            "rate": rate,
            "input": True,
            "frames_per_buffer": chunk_frames,
        }
        if device_index is not None:
            kwargs["input_device_index"] = device_index
        self.stream = self.instance.open(**kwargs)

    def read_chunk(self) -> bytes:
        return self.stream.read(self.chunk_frames, exception_on_overflow=False)

    def close(self) -> None:
        self.stream.stop_stream()
        self.stream.close()
        self.instance.terminate()


class PyAudioSpeaker:
    def __init__(
        self,
        device_index: int | None = None,
        *,
        rate: int = 24000,
        pyaudio_module: Any | None = None,
    ) -> None:
        self.module = _module_or_default(pyaudio_module)
        self.instance = self.module.PyAudio()
        self.device_name = _device_name(self.instance, device_index, "output")
        kwargs = {
            "format": self.module.paInt16,
            "channels": 1,
            "rate": rate,
            "output": True,
        }
        if device_index is not None:
            kwargs["output_device_index"] = device_index
        self.stream = self.instance.open(**kwargs)

    def __call__(self, pcm: bytes) -> None:
        self.stream.write(pcm)

    def close(self) -> None:
        self.stream.stop_stream()
        self.stream.close()
        self.instance.terminate()


def _normalize_device_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _score_device_name(
    name: str,
    *,
    prefer: tuple[tuple[str, int], ...],
    avoid: tuple[tuple[str, int], ...],
) -> int:
    normalized = _normalize_device_name(name)
    score = 0
    for keyword, weight in prefer:
        if keyword in normalized:
            score += weight
    for keyword, weight in avoid:
        if keyword in normalized:
            score -= weight
    return score


def _device_supports_kind(devices: list[dict[str, Any]], index: int, kind: AudioKind) -> bool:
    channel_key = "inputs" if kind == "input" else "outputs"
    for device in devices:
        if int(device.get("index", -1)) == index:
            return int(device.get(channel_key, 0)) > 0
    return False


def resolve_audio_device_index(
    kind: AudioKind,
    *,
    explicit_index: int | None = None,
    devices: list[dict[str, Any]] | None = None,
    pyaudio_module: Any | None = None,
) -> int | None:
    """Pick an audio device index; ``None`` means PyAudio/system default."""
    if devices is None:
        devices = list_audio_devices(pyaudio_module=pyaudio_module)

    if explicit_index is not None:
        if _device_supports_kind(devices, explicit_index, kind):
            return explicit_index
        invalid_name = next(
            (str(device.get("name", explicit_index)) for device in devices if int(device.get("index", -1)) == explicit_index),
            str(explicit_index),
        )
        LOGGER.warning(
            "audio_device_invalid_for_kind",
            extra={
                "kind": kind,
                "index": explicit_index,
                "device_name": invalid_name,
                "fallback": "auto",
            },
        )

    channel_key = "inputs" if kind == "input" else "outputs"
    other_key = "outputs" if kind == "input" else "inputs"
    prefer = _INPUT_PREFER if kind == "input" else _OUTPUT_PREFER
    avoid = _INPUT_AVOID if kind == "input" else _OUTPUT_AVOID

    candidates = [device for device in devices if int(device.get(channel_key, 0)) > 0]
    if not candidates:
        return None

    ranked = sorted(
        (
            (
                _score_device_name(str(device.get("name", "")), prefer=prefer, avoid=avoid)
                + (25 if int(device.get(other_key, 0)) == 0 else 0),
                int(device["index"]),
                str(device.get("name", "")),
            )
            for device in candidates
        ),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    best_score, best_index, best_name = ranked[0]
    if best_score <= 0:
        LOGGER.info(
            "audio_device_auto_default",
            extra={"kind": kind, "reason": "no_preferred_match"},
        )
        return None

    LOGGER.info(
        "audio_device_auto_selected",
        extra={
            "kind": kind,
            "index": best_index,
            "device_name": best_name,
            "score": best_score,
        },
    )
    return best_index


def resolve_audio_device_indices(
    *,
    microphone_index: int | None = None,
    speaker_index: int | None = None,
    devices: list[dict[str, Any]] | None = None,
    pyaudio_module: Any | None = None,
) -> tuple[int | None, int | None]:
    if devices is None:
        devices = list_audio_devices(pyaudio_module=pyaudio_module)
    mic = resolve_audio_device_index(
        "input",
        explicit_index=microphone_index,
        devices=devices,
        pyaudio_module=pyaudio_module,
    )
    speaker = resolve_audio_device_index(
        "output",
        explicit_index=speaker_index,
        devices=devices,
        pyaudio_module=pyaudio_module,
    )
    return mic, speaker


def list_audio_devices(*, pyaudio_module: Any | None = None) -> list[dict[str, Any]]:
    module = _module_or_default(pyaudio_module)
    instance = module.PyAudio()
    try:
        devices: list[dict[str, Any]] = []
        for index in range(instance.get_device_count()):
            info = instance.get_device_info_by_index(index)
            devices.append(
                {
                    "index": index,
                    "name": str(info.get("name", index)),
                    "inputs": int(info.get("maxInputChannels", 0)),
                    "outputs": int(info.get("maxOutputChannels", 0)),
                }
            )
        return devices
    finally:
        instance.terminate()
