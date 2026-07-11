from __future__ import annotations

from app.photo_agent.audio import (
    PyAudioMicrophone,
    PyAudioSpeaker,
    list_audio_devices,
    resolve_audio_device_index,
    resolve_audio_device_indices,
)


class FakeStream:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.stopped = False
        self.closed = False

    def read(self, frames: int, exception_on_overflow: bool = False) -> bytes:
        return b"a" * frames * 2

    def write(self, pcm: bytes) -> None:
        self.writes.append(pcm)

    def stop_stream(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class FakePyAudioInstance:
    def __init__(self) -> None:
        self.stream = FakeStream()
        self.opens: list[dict] = []
        self.terminated = False

    def open(self, **kwargs):
        self.opens.append(kwargs)
        return self.stream

    def terminate(self) -> None:
        self.terminated = True

    def get_device_count(self) -> int:
        return 1

    def get_device_info_by_index(self, index: int) -> dict:
        return {"index": index, "name": "fake audio", "maxInputChannels": 1, "maxOutputChannels": 1}


class FakePyAudioModule:
    paInt16 = 8

    def __init__(self) -> None:
        self.instances: list[FakePyAudioInstance] = []

    def PyAudio(self) -> FakePyAudioInstance:  # noqa: N802 - PyAudio API
        instance = FakePyAudioInstance()
        self.instances.append(instance)
        return instance


def test_microphone_and_speaker_use_selected_devices_and_release() -> None:
    module = FakePyAudioModule()
    microphone = PyAudioMicrophone(device_index=2, pyaudio_module=module)
    speaker = PyAudioSpeaker(device_index=3, pyaudio_module=module)

    assert len(microphone.read_chunk()) == 3200
    speaker(b"pcm")
    microphone.close()
    speaker.close()

    assert module.instances[0].opens[0]["input_device_index"] == 2
    assert module.instances[1].opens[0]["output_device_index"] == 3
    assert microphone.device_name == "fake audio"
    assert speaker.device_name == "fake audio"
    assert module.instances[1].stream.writes == [b"pcm"]
    assert all(instance.terminated for instance in module.instances)


def test_audio_device_enumeration_is_read_only() -> None:
    module = FakePyAudioModule()

    devices = list_audio_devices(pyaudio_module=module)

    assert devices == [
        {"index": 0, "name": "fake audio", "inputs": 1, "outputs": 1}
    ]
    assert module.instances[0].terminated is True


def test_resolve_audio_device_index_rejects_wrong_channel_explicit_index() -> None:
    devices = [
        {"index": 1, "name": "MacBook Air麦克风", "inputs": 1, "outputs": 0},
        {"index": 2, "name": "MacBook Air扬声器", "inputs": 0, "outputs": 2},
        {"index": 4, "name": "Bose QC Headphones", "inputs": 0, "outputs": 2},
    ]

    assert resolve_audio_device_index("input", explicit_index=2, devices=devices) == 1
    assert resolve_audio_device_index("output", explicit_index=3, devices=devices) == 4


def test_resolve_audio_device_index_prefers_mac_input_and_headphones_output() -> None:
    devices = [
        {"index": 0, "name": "MacBook Pro Microphone", "inputs": 1, "outputs": 0},
        {"index": 1, "name": "Bose QC Headphones", "inputs": 1, "outputs": 2},
        {"index": 2, "name": "MacBook Pro Speakers", "inputs": 0, "outputs": 2},
        {"index": 3, "name": "Bose QC Headphones", "inputs": 0, "outputs": 2},
    ]

    assert resolve_audio_device_index("input", devices=devices) == 0
    assert resolve_audio_device_index("output", devices=devices) == 3


def test_resolve_audio_device_index_honors_explicit_override() -> None:
    devices = [
        {"index": 0, "name": "MacBook Pro Microphone", "inputs": 1, "outputs": 0},
        {"index": 1, "name": "Bose QC Headphones", "inputs": 0, "outputs": 2},
    ]

    assert resolve_audio_device_index("input", explicit_index=0, devices=devices) == 0
    assert resolve_audio_device_index("output", explicit_index=1, devices=devices) == 1


def test_resolve_audio_device_indices_returns_pair() -> None:
    devices = [
        {"index": 0, "name": "MacBook Pro Microphone", "inputs": 1, "outputs": 0},
        {"index": 1, "name": "Bose QC Headphones", "inputs": 0, "outputs": 2},
    ]

    mic, speaker = resolve_audio_device_indices(devices=devices)
    assert mic == 0
    assert speaker == 1
