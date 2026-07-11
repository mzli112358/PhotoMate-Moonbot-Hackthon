from __future__ import annotations

import argparse
import asyncio
import json

from app.photo_agent.config import load_runtime_config
from app.photo_agent.observability import configure_json_logging
from app.photo_agent.runtime import build_local_runtime, build_self_check, run_mock_demo
from app.photo_agent.server import PhotoApiServer


async def _run_local(config, runtime, *, serve_photos: bool) -> None:
    server = PhotoApiServer(config.base_url) if serve_photos else None
    if serve_photos:
        assert server is not None
        await server.start()
    try:
        await runtime.run_forever()
    finally:
        if server is not None:
            await server.stop()


async def async_main(args: argparse.Namespace) -> int:
    configure_json_logging()
    config = load_runtime_config(mode=args.mode)
    if config.mode == "mock":
        print(json.dumps(build_self_check(config), ensure_ascii=False, indent=2))
        result = await run_mock_demo(config)
        print(json.dumps({"ok": result.ok, "photo_id": result.photo_id, "photo_url": result.photo_url}, ensure_ascii=False))
        return 0 if result.ok else 2
    if config.mode == "hardware-real":
        print(json.dumps(build_self_check(config), ensure_ascii=False, indent=2))
        print("hardware-real 仅保留接口；当前未接入 Jetson、Insta360 或 GalbotSDK。")
        return 3
    try:
        runtime = build_local_runtime(config)
    except Exception as exc:  # noqa: BLE001 - startup preflight boundary
        report = build_self_check(config, missing_real_dependencies=[str(exc)])
        report["preflight_error"] = str(exc)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4
    print(json.dumps(build_self_check(config, device_info=runtime.device_info), ensure_ascii=False, indent=2))
    await _run_local(config, runtime, serve_photos=not args.no_photo_server)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhotoMate S1-S6 photo agent")
    parser.add_argument("--mode", choices=("mock", "local-real", "hardware-real"), default="mock")
    parser.add_argument("--no-photo-server", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        return asyncio.run(async_main(parse_args()))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
