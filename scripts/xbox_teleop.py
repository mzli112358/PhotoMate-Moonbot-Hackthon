#!/usr/bin/env python3
"""Xbox 手柄 → Galbot 底盘遥控（无 ROS）。

在 Orin/Jetson 上运行，需先 source GalbotSDK setup.sh。
默认映射（Xbox Wireless Controller）：
  左摇杆 Y → 前后 (vx)
  左摇杆 X → 横移 (vy)
  右摇杆 X → 转向 (vyaw)
"""
from __future__ import annotations

import argparse
import fcntl
import glob
import os
import select
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

# Linux joystick ioctl: get axis count
JSIOCGAXES = 0x80006A11


def _default_robot_model() -> str:
    try:
        from app.config import load_app_yaml

        return load_app_yaml().robot.model
    except Exception:
        return "g1"


def find_gamepad_device() -> str | None:
    """从 /proc/bus/input/devices 查找 Xbox/手柄，优先 js*。"""
    proc = Path("/proc/bus/input/devices")
    if not proc.exists():
        return None

    candidates: list[tuple[int, str, str]] = []
    keywords = ("xbox", "045e:")
    for block in proc.read_text(encoding="utf-8", errors="ignore").split("\n\n"):
        lower = block.lower()
        if not any(k in lower for k in keywords):
            continue
        name = next((ln[3:].strip() for ln in block.splitlines() if ln.startswith("N: Name=")), "gamepad")
        handlers = next((ln.split("=", 1)[1].split() for ln in block.splitlines() if ln.startswith("H: Handlers=")), [])
        for handler in handlers:
            if handler.startswith("js"):
                candidates.append((0, f"/dev/input/{handler}", name))
            elif handler.startswith("event"):
                candidates.append((1, f"/dev/input/{handler}", name))

    if not candidates:
        js_nodes = sorted(glob.glob("/dev/input/js*"))
        if js_nodes:
            return js_nodes[0]
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def resolve_gamepad_device(requested: str | None) -> tuple[str | None, str]:
    if requested and requested != "auto":
        return requested, "manual"
    found = find_gamepad_device()
    return found, "auto"


def apply_deadzone(value: float, deadzone: float) -> float:
    return 0.0 if abs(value) < deadzone else value


class JoystickReader:
    def __init__(self, path: str) -> None:
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.axes: dict[int, float] = {}
        try:
            buf = bytearray(4)
            fcntl.ioctl(self.fd, JSIOCGAXES, buf)
            axis_count = struct.unpack("i", buf)[0]
            for i in range(axis_count):
                self.axes[i] = 0.0
        except OSError:
            pass

    def poll(self) -> None:
        while True:
            ready, _, _ = select.select([self.fd], [], [], 0)
            if not ready:
                break
            try:
                data = os.read(self.fd, 8)
            except BlockingIOError:
                break
            if len(data) < 8:
                break
            _time_ms, value, ev_type, number = struct.unpack("IhBB", data)
            if (ev_type & JS_EVENT_AXIS) or (ev_type & JS_EVENT_INIT and number < 32):
                self.axes[number] = max(-1.0, min(1.0, value / 32767.0))

    def get_axis(self, index: int) -> float:
        return self.axes.get(index, 0.0)

    def close(self) -> None:
        os.close(self.fd)


def _chassis_controller(model: str, mode: str) -> str:
    """按机型/模式选择底盘控制器（G1 与 S1 常量名不同）。"""
    model = model.lower()
    if model == "s1":
        from galbot_sdk.s1 import S1ControllerName

        names = S1ControllerName
        if mode == "nav":
            return names.SWERVE_CHASSIS_POSE_CTRL
        return getattr(names, "SWERVE_CHASSIS_TWIST_CTRL", names.SWERVE_CHASSIS_POSE_CTRL)

    from galbot_sdk.g1 import G1ControllerName

    names = G1ControllerName
    if mode == "nav":
        return names.CHASSIS_POSE_CTRL
    return names.CHASSIS_TWIST_CTRL


def init_galbot(model: str, mode: str):
    model = model.lower()
    if model == "s1":
        from galbot_sdk.s1 import ControlStatus, GalbotNavigation, GalbotRobot
    else:
        from galbot_sdk.g1 import ControlStatus, GalbotNavigation, GalbotRobot

    ctrl = _chassis_controller(model, mode)

    robot = GalbotRobot()
    nav = GalbotNavigation()
    if not robot.init():
        raise RuntimeError("GalbotRobot.init() failed")
    if mode == "nav" and not nav.init():
        raise RuntimeError("GalbotNavigation.init() failed")

    if robot.switch_controller(ctrl) != ControlStatus.SUCCESS:
        raise RuntimeError(f"switch_controller({ctrl}) failed")

    return robot, nav


def stop_motion(robot, nav, mode: str) -> None:
    if mode == "nav" and nav is not None:
        nav.stop_navigation()
    robot.set_base_velocity([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0.15)


def main() -> int:
    parser = argparse.ArgumentParser(description="Xbox 手柄遥控 Galbot 底盘")
    parser.add_argument(
        "--device",
        default="auto",
        help="手柄设备路径；默认 auto 自动查找 Xbox/js*",
    )
    parser.add_argument("--model", default=_default_robot_model(), choices=["g1", "s1"])
    parser.add_argument(
        "--mode",
        default="direct",
        choices=["direct", "nav"],
        help="direct=set_base_velocity；nav=navigate_with_velocity（带避障）",
    )
    parser.add_argument("--max-vx", type=float, default=0.5, help="摇杆满推时最大前后速度 m/s")
    parser.add_argument("--max-vy", type=float, default=0.3, help="摇杆满推时最大横移速度 m/s")
    parser.add_argument("--max-yaw", type=float, default=1.0, help="摇杆满推时最大角速度 rad/s")
    parser.add_argument("--deadzone", type=float, default=0.08)
    parser.add_argument("--rate-hz", type=float, default=30.0)
    parser.add_argument(
        "--cmd-duration",
        type=float,
        default=-1.0,
        help="速度指令持续秒数；direct 默认 0=持续；nav 默认 0.15",
    )
    parser.add_argument("--axis-vx", type=int, default=1, help="前后轴号")
    parser.add_argument("--axis-vy", type=int, default=0, help="横移轴号")
    parser.add_argument("--axis-yaw", type=int, default=3, help="转向轴号")
    # G1 + Xbox 蓝牙默认轴方向与底盘坐标相反；个别轴仍反了可加 --no-invert-*
    parser.add_argument("--no-invert-vx", action="store_true", help="不反转前后轴")
    parser.add_argument("--no-invert-vy", action="store_true", help="不反转横移轴")
    parser.add_argument("--no-invert-yaw", action="store_true", help="不反转转向轴")
    parser.add_argument(
        "--safe",
        action="store_true",
        help="保守速度：max-vx=0.15 max-yaw=0.3",
    )
    args = parser.parse_args()

    if args.safe:
        args.max_vx = 0.15
        args.max_vy = 0.1
        args.max_yaw = 0.3

    cmd_duration = args.cmd_duration
    if cmd_duration < 0:
        cmd_duration = 0.0 if args.mode == "direct" else 0.15

    device, device_source = resolve_gamepad_device(args.device)
    if not device or not os.path.exists(device):
        print("未找到手柄设备。", file=sys.stderr)
        print("请在 Orin 上把 Xbox 手柄通过蓝牙/USB 连到 galbot-echo，然后检查：", file=sys.stderr)
        print("  ls /dev/input/js*", file=sys.stderr)
        print("  cat /proc/bus/input/devices | grep -A6 -i xbox", file=sys.stderr)
        if args.device not in (None, "auto"):
            print(f"指定路径不存在: {args.device}", file=sys.stderr)
        return 1

    joy = JoystickReader(device)
    robot = None
    nav = None

    try:
        robot, nav = init_galbot(args.model, args.mode)
        print(
            f"Galbot {args.model.upper()} 已连接 | 手柄: {device} ({device_source}) | 模式: {args.mode}"
        )
        print(
            f"速度上限 vx={args.max_vx} vy={args.max_vy} vyaw={args.max_yaw} | "
            f"发送 {args.rate_hz:.0f}Hz | cmd_duration={cmd_duration}s"
        )
        print("左摇杆移动，右摇杆转向。Ctrl+C 停车退出。")

        interval = 1.0 / max(args.rate_hz, 1.0)
        while True:
            joy.poll()
            sign_vx = 1.0 if args.no_invert_vx else -1.0
            sign_vy = 1.0 if args.no_invert_vy else -1.0
            sign_yaw = 1.0 if args.no_invert_yaw else -1.0

            vx = sign_vx * apply_deadzone(joy.get_axis(args.axis_vx), args.deadzone) * args.max_vx
            vy = sign_vy * apply_deadzone(joy.get_axis(args.axis_vy), args.deadzone) * args.max_vy
            vyaw = sign_yaw * apply_deadzone(joy.get_axis(args.axis_yaw), args.deadzone) * args.max_yaw

            if args.mode == "nav":
                nav.navigate_with_velocity(vx, vy, vyaw, cmd_duration, True)
            else:
                robot.set_base_velocity([vx, vy, 0.0], [0.0, 0.0, vyaw], cmd_duration)

            if any(abs(v) > 0.01 for v in (vx, vy, vyaw)):
                print(f"\rvx={vx:+.2f} vy={vy:+.2f} vyaw={vyaw:+.2f}", end="", flush=True)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n停车…")
    finally:
        if robot is not None:
            stop_motion(robot, nav, args.mode)
            robot.request_shutdown()
            robot.wait_for_shutdown()
            robot.destroy()
        joy.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
