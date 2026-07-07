from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from app.perception import GuestDetector, GuestObservation, GuestSignal, PerceptionConfig


class TaskState(str, Enum):
    IDLE = "idle"
    PATROL = "patrol"
    GREET = "greet"
    NAVIGATE = "navigate"
    SHOOT_PHONE = "shoot_phone"
    SHOOT_CAMERA = "shoot_camera"
    DELIVER = "deliver"
    FAILED = "failed"


SHOOT_MODES = ("phone", "camera")


@dataclass
class TaskContext:
    state: TaskState = TaskState.IDLE
    shoot_mode: str = "phone"
    target_spot_id: str | None = None
    guest_signal: str = GuestSignal.NONE.value
    message: str = ""
    updated_at: float = field(default_factory=time.time)
    history: list[str] = field(default_factory=list)

    def bump(self, msg: str) -> None:
        self.message = msg
        self.updated_at = time.time()
        self.history.append(f"{time.strftime('%H:%M:%S')} {self.state.value}: {msg}")
        if len(self.history) > 40:
            self.history = self.history[-40:]


class PhotoMateFSM:
    """应用层 Agent：巡航 → 发现用户 → 导航 → 拍摄 → 交付。"""

    def __init__(
        self,
        *,
        perception: PerceptionConfig | None = None,
        mock: bool = True,
        on_start_patrol: Callable[[], dict[str, Any]] | None = None,
        on_stop_patrol: Callable[[], None] | None = None,
        on_navigate: Callable[[str], dict[str, Any]] | None = None,
        on_speak: Callable[[str], None] | None = None,
    ) -> None:
        self._ctx = TaskContext()
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._detector = GuestDetector(perception or PerceptionConfig(), mock=mock)
        self._on_start_patrol = on_start_patrol
        self._on_stop_patrol = on_stop_patrol
        self._on_navigate = on_navigate
        self._on_speak = on_speak or (lambda _t: None)
        self._default_spot_id = "spot_a"

    @property
    def detector(self) -> GuestDetector:
        return self._detector

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._ctx.state.value,
                "shoot_mode": self._ctx.shoot_mode,
                "target_spot_id": self._ctx.target_spot_id,
                "guest_signal": self._ctx.guest_signal,
                "message": self._ctx.message,
                "updated_at": self._ctx.updated_at,
                "running": self._running,
                "history": list(self._ctx.history),
            }

    def start_patrol_mode(self, shoot_mode: str = "phone", spot_id: str | None = None) -> dict[str, Any]:
        if shoot_mode not in SHOOT_MODES:
            return {"ok": False, "message": f"未知拍摄模式: {shoot_mode}"}
        if self._running:
            return {"ok": False, "message": "Agent 已在运行"}

        self._default_spot_id = spot_id or self._default_spot_id
        with self._lock:
            self._ctx.shoot_mode = shoot_mode
            self._ctx.target_spot_id = self._default_spot_id
            self._set_state(TaskState.PATROL, "开始场内巡航")

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if self._on_start_patrol:
            self._on_start_patrol()
        return {"ok": True, "message": "Agent 巡航已启动", "state": TaskState.PATROL.value}

    def stop(self) -> dict[str, Any]:
        self._running = False
        if self._on_stop_patrol:
            self._on_stop_patrol()
        with self._lock:
            self._set_state(TaskState.IDLE, "Agent 已停止")
        return {"ok": True, "message": "已停止"}

    def confirm_guest(self, accept: bool = True, spot_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self._ctx.state != TaskState.GREET:
                return {"ok": False, "message": f"当前状态 {self._ctx.state.value}，无法确认"}
            if not accept:
                self._set_state(TaskState.PATROL, "用户拒绝，继续巡航")
                return {"ok": True, "message": "继续巡航"}
            sid = spot_id or self._ctx.target_spot_id or self._default_spot_id
            self._ctx.target_spot_id = sid
            self._set_state(TaskState.NAVIGATE, f"前往 {sid}")
        self._on_speak("好的，请跟我到合影位置。")
        if self._on_navigate:
            self._on_navigate(sid)
        return {"ok": True, "message": "已确认，开始导航", "spot_id": sid}

    def on_navigation_arrived(self, spot_id: str) -> None:
        with self._lock:
            if self._ctx.state != TaskState.NAVIGATE:
                return
            self._ctx.target_spot_id = spot_id
            if self._ctx.shoot_mode == "camera":
                self._set_state(TaskState.SHOOT_CAMERA, "到达，准备 Insta360 拍摄")
            else:
                self._set_state(TaskState.SHOOT_PHONE, "到达，请把手机递给我")
        self._on_speak("请看镜头，三、二、一。")

    def on_shoot_done(self, success: bool = True) -> None:
        with self._lock:
            if self._ctx.state not in (TaskState.SHOOT_PHONE, TaskState.SHOOT_CAMERA):
                return
            if not success:
                self._set_state(TaskState.FAILED, "拍摄失败")
                return
            self._set_state(TaskState.DELIVER, "拍摄完成，交付中")
        self._on_speak("照片好了，请查收。")

    def on_deliver_done(self) -> None:
        with self._lock:
            self._set_state(TaskState.PATROL, "交付完成，继续巡航")
        if self._on_start_patrol:
            self._on_start_patrol()

    def notify_web_photo_request(self) -> dict[str, Any]:
        self._detector.notify_web_request()
        with self._lock:
            if self._ctx.state in (TaskState.PATROL, TaskState.IDLE):
                self._set_state(TaskState.GREET, "网页请求拍照")
        return {"ok": True, "message": "已记录网页拍照请求"}

    def _set_state(self, state: TaskState, message: str) -> None:
        self._ctx.state = state
        self._ctx.bump(message)

    def _loop(self) -> None:
        while self._running:
            obs = self._detector.poll()
            with self._lock:
                self._ctx.guest_signal = obs.signal.value
                state = self._ctx.state

            if state == TaskState.PATROL and obs.signal in (
                GuestSignal.LOITERING,
                GuestSignal.WAVING,
                GuestSignal.WEB_REQUEST,
            ):
                with self._lock:
                    self._set_state(TaskState.GREET, obs.message or "发现潜在用户")
                self._on_speak("你好，需要我帮你拍照吗？")

            elif state == TaskState.SHOOT_PHONE:
                # 7/9 接 M2/M3：接手机、点快门后调 on_shoot_done()
                pass
            elif state == TaskState.SHOOT_CAMERA:
                # 7/9 接 M4：Insta360 拍照后调 on_shoot_done()
                pass
            elif state == TaskState.DELIVER:
                # 7/11 前接 M5 打印；现在可自动回巡航
                self.on_deliver_done()

            time.sleep(0.5)
