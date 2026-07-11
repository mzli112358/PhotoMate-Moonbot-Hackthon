from __future__ import annotations

import pytest

from scripts.photo_agent.omni_smoke import capture_microphone_chunks, detect_timeout


@pytest.mark.asyncio
async def test_omni_smoke_captures_real_microphone_chunks_and_closes() -> None:
    class Microphone:
        def __init__(self, device_index=None):
            self.device_index = device_index
            self.closed = False
            self.reads = 0

        def read_chunk(self) -> bytes:
            self.reads += 1
            return f"chunk-{self.reads}".encode()

        def close(self) -> None:
            self.closed = True

    microphone = Microphone(2)

    chunks = await capture_microphone_chunks(
        2,
        count=3,
        microphone_factory=lambda device_index: microphone,
    )

    assert chunks == [b"chunk-1", b"chunk-2", b"chunk-3"]
    assert microphone.device_index == 2
    assert microphone.closed is True


@pytest.mark.asyncio
async def test_smoke_timeout_check_is_observed_not_hardcoded() -> None:
    class Client:
        async def next_event(self, timeout=None):
            raise TimeoutError("expected timeout")

    assert await detect_timeout(Client(), timeout=0.01) is True
