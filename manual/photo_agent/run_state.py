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
from app.photo_agent.runtime import build_local_runtime, build_self_check, run_mock_state  # noqa: E402


INSTRUCTIONS = {
    "S1": "面向摄像头停留约三秒；短暂停留或侧身不应唤醒。",
    "S2": "分别回答‘要’、‘不用’和保持沉默。",
    "S3": "保持安静观察约五秒一次引导，再说‘可以拍了’打断。",
    "S4": "分别正常睁眼、故意闭眼、快速移动，观察保存与质检回环。",
    "S5": "分别回答‘满意’和‘不满意’，确认 S6/S3 分流。",
    "S6": "打开输出 photo_url，确认照片正确且会话复位。",
}


async def run(args: argparse.Namespace) -> int:
    config = load_runtime_config(mode=args.mode)
    print(json.dumps(build_self_check(config), ensure_ascii=False, indent=2))
    print(f"当前验收状态={args.state}；用户动作：{INSTRUCTIONS[args.state]}")
    if args.mode == "mock":
        result = await run_mock_state(config, args.state)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 2
    print("local-real 将启动完整真实链路；请只执行上面的目标状态动作，其余步骤正常完成。Ctrl+C 结束。")
    runtime = build_local_runtime(config)
    await runtime.run_forever()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="S1-S6 manual acceptance entry")
    parser.add_argument("--state", choices=tuple(INSTRUCTIONS), required=True)
    parser.add_argument("--mode", choices=("mock", "local-real"), default="mock")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
