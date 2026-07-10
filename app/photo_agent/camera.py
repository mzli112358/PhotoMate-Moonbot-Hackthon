"""Local OpenCV camera, wake detection, and quality checking adapters."""

from __future__ import annotations

import asyncio
import base64
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from app.photo_agent.models import CaptureResult, QualityResult, WakeSignal

MAX_IMAGE_B64_BYTES = 256 * 1024


def encode_frame(frame: np.ndarray, max_bytes: int = MAX_IMAGE_B64_BYTES) -> str | None:
    """Encode a frame for Omni while enforcing the documented Base64 limit."""
    if frame is None or not getattr(frame, "size", 0):
        return None
    working = frame
    max_edge = 960
    for _ in range(4):
        height, width = working.shape[:2]
        if max(height, width) > max_edge:
            scale = max_edge / max(height, width)
            working = cv2.resize(working, (max(1, int(width * scale)), max(1, int(height * scale))))
        for quality in (80, 70, 60, 50, 40, 30):
            ok, encoded = cv2.imencode(".jpg", working, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ok:
                return None
            value = base64.b64encode(encoded.tobytes()).decode("ascii")
            if len(value) <= max_bytes:
                return value
        max_edge = int(max_edge * 0.75)
    return None


class OpenCVCamera:
    def __init__(
        self,
        device_index: int,
        photo_dir: Path,
        *,
        capture_factory: Callable[[int], Any] = cv2.VideoCapture,
    ) -> None:
        self.device_index = device_index
        self.photo_dir = photo_dir
        self.capture_factory = capture_factory
        self._capture: Any | None = None
        self._lock = asyncio.Lock()
        self._latest_frame: np.ndarray | None = None

    @property
    def device_name(self) -> str:
        backend = "not-opened"
        if self._capture is not None:
            try:
                backend = self._capture.getBackendName()
            except Exception:  # noqa: BLE001
                backend = "opencv"
        return f"camera:{self.device_index} ({backend})"

    def _open(self) -> None:
        if self._capture is not None:
            return
        capture = self.capture_factory(self.device_index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"camera {self.device_index} cannot be opened")
        self._capture = capture

    def open(self) -> None:
        """Open on the caller thread so macOS can perform camera permission checks."""
        self._open()

    def _read(self) -> np.ndarray:
        self._open()
        assert self._capture is not None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"camera {self.device_index} failed to read a frame")
        self._latest_frame = frame.copy()
        return frame

    async def get_frame(self) -> np.ndarray:
        async with self._lock:
            return await asyncio.to_thread(self._read)

    def latest_frame(self) -> np.ndarray | None:
        return None if self._latest_frame is None else self._latest_frame.copy()

    async def capture(self, mode: str = "photo") -> CaptureResult:
        if mode != "photo":
            return CaptureResult("", Path(), False, error=f"unsupported mode: {mode}")
        try:
            frame = await self.get_frame()
            photo_id = uuid.uuid4().hex
            self.photo_dir.mkdir(parents=True, exist_ok=True)
            path = self.photo_dir / f"{photo_id}.jpg"
            ok = await asyncio.to_thread(cv2.imwrite, str(path), frame)
            if not ok:
                raise RuntimeError("cv2.imwrite returned false")
            return CaptureResult(photo_id, path, True, frame.copy())
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            return CaptureResult("", Path(), False, error=str(exc))

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.close_sync)

    def close_sync(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()


def _default_face_detector() -> Callable[[np.ndarray], Any]:
    cascade = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
    return lambda gray: cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))


def _default_eye_detector() -> Callable[[np.ndarray], Any]:
    cascade = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_eye_tree_eyeglasses.xml"))
    return lambda gray: cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(12, 12))


class FaceWakeDetector:
    """V0 wake proxy: a stable frontal face means present and facing the robot."""

    def __init__(
        self,
        camera: OpenCVCamera,
        *,
        face_detector: Callable[[np.ndarray], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.camera = camera
        self.face_detector = face_detector or _default_face_detector()
        self.clock = clock
        self._first_seen_at: float | None = None

    async def poll(self) -> WakeSignal:
        frame = await self.camera.get_frame()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = list(self.face_detector(gray))
        now = self.clock()
        if not faces:
            self._first_seen_at = None
            return WakeSignal(False, 0.0, False)
        largest = max(faces, key=lambda face: face[2] * face[3])
        x, y, width, height = (float(value) for value in largest)
        center_x = x + width / 2
        facing = abs(center_x - frame.shape[1] / 2) <= frame.shape[1] * 0.35 and height > 0
        if not facing:
            self._first_seen_at = None
            return WakeSignal(True, 0.0, False)
        if self._first_seen_at is None:
            self._first_seen_at = now
        return WakeSignal(True, max(0.0, now - self._first_seen_at), True)


class OpenCVQualityChecker:
    def __init__(
        self,
        *,
        face_detector: Callable[[np.ndarray], Any] | None = None,
        eye_detector: Callable[[np.ndarray], Any] | None = None,
        sharpness_threshold: float = 80.0,
    ) -> None:
        self.face_detector = face_detector or _default_face_detector()
        self.eye_detector = eye_detector or _default_eye_detector()
        self.sharpness_threshold = sharpness_threshold

    def check(self, image: np.ndarray) -> QualityResult:
        if image is None or not getattr(image, "size", 0):
            return QualityResult(False, False, False, "missing_image")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = list(self.face_detector(gray))
        sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var()) >= self.sharpness_threshold
        face_in_frame = bool(faces)
        eyes_open = False
        if faces:
            x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
            roi = gray[y : y + height, x : x + width]
            eyes_open = len(list(self.eye_detector(roi))) >= 1
        reasons: list[str] = []
        if not face_in_frame:
            reasons.append("face_not_found")
        if face_in_frame and not eyes_open:
            reasons.append("eyes_closed_or_not_found")
        if not sharp:
            reasons.append("blurred")
        return QualityResult(face_in_frame, eyes_open, sharp, ",".join(reasons) or None)
