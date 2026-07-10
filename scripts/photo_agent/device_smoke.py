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
    print(json.dumps({"audio_devices": list_audio_devices()}, ensure_ascii=False, indent=2))
    camera = None
    microphone = None
    speaker = None
    try:
        camera = OpenCVCamera(args.camera, Path("data/smoke-photos"))
        open_camera = getattr(camera, "open", None)
        if open_camera:
            open_camera()
        microphone = PyAudioMicrophone(args.microphone)
        speaker = PyAudioSpeaker(args.speaker)
        frame = await camera.get_frame()
        pcm = await asyncio.to_thread(microphone.read_chunk)
        await asyncio.to_thread(speaker, b"\x00\x00" * 1200)
        print(
            json.dumps(
                {
                    "camera_ok": True,
                    "camera_name": camera.device_name,
                    "frame_shape": list(frame.shape),
                    "microphone_ok": len(pcm) > 0,
                    "speaker_ok": True,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - device smoke boundary
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 3
    finally:
        if microphone is not None:
            microphone.close()
        if speaker is not None:
            speaker.close()
        if camera is not None:
            await camera.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Camera/microphone/speaker independent smoke test")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--microphone", type=int, default=None)
    parser.add_argument("--speaker", type=int, default=None)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
