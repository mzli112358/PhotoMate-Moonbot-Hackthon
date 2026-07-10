#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.photo_agent.config import load_runtime_config  # noqa: E402
from app.photo_agent.audio import PyAudioMicrophone  # noqa: E402
from app.photo_agent.omni import DashscopeOmniClient, OmniSettings  # noqa: E402


async def wait_until(client: DashscopeOmniClient, wanted: set[str], timeout: float = 20.0) -> list[dict]:
    events: list[dict] = []
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        event = await client.next_event(timeout=max(0.1, deadline - asyncio.get_running_loop().time()))
        events.append(event)
        if event.get("type") in wanted:
            return events
    raise TimeoutError(f"Omni smoke timed out waiting for {wanted}")


async def detect_timeout(client: DashscopeOmniClient, timeout: float = 0.05) -> bool:
    try:
        await wait_until(client, {"intentionally_absent_event"}, timeout=timeout)
    except TimeoutError:
        return True
    return False


async def capture_microphone_chunks(
    device_index: int | None,
    *,
    count: int = 3,
    microphone_factory=PyAudioMicrophone,
) -> list[bytes]:
    microphone = microphone_factory(device_index)
    try:
        return [await asyncio.to_thread(microphone.read_chunk) for _ in range(count)]
    finally:
        microphone.close()


async def run(args: argparse.Namespace) -> int:
    config = load_runtime_config(mode="local-real")
    if not config.api_key:
        print(json.dumps({"ok": False, "blocked": "DASHSCOPE_API_KEY missing"}, ensure_ascii=False))
        return 2
    audio_chunks: list[bytes] = []
    client = DashscopeOmniClient(
        OmniSettings(
            api_key=config.api_key,
            workspace_host=config.workspace_host,
            model=config.model,
            voice=config.voice,
        ),
        audio_sink=audio_chunks.append,
    )
    report = {
        "key_present": True,
        "session": False,
        "microphone_audio": False,
        "input_audio_bytes": 0,
        "audio_before_image": False,
        "text_output": False,
        "audio_output": False,
        "vad_plus_manual_response": False,
        "function_call": False,
        "tool_followup": False,
        "error_or_timeout_detectable": False,
    }
    try:
        session_id = await client.connect()
        report["session"] = bool(session_id)
        await client.configure()
        if args.synthetic_audio:
            input_chunks = [b"\x00\x00" * 1600 for _ in range(3)]
        else:
            input_chunks = await capture_microphone_chunks(args.microphone)
        for chunk in input_chunks:
            await client.append_audio(chunk)
        report["microphone_audio"] = not args.synthetic_audio and bool(input_chunks)
        report["input_audio_bytes"] = sum(len(chunk) for chunk in input_chunks)
        report["audio_before_image"] = True
        frame = np.full((480, 640, 3), 180, dtype=np.uint8)
        await client.append_image(frame)
        await client.commit_input()
        await client.create_response("用一句中文说：Omni 实时链路正常。不要调用工具。")
        events = await wait_until(client, {"response_done", "error"})
        report["text_output"] = any(event.get("type") == "assistant_text" for event in events)
        report["audio_output"] = bool(audio_chunks)
        report["vad_plus_manual_response"] = any(event.get("type") == "response_done" for event in events)
        if any(event.get("type") == "error" for event in events):
            raise RuntimeError(str(events[-1]))

        await client.create_response(
            "这是协议 smoke test。必须调用 end_session 工具，参数 reason=timeout；不要直接回答。"
        )
        tool_events = await wait_until(client, {"tool_call", "error"})
        tool_event = next((event for event in tool_events if event.get("type") == "tool_call"), None)
        if tool_event is None:
            raise RuntimeError(f"function call not returned: {tool_events}")
        report["function_call"] = True
        call = tool_event["tool_call"]
        await client.submit_tool_result(call.call_id, {"ok": True})
        followup = await wait_until(client, {"response_done", "error"})
        report["tool_followup"] = any(event.get("type") == "response_done" for event in followup)
        report["error_or_timeout_detectable"] = await detect_timeout(client)
        report["ok"] = all(value for key, value in report.items() if key != "ok")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 3
    except Exception as exc:  # noqa: BLE001 - smoke-test boundary
        report["ok"] = False
        report["error"] = str(exc)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3
    finally:
        await client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Qwen Omni independent realtime smoke test")
    parser.add_argument("--microphone", type=int, default=None)
    parser.add_argument(
        "--synthetic-audio",
        action="store_true",
        help="Only for protocol debugging; real acceptance must use the microphone.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
