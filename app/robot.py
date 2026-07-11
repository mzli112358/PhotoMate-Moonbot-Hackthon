from __future__ import annotations

import asyncio
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import AppYaml, load_waypoints
from app.map_loader import yaw_deg_from_quat
from app.schemas import PoseOut


@dataclass
class NavigationState:
    localized: bool = False
    navigation_status: str = "idle"
    target_spot_id: str | None = None
    message: str = ""
    pose: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    patrol_active: bool = False
    patrol_loop: bool = False
    patrol_index: int = 0


class RobotBridge:
    """Galbot SDK 桥接；无真机时走 mock 演示。"""

    def __init__(self, app_config: AppYaml) -> None:
        self._cfg = app_config
        self._state = NavigationState(localized=True)
        self._lock = threading.RLock()
        self._nav_thread: threading.Thread | None = None
        self._patrol_thread: threading.Thread | None = None
        self._stop_nav = threading.Event()
        self._galbot_nav = None
        self._galbot_robot = None
        self._mock_t0 = time.time()
        self._on_arrived: Callable[[str], None] | None = None

        if not app_config.robot.mock:
            self._init_galbot()

    def _init_galbot(self) -> None:
        model = self._cfg.robot.model.lower()
        try:
            if model == "s1":
                from galbot_sdk.s1 import GalbotNavigation, GalbotRobot
                from galbot_sdk.s1 import ControlStatus, S1ControllerName

                chassis_ctrl = S1ControllerName.SWERVE_CHASSIS_POSE_CTRL
                self._switch_controller = lambda robot, c=chassis_ctrl: robot.switch_controller(c)
                self._control_ok = ControlStatus.SUCCESS
            else:
                from galbot_sdk.g1 import GalbotNavigation, GalbotRobot
                from galbot_sdk.g1 import ControlStatus, G1ControllerName

                chassis_ctrl = G1ControllerName.CHASSIS_POSE_CTRL
                self._switch_controller = lambda robot, c=chassis_ctrl: robot.switch_controller(c)
                self._control_ok = ControlStatus.SUCCESS

            self._galbot_robot = GalbotRobot()
            self._galbot_nav = GalbotNavigation()
            if not self._galbot_robot.init():
                raise RuntimeError("GalbotRobot.init() failed")
            if not self._galbot_nav.init():
                raise RuntimeError("GalbotNavigation.init() failed")
            res = self._switch_controller(self._galbot_robot)
            if res != self._control_ok:
                raise RuntimeError("Failed to switch chassis controller")
            with self._lock:
                self._state.localized = self._galbot_nav.is_localized()
                self._state.message = "Galbot SDK 已连接"
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._state.message = f"Galbot 初始化失败，回退 mock: {exc}"
            self._cfg.robot.mock = True

    def set_on_arrived(self, callback: Callable[[str], None] | None) -> None:
        self._on_arrived = callback

    @property
    def is_mock(self) -> bool:
        return self._cfg.robot.mock

    def get_spot(self, spot_id: str) -> dict[str, Any] | None:
        for spot in load_waypoints().get("photo_spots", []):
            if spot.get("id") == spot_id:
                return spot
        return None

    def list_spots(self) -> list[dict[str, Any]]:
        return list(load_waypoints().get("photo_spots", []))

    def _read_pose_galbot(self) -> list[float]:
        assert self._galbot_nav is not None
        pose = self._galbot_nav.get_current_pose()
        if hasattr(pose, "tolist"):
            return list(pose.tolist())
        return list(pose)

    def _read_pose_mock(self) -> list[float]:
        t = time.time() - self._mock_t0
        x = 0.8 * math.cos(t * 0.12)
        y = 0.8 * math.sin(t * 0.12)
        yaw = t * 0.12
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)
        return [x, y, 0.0, 0.0, 0.0, qz, qw]

    def read_pose(self) -> PoseOut | None:
        with self._lock:
            if self.is_mock:
                raw = self._state.pose if self._state.navigation_status == "navigating" else self._read_pose_mock()
                localized = True
            else:
                if not self._galbot_nav:
                    return None
                localized = self._galbot_nav.is_localized()
                if not localized:
                    return None
                raw = self._read_pose_galbot()

        return PoseOut(
            x=raw[0],
            y=raw[1],
            z=raw[2],
            qx=raw[3],
            qy=raw[4],
            qz=raw[5],
            qw=raw[6],
            yaw_deg=yaw_deg_from_quat(raw[3], raw[4], raw[5], raw[6]),
            frame_id="map",
        )

    def status_snapshot(self) -> dict[str, Any]:
        pose = self.read_pose()
        with self._lock:
            return {
                "mock": self.is_mock,
                "localized": self._state.localized if self.is_mock else bool(pose),
                "navigation_status": self._state.navigation_status,
                "pose": pose.model_dump() if pose else None,
                "target_spot_id": self._state.target_spot_id,
                "message": self._state.message,
                "patrol_active": self._state.patrol_active,
                "patrol_loop": self._state.patrol_loop,
                "patrol_index": self._state.patrol_index,
            }

    def patrol_spot_ids(self) -> list[str]:
        spots = load_waypoints().get("photo_spots", [])
        patrol = [s["id"] for s in spots if s.get("patrol", True) and s.get("id")]
        return patrol or [s["id"] for s in spots if s.get("id")]

    def start_patrol(self, *, loop: bool = True) -> dict[str, Any]:
        if self._patrol_thread and self._patrol_thread.is_alive():
            return {"ok": False, "message": "巡航已在进行"}
        if self._nav_thread and self._nav_thread.is_alive():
            return {"ok": False, "message": "单点导航进行中，请先停止"}

        spot_ids = self.patrol_spot_ids()
        if len(spot_ids) < 1:
            return {"ok": False, "message": "无可用航点"}

        with self._lock:
            self._state.patrol_active = True
            self._state.patrol_loop = loop
            self._state.patrol_index = 0
            self._state.message = f"巡航启动，共 {len(spot_ids)} 站"

        def _run() -> None:
            idx = 0
            self._stop_nav.clear()
            while not self._stop_nav.is_set():
                spot_id = spot_ids[idx % len(spot_ids)]
                with self._lock:
                    self._state.patrol_index = idx % len(spot_ids)
                result = self._navigate_spot_blocking(spot_id)
                if self._stop_nav.is_set():
                    break
                if not result.get("ok"):
                    with self._lock:
                        self._state.message = result.get("message", "巡航失败")
                    break
                idx += 1
                if not loop and idx >= len(spot_ids):
                    break
            with self._lock:
                self._state.patrol_active = False
                if self._state.navigation_status == "navigating":
                    self._state.navigation_status = "idle"

        self._patrol_thread = threading.Thread(target=_run, daemon=True)
        self._patrol_thread.start()
        return {"ok": True, "message": "巡航已启动", "spots": spot_ids, "loop": loop}

    def stop_patrol(self) -> None:
        self.stop_navigation()
        with self._lock:
            self._state.patrol_active = False
            self._state.message = "巡航已停止"

    def _navigate_spot_blocking(self, spot_id: str) -> dict[str, Any]:
        spot = self.get_spot(spot_id)
        if not spot:
            return {"ok": False, "message": f"未知航点: {spot_id}"}
        with self._lock:
            self._state.navigation_status = "navigating"
            self._state.target_spot_id = spot_id
            self._state.message = f"巡航 → {spot.get('name', spot_id)}"
        try:
            if self.is_mock:
                self._navigate_mock(spot)
            else:
                self._navigate_galbot(spot)
            with self._lock:
                ok = self._state.navigation_status == "arrived"
            return {"ok": ok, "message": self._state.message, "spot_id": spot_id}
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._state.navigation_status = "failed"
                self._state.message = str(exc)
            return {"ok": False, "message": str(exc)}

    def stop_navigation(self) -> None:
        self._stop_nav.set()
        with self._lock:
            self._state.navigation_status = "idle"
            self._state.target_spot_id = None
            self._state.message = "导航已停止"
        if not self.is_mock and self._galbot_nav:
            try:
                self._galbot_nav.stop_navigation()
            except Exception:  # noqa: BLE001
                pass

    def _navigate_mock(self, spot: dict[str, Any]) -> None:
        goal = spot["pose"]
        start = self._state.pose[:] if self._state.pose else [0, 0, 0, 0, 0, 0, 1]
        duration = 8.0
        t0 = time.time()
        self._stop_nav.clear()
        while not self._stop_nav.is_set():
            elapsed = time.time() - t0
            if elapsed >= duration:
                break
            alpha = min(1.0, elapsed / duration)
            pose = [start[i] + (goal[i] - start[i]) * alpha for i in range(7)]
            # 四元数部分简单 slerp 近似：接近目标时直接用目标朝向
            if alpha > 0.85:
                pose[3:7] = goal[3:7]
            with self._lock:
                self._state.pose = pose
            time.sleep(0.05)
        with self._lock:
            self._state.pose = goal[:]
            self._state.navigation_status = "arrived"
            self._state.message = f"已到达 {spot.get('name', spot['id'])}"
        if self._on_arrived:
            self._on_arrived(spot["id"])

    def _navigate_galbot(self, spot: dict[str, Any]) -> None:
        assert self._galbot_nav is not None
        goal = spot["pose"]
        timeout = self._cfg.navigation.goal_timeout_sec
        if not self._galbot_nav.is_localized():
            self._galbot_nav.relocalize(goal)
            time.sleep(0.5)
        current = self._galbot_nav.get_current_pose()
        if hasattr(self._galbot_nav, "check_path_reachability"):
            if not self._galbot_nav.check_path_reachability(goal, current):
                with self._lock:
                    self._state.navigation_status = "failed"
                    self._state.message = "路径不可达"
                return
        status = self._galbot_nav.navigate_to_goal(
            goal,
            enable_collision_check=True,
            is_blocking=True,
            timeout=timeout,
        )
        arrived = self._galbot_nav.check_goal_arrival()
        with self._lock:
            self._state.navigation_status = "arrived" if arrived else "failed"
            self._state.message = f"navigate_to_goal: {status}"
        if arrived and self._on_arrived:
            self._on_arrived(spot["id"])

    def navigate_through_spots(self, spot_ids: list[str]) -> dict[str, Any]:
        """多航点一次提交（真机用 SDK navigate_through_waypoints）。"""
        spots = [self.get_spot(sid) for sid in spot_ids]
        if any(s is None for s in spots):
            return {"ok": False, "message": "航点列表含未知 id"}

        if self._nav_thread and self._nav_thread.is_alive():
            return {"ok": False, "message": "已有导航任务进行中"}

        def _run() -> None:
            with self._lock:
                self._state.navigation_status = "navigating"
                self._state.message = f"多航点导航 ×{len(spot_ids)}"
            try:
                if self.is_mock:
                    for spot in spots:
                        if self._stop_nav.is_set():
                            break
                        assert spot is not None
                        self._navigate_mock(spot)
                else:
                    self._navigate_galbot_waypoints([s for s in spots if s])
                with self._lock:
                    if self._state.navigation_status != "failed":
                        self._state.navigation_status = "arrived"
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._state.navigation_status = "failed"
                    self._state.message = str(exc)

        self._stop_nav.clear()
        self._nav_thread = threading.Thread(target=_run, daemon=True)
        self._nav_thread.start()
        return {"ok": True, "message": "多航点导航已启动", "spot_ids": spot_ids}

    def _navigate_galbot_waypoints(self, spots: list[dict[str, Any]]) -> None:
        assert self._galbot_nav is not None
        model = self._cfg.robot.model.lower()
        if model == "s1":
            from galbot_sdk.s1 import Pose, Waypoint, WaypointParams
        else:
            from galbot_sdk.g1 import Pose, Waypoint, WaypointParams

        waypoints = []
        for spot in spots:
            p = spot["pose"]
            waypoints.append(Waypoint(Pose(p), WaypointParams()))

        if not self._galbot_nav.is_localized() and spots:
            self._galbot_nav.relocalize(spots[0]["pose"])
            time.sleep(0.5)

        handle = self._galbot_nav.navigate_through_waypoints(
            waypoints, "map", enable_collision_check=True
        )
        if not handle.request_sent:
            with self._lock:
                self._state.navigation_status = "failed"
                self._state.message = "多航点任务提交失败"
            return

        timeout = self._cfg.navigation.goal_timeout_sec * max(len(waypoints), 1)
        t0 = time.time()
        while not self._stop_nav.is_set() and (time.time() - t0) < timeout:
            snap = self._galbot_nav.get_navigation_target_status(handle.task_id)
            status_name = str(snap.status)
            if status_name.endswith("SUCCESS"):
                with self._lock:
                    self._state.navigation_status = "arrived"
                    self._state.message = "多航点导航完成"
                return
            if any(
                status_name.endswith(x)
                for x in ("FAILED", "INTERRUPTED", "COLLISION", "OCCUPIED")
            ):
                with self._lock:
                    self._state.navigation_status = "failed"
                    self._state.message = f"多航点导航: {status_name}"
                return
            time.sleep(0.5)

        with self._lock:
            self._state.navigation_status = "failed"
            self._state.message = "多航点导航超时"

    def navigate_to_spot(self, spot_id: str) -> dict[str, Any]:
        spot = self.get_spot(spot_id)
        if not spot:
            return {"ok": False, "message": f"未知航点: {spot_id}"}

        if self._nav_thread and self._nav_thread.is_alive():
            return {"ok": False, "message": "已有导航任务进行中"}

        def _run() -> None:
            with self._lock:
                self._state.navigation_status = "navigating"
                self._state.target_spot_id = spot_id
                self._state.message = f"正在前往 {spot.get('name', spot_id)}"
            try:
                if self.is_mock:
                    self._navigate_mock(spot)
                else:
                    self._navigate_galbot(spot)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._state.navigation_status = "failed"
                    self._state.message = str(exc)

        self._stop_nav.clear()
        self._nav_thread = threading.Thread(target=_run, daemon=True)
        self._nav_thread.start()
        return {"ok": True, "message": "导航已启动", "spot_id": spot_id}

    async def pose_stream(self, on_pose: Callable[[dict[str, Any]], Any], hz: float) -> None:
        interval = 1.0 / max(hz, 0.5)
        while True:
            snap = self.status_snapshot()
            await on_pose(snap)
            await asyncio.sleep(interval)

    def shutdown(self) -> None:
        self.stop_patrol()
        self.stop_navigation()
        if self._galbot_robot:
            try:
                self._galbot_robot.request_shutdown()
                self._galbot_robot.wait_for_shutdown()
                self._galbot_robot.destroy()
            except Exception:  # noqa: BLE001
                pass
