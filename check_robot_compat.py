#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SDK_VERSION = "1.7.3"
REQUIRED_ROBOT_VERSION = "GBS_1.15"
DEFAULT_CFG_PATH = "/data/config/system.cfg"

EXIT_MATCH = 0
EXIT_MISMATCH = 1
EXIT_ERROR = 2


def parse_args():
    parser = argparse.ArgumentParser(
        description="检查机器人版本与 SDK 依赖版本兼容性（默认优先通过 SDK 连接读取）。"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--guide", action="store_true", help="输出详细升级建议")
    parser.add_argument(
        "--source",
        choices=["auto", "sdk", "local_cfg", "ssh_cfg"],
        default="auto",
        help="版本来源：auto(默认)、sdk、local_cfg、ssh_cfg",
    )
    parser.add_argument("--system-cfg", default=DEFAULT_CFG_PATH, help="system.cfg 路径")
    parser.add_argument("--host", help="远程主机（仅 ssh_cfg 使用）")
    parser.add_argument("--user", help="远程用户名（仅 ssh_cfg 使用）")
    parser.add_argument("--port", type=int, default=22, help="SSH 端口（仅 ssh_cfg 使用）")
    parser.add_argument(
        "--robot-version",
        help="手工指定机器人版本（用于离线验证，优先级最高）",
    )
    return parser.parse_args()


def normalize_version(ver):
    m = re.search(r"(\d+(?:\.\d+)*)", ver or "")
    if not m:
        raise ValueError(f"无法解析版本号: {ver}")
    return [int(x) for x in m.group(1).split(".")]


def version_ge(lhs, rhs):
    l_parts = normalize_version(lhs)
    r_parts = normalize_version(rhs)
    length = max(len(l_parts), len(r_parts))
    l_parts.extend([0] * (length - len(l_parts)))
    r_parts.extend([0] * (length - len(r_parts)))
    return l_parts >= r_parts


def get_robot_version_from_sdk():
    robot = None
    last_error = None
    for module in ("galbot_sdk.g1", "galbot_sdk.s1"):
        try:
            mod = __import__(module, fromlist=["GalbotRobot"])
            robot_cls = getattr(mod, "GalbotRobot")
            robot = robot_cls()
            robot.init()
            time.sleep(1)
            device_info = robot.get_device_information() or {}
            fw = str(device_info.get("firmware_version", "")).strip()
            if not fw:
                raise RuntimeError("SDK 已连接但 firmware_version 为空")
            return fw, "sdk:get_device_information.firmware_version"
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
        finally:
            if robot is not None:
                try:
                    robot.request_shutdown()
                    robot.wait_for_shutdown()
                    robot.destroy()
                except Exception:
                    pass
            robot = None
    raise RuntimeError(f"无法通过 SDK 获取机器人版本: {last_error}")


def get_robot_version_from_local_cfg(cfg_path):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    cur = str(cfg.get("CUR_VERSION", "")).strip()
    if not cur:
        raise RuntimeError("system.cfg 中缺少 CUR_VERSION")
    return cur, f"local_cfg:{cfg_path}"


def get_robot_version_from_ssh_cfg(host, user, port, cfg_path):
    if not host or not user:
        raise ValueError("ssh_cfg 模式必须提供 --host 和 --user")
    cmd = ["ssh", "-p", str(port), f"{user}@{host}", f"cat '{cfg_path}'"]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ssh 执行失败")
    cfg = json.loads(proc.stdout)
    cur = str(cfg.get("CUR_VERSION", "")).strip()
    if not cur:
        raise RuntimeError("远程 system.cfg 中缺少 CUR_VERSION")
    return cur, f"ssh_cfg:{user}@{host}:{port}{cfg_path}"


def resolve_robot_version(args):
    if args.robot_version:
        return args.robot_version.strip(), "manual:--robot-version"

    if args.source == "sdk":
        return get_robot_version_from_sdk()
    if args.source == "local_cfg":
        return get_robot_version_from_local_cfg(args.system_cfg)
    if args.source == "ssh_cfg":
        return get_robot_version_from_ssh_cfg(args.host, args.user, args.port, args.system_cfg)

    # auto: 优先 SDK，其次 local_cfg，最后 ssh_cfg
    errors = []
    for getter in (
        lambda: get_robot_version_from_sdk(),
        lambda: get_robot_version_from_local_cfg(args.system_cfg),
        lambda: get_robot_version_from_ssh_cfg(args.host, args.user, args.port, args.system_cfg),
    ):
        try:
            return getter()
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(str(exc))
    raise RuntimeError(" ; ".join(errors))


def guide_text(match, cur_version, show_detail):
    if match:
        return "版本兼容（机器人系统版本 >= SDK 依赖版本），可直接使用当前组合。"
    if not show_detail:
        return "版本不匹配：请升级机器人系统或切换匹配的 SDK。"
    return (
        f"版本不匹配：机器人当前为 {cur_version}，SDK 期望 {REQUIRED_ROBOT_VERSION}。"
        f"建议路径：A) 升级机器人系统到 {REQUIRED_ROBOT_VERSION}；"
        f"B) 切换到与 {cur_version} 匹配的 SDK 版本。"
    )


def main():
    args = parse_args()
    try:
        cur_version, source = resolve_robot_version(args)
        match = version_ge(cur_version, REQUIRED_ROBOT_VERSION)
        status = "MATCH" if match else "MISMATCH"
        payload = {
            "sdk_version": SDK_VERSION,
            "required_robot_system_version": REQUIRED_ROBOT_VERSION,
            "robot_system_version": cur_version,
            "version_source": source,
            "status": status,
            "match": match,
            "guide": guide_text(match, cur_version, args.guide),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("=== Galbot SDK 兼容性检查 ===")
            print(f"SDK 版本: {payload['sdk_version']}")
            print(f"SDK 依赖机器人系统版本(GBS_VERSION): {payload['required_robot_system_version']}")
            print(f"机器人当前系统版本: {payload['robot_system_version']}")
            print(f"版本来源: {payload['version_source']}")
            print(f"检查结果: {payload['status']}")
            print(f"升级指引: {payload['guide']}")
        sys.exit(EXIT_MATCH if match else EXIT_MISMATCH)
    except Exception as exc:  # pylint: disable=broad-except
        err = {
            "status": "ERROR",
            "error": str(exc),
            "hint": "请检查 SDK 连通性、system.cfg 路径或 SSH 参数。",
        }
        if args.json:
            print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"ERROR: {err['error']}", file=sys.stderr)
            print(f"HINT: {err['hint']}", file=sys.stderr)
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
