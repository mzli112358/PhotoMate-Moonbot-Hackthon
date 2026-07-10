from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import urlparse

from app.photo_agent.config import load_runtime_config
from app.photo_agent.runtime import build_local_runtime, build_self_check, run_mock_demo


async def _run_local(config, *, serve_photos: bool) -> None:
    runtime = build_local_runtime(config)
    server = None
    server_task = None
    if serve_photos:
        import uvicorn

        from app.main import app

        parsed = urlparse(config.base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8000
        server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info"))
        server_task = asyncio.create_task(server.serve(), name="photo-api")
    try:
        await runtime.run_forever()
    finally:
        if server is not None:
            server.should_exit = True
        if server_task is not None:
            await server_task


async def async_main(args: argparse.Namespace) -> int:
    config = load_runtime_config(mode=args.mode)
    print(json.dumps(build_self_check(config), ensure_ascii=False, indent=2))
    if config.mode == "mock":
        result = await run_mock_demo(config)
        print(json.dumps({"ok": result.ok, "photo_id": result.photo_id, "photo_url": result.photo_url}, ensure_ascii=False))
        return 0 if result.ok else 2
    if config.mode == "hardware-real":
        print("hardware-real 仅保留接口；当前未接入 Jetson、Insta360 或 GalbotSDK。")
        return 3
    await _run_local(config, serve_photos=not args.no_photo_server)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhotoMate S1-S6 photo agent")
    parser.add_argument("--mode", choices=("mock", "local-real", "hardware-real"), default="mock")
    parser.add_argument("--no-photo-server", action="store_true")
    return parser.parse_args()


def main() -> int:
    return asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
