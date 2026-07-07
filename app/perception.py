from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class GuestSignal(str, Enum):
    NONE = "none"
    APPROACHING = "approaching"
    LOITERING = "loitering"
    WAVING = "waving"
    WEB_REQUEST = "web_request"


@dataclass
class GuestObservation:
    signal: GuestSignal = GuestSignal.NONE
    confidence: float = 0.0
    person_count: int = 0
    dwell_sec: float = 0.0
    message: str = ""
    source: str = "mock"


@dataclass
class PerceptionConfig:
    loiter_threshold_sec: float = 3.0
    approach_distance_m: float = 2.5
    mock_signal_interval_sec: float = 25.0
    enabled: bool = True


class GuestDetector:
    """发现「可能想拍照」的嘉宾。真机 9 日接 Galbot 头摄 RGB。"""

    def __init__(self, cfg: PerceptionConfig, *, mock: bool = True) -> None:
        self._cfg = cfg
        self._mock = mock
        self._web_pending = False
        self._last_person_center: tuple[float, float] | None = None
        self._loiter_since: float | None = None
        self._mock_next_ping = time.time() + cfg.mock_signal_interval_sec
        self._camera_fn: Callable[[], Any] | None = None

    def set_camera_source(self, fn: Callable[[], Any]) -> None:
        self._camera_fn = fn

    def notify_web_request(self) -> None:
        self._web_pending = True

    def clear_web_request(self) -> None:
        self._web_pending = False

    def poll(self) -> GuestObservation:
        if not self._cfg.enabled:
            return GuestObservation(message="感知已关闭")

        if self._web_pending:
            self._web_pending = False
            return GuestObservation(
                signal=GuestSignal.WEB_REQUEST,
                confidence=1.0,
                message="网页按钮：我要拍照",
                source="dashboard",
            )

        if self._mock:
            return self._poll_mock()
        return self._poll_camera()

    def _poll_mock(self) -> GuestObservation:
        now = time.time()
        if now >= self._mock_next_ping:
            self._mock_next_ping = now + self._cfg.mock_signal_interval_sec
            roll = random.random()
            if roll < 0.5:
                return GuestObservation(
                    signal=GuestSignal.LOITERING,
                    confidence=0.75,
                    person_count=1,
                    dwell_sec=self._cfg.loiter_threshold_sec + 0.5,
                    message="[mock] 有人驻足观看",
                    source="mock",
                )
            return GuestObservation(
                signal=GuestSignal.APPROACHING,
                confidence=0.7,
                person_count=1,
                message="[mock] 有人靠近",
                source="mock",
            )
        return GuestObservation(message="[mock] 无信号")

    def _poll_camera(self) -> GuestObservation:
        # 9 日真机：get_camera_data → YOLO/MediaPipe 人体框 → 驻足计时
        if not self._camera_fn:
            return GuestObservation(message="未配置相机源", source="camera")

        try:
            frame = self._camera_fn()
        except Exception as exc:  # noqa: BLE001
            return GuestObservation(message=f"取流失败: {exc}", source="camera")

        if frame is None:
            return GuestObservation(message="无画面", source="camera")

        # TODO(7/9): 接入 detector，返回 bbox 列表
        _ = frame
        return GuestObservation(message="相机已接，检测器待接入", source="camera")

    def update_loiter_from_bbox(self, center_xy: tuple[float, float], now: float | None = None) -> GuestObservation:
        """真机检测循环调用：根据人体框中心位移判断驻足。"""
        ts = now if now is not None else time.time()
        if self._last_person_center is None:
            self._last_person_center = center_xy
            self._loiter_since = ts
            return GuestObservation(person_count=1, message="首次发现人体")

        dx = center_xy[0] - self._last_person_center[0]
        dy = center_xy[1] - self._last_person_center[1]
        moved = (dx * dx + dy * dy) ** 0.5

        if moved > 0.08:
            self._last_person_center = center_xy
            self._loiter_since = ts
            return GuestObservation(
                signal=GuestSignal.APPROACHING,
                confidence=0.6,
                person_count=1,
                message="人体移动中",
                source="camera",
            )

        dwell = ts - (self._loiter_since or ts)
        if dwell >= self._cfg.loiter_threshold_sec:
            return GuestObservation(
                signal=GuestSignal.LOITERING,
                confidence=min(0.95, 0.5 + dwell / 10.0),
                person_count=1,
                dwell_sec=dwell,
                message=f"驻足 {dwell:.1f}s",
                source="camera",
            )

        return GuestObservation(person_count=1, dwell_sec=dwell, message="等待驻足计时", source="camera")
