from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from app.config import CONFIG_DIR, ROOT_DIR
from app.photo_agent.runtime import RuntimeConfig


def _int_or_none(value: Any) -> int | None:
    if value in (None, "", "default"):
        return None
    return int(value)


def load_runtime_config(
    *,
    mode: str | None = None,
    config_file: Path | None = None,
    root_dir: Path | None = None,
) -> RuntimeConfig:
    root = (root_dir or ROOT_DIR).resolve()
    path = config_file or CONFIG_DIR / "app.yaml"
    raw: dict[str, Any] = {}
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = raw.get("photo_agent") or {}

    def env(name: str, default: Any = None) -> Any:
        return os.getenv(name, default)

    photo_dir = Path(env("PHOTOMATE_PHOTO_AGENT__PHOTO_DIR", cfg.get("photo_dir", "data/photos")))
    if not photo_dir.is_absolute():
        photo_dir = root / photo_dir
    return RuntimeConfig(
        mode=mode or env("PHOTOMATE_PHOTO_AGENT__MODE", cfg.get("mode", "mock")),
        model=env("OMNI_MODEL", cfg.get("model", "qwen3.5-omni-flash-2026-03-15")),
        workspace_host=env(
            "DASHSCOPE_WORKSPACE_HOST",
            cfg.get("workspace_host", "llm-iscpge3ysktzaaf2.cn-beijing.maas.aliyuncs.com"),
        ),
        api_key=env("DASHSCOPE_API_KEY", ""),
        voice=env("OMNI_VOICE", cfg.get("voice", "Tina")),
        camera_index=int(env("PHOTOMATE_PHOTO_AGENT__CAMERA_INDEX", cfg.get("camera_index", 0))),
        microphone_index=_int_or_none(
            env("PHOTOMATE_PHOTO_AGENT__MICROPHONE_INDEX", cfg.get("microphone_index"))
        ),
        speaker_index=_int_or_none(
            env("PHOTOMATE_PHOTO_AGENT__SPEAKER_INDEX", cfg.get("speaker_index"))
        ),
        photo_dir=photo_dir,
        base_url=env("PHOTOMATE_PHOTO_AGENT__BASE_URL", cfg.get("base_url", "http://127.0.0.1:8000")),
        guidance_interval_s=float(
            env("PHOTOMATE_PHOTO_AGENT__GUIDANCE_INTERVAL_S", cfg.get("guidance_interval_s", 5.0))
        ),
    )
