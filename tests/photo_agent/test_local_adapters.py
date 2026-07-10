from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.photo_agent.camera import FaceWakeDetector, OpenCVCamera, OpenCVQualityChecker, encode_frame
from app.photo_agent.delivery import FileDeliveryAdapter, PhotoStore


class FakeCapture:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self.frames = frames
        self.index = 0
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 - OpenCV API
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        frame = self.frames[min(self.index, len(self.frames) - 1)].copy()
        self.index += 1
        return True, frame

    def release(self) -> None:
        self.released = True

    def getBackendName(self) -> str:  # noqa: N802 - OpenCV API
        return "FAKE"


@pytest.mark.asyncio
async def test_opencv_camera_captures_current_frame_and_releases(tmp_path: Path) -> None:
    frame = np.full((24, 32, 3), 127, dtype=np.uint8)
    fake = FakeCapture([frame])
    camera = OpenCVCamera(0, tmp_path, capture_factory=lambda _: fake)

    camera.open()
    assert "FAKE" in camera.device_name
    assert await camera.get_frame() is not None
    preview = camera.latest_frame()
    assert preview is not None
    preview[:] = 0
    assert camera.latest_frame().mean() == 127
    result = await camera.capture()
    await camera.close()

    assert result.ok is True
    assert result.photo_id
    assert result.path.is_file()
    loaded = cv2.imread(str(result.path))
    assert loaded.shape == frame.shape
    assert fake.released is True


def test_encode_frame_obeys_realtime_image_limit() -> None:
    rng = np.random.default_rng(7)
    frame = rng.integers(0, 256, (2160, 3840, 3), dtype=np.uint8)

    encoded = encode_frame(frame)

    assert encoded is not None
    assert len(encoded) <= 256 * 1024


@pytest.mark.asyncio
async def test_wake_detector_requires_face_and_tracks_dwell(tmp_path: Path) -> None:
    frame = np.ones((10, 10, 3), dtype=np.uint8)
    camera = OpenCVCamera(0, tmp_path, capture_factory=lambda _: FakeCapture([frame]))
    now = iter([10.0, 11.0, 13.2])
    detector = FaceWakeDetector(
        camera,
        face_detector=lambda _: [(1, 1, 4, 4)],
        clock=lambda: next(now),
    )

    first = await detector.poll()
    second = await detector.poll()
    third = await detector.poll()

    assert first.person_present is True and first.dwell_seconds == 0
    assert second.dwell_seconds == 1.0
    assert third.is_awake(3.0) is True
    await camera.close()


def test_quality_checker_rejects_no_face_and_blur() -> None:
    checker = OpenCVQualityChecker(face_detector=lambda _: [], eye_detector=lambda _: [])
    blank = np.zeros((64, 64, 3), dtype=np.uint8)

    result = checker.check(blank)

    assert result.ok is False
    assert result.face_in_frame is False
    assert result.sharp is False
    assert result.reason


@pytest.mark.asyncio
async def test_file_delivery_registers_only_existing_photo(tmp_path: Path) -> None:
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"jpeg")
    store = PhotoStore()
    store.register("p1", photo)
    adapter = FileDeliveryAdapter(store, "http://127.0.0.1:8000")

    assert await adapter.show("p1") is True
    result = await adapter.deliver("p1")

    assert result.ok is True
    assert result.photo_url == "http://127.0.0.1:8000/api/photos/p1"
    assert store.resolve("../etc/passwd") is None
