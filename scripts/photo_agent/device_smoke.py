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

from app.photo_agent.audio import PyAudioMicrophone, PyAudioSpeaker, list_audio_devices  # noqa: E402
from app.photo_agent.camera import OpenCVCamera  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    report = {
        "audio_devices": list_audio_devices(),
        "camera": {"ok": False, "device": args.camera},
        "microphone": {"ok": False, "device": args.microphone if args.microphone is not None else "default"},
        "speaker": {"ok": False, "device": args.speaker if args.speaker is not None else "default"},
    }
    camera = OpenCVCamera(args.camera, Path("data/smoke-photos"))
    try:
        open_camera = getattr(camera, "open", None)
        if open_camera:
            open_camera()
        frame = await camera.get_frame()
        report["camera"] = {"ok": True, "device": camera.device_name, "frame_shape": list(frame.shape)}
    except Exception as exc:  # noqa: BLE001 - device smoke boundary
        report["camera"]["error"] = str(exc)
    finally:
        await camera.close()

    microphone = None
    try:
        microphone = PyAudioMicrophone(args.microphone)
        pcm = await asyncio.to_thread(microphone.read_chunk)
        report["microphone"]["device"] = getattr(microphone, "device_name", report["microphone"]["device"])
        report["microphone"]["ok"] = len(pcm) > 0
        report["microphone"]["bytes"] = len(pcm)
    except Exception as exc:  # noqa: BLE001
        report["microphone"]["error"] = str(exc)
    finally:
        if microphone is not None:
            microphone.close()

    speaker = None
    try:
        speaker = PyAudioSpeaker(args.speaker)
        await asyncio.to_thread(speaker, b"\x00\x00" * 1200)
        report["speaker"]["device"] = getattr(speaker, "device_name", report["speaker"]["device"])
        report["speaker"]["ok"] = True
    except Exception as exc:  # noqa: BLE001
        report["speaker"]["error"] = str(exc)
    finally:
        if speaker is not None:
            speaker.close()

    report["ok"] = all(report[name]["ok"] for name in ("camera", "microphone", "speaker"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Camera/microphone/speaker independent smoke test")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--microphone", type=int, default=None)
    parser.add_argument("--speaker", type=int, default=None)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
