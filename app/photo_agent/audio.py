from __future__ import annotations

from typing import Any


def _module_or_default(module: Any | None) -> Any:
    if module is not None:
        return module
    import pyaudio

    return pyaudio


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
