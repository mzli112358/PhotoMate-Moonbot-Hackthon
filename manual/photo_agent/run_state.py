#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.photo_agent.config import load_runtime_config  # noqa: E402
from app.photo_agent.observability import configure_json_logging  # noqa: E402
from app.photo_agent.runtime import build_local_runtime, build_self_check, run_mock_state  # noqa: E402
from app.photo_agent.server import PhotoApiServer  # noqa: E402


INSTRUCTIONS = {
    "S1": "面向摄像头停留约三秒；短暂停留或侧身不应唤醒。",
    "S2": "分别回答‘要’、‘不用’和保持沉默。",
    "S3": "保持安静观察引导；达标或说‘可以拍了’后应 capture_photo 并听到「我拍好啦」。",
    "S5": "分别回答‘满意’和‘不满意’，确认 S6/S3 分流。",
    "S6": "打开输出 photo_url，确认照片正确且会话复位。",
}

EXPECTED = {
    "S1": "满足停留与朝向条件后只建一次会话并进入 S2；不满足时保持 S1。",
    "S2": "回答要进入 S3；回答不用或两次沉默超时回到 S0。",
    "S3": "约十秒一次评估引导；达标或用户确认后在 S3 内拍照并播报「我拍好啦」，然后进入 S5。",
    "S5": "显示本次照片；满意进 S6，不满意回 S3，且沿用同一会话。",
    "S6": "生成可访问 photo_url，结束会话并复位到 S0。",
}


async def run(args: argparse.Namespace) -> int:
    config = load_runtime_config(mode=args.mode)
    if args.mode == "mock":
        print(json.dumps(build_self_check(config), ensure_ascii=False, indent=2))
        print(f"当前验收状态={args.state}；用户动作：{INSTRUCTIONS[args.state]}")
        print(f"正常预期现象：{EXPECTED[args.state]}")
        result = await run_mock_state(config, args.state)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 2
    try:
        runtime = build_local_runtime(config)
    except Exception as exc:  # noqa: BLE001 - manual preflight boundary
        report = build_self_check(config, missing_real_dependencies=[str(exc)])
        report["preflight_error"] = str(exc)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"当前验收状态={args.state}；用户动作：{INSTRUCTIONS[args.state]}")
        print(f"正常预期现象：{EXPECTED[args.state]}")
        return 4
    print(json.dumps(build_self_check(config, device_info=runtime.device_info), ensure_ascii=False, indent=2))
    print(f"当前验收状态={args.state}；用户动作：{INSTRUCTIONS[args.state]}")
    print(f"正常预期现象：{EXPECTED[args.state]}")
    server = PhotoApiServer(config.base_url) if args.state in {"S5", "S6"} else None
    if server is not None:
        await server.start()
    try:
        result = await runtime.run_manual_state(args.state)
    finally:
        if server is not None:
            await server.stop()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 3


def main() -> int:
    configure_json_logging()
    parser = argparse.ArgumentParser(description="S1-S6 manual acceptance entry (S4 removed; capture in S3)")
    parser.add_argument("--state", choices=tuple(INSTRUCTIONS), required=True)
    parser.add_argument("--mode", choices=("mock", "local-real"), default="mock")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
