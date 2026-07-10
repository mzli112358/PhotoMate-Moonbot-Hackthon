"""Persistent, versioned prompt registry for Photo Agent testing and runtime."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from string import Formatter
from typing import Any, Protocol

import yaml


DEFAULT_PROMPTS: dict[str, str] = {
    "system.base": (
        "你是热情、幽默、会逗人开心的活动摄影师。每轮只说一两句简短中文。"
        "你负责自然对话、粗粒度姿态引导和工具调用；状态、计时、重试由本地编排层负责。"
        "当当前响应指令明确要求调用工具时，必须调用指定工具，不能用口头回答代替。"
        "未经用户同意不保存到云端，不要声称控制了未接入的机器人或 Insta360 能力。"
    ),
    "state.S2": "当前进入询问拍照意愿环节。主动询问用户是否需要拍照。",
    "state.S3": "当前进入拍照引导环节。每轮只给一句简短、亲切的姿态建议。",
    "state.S4": "当前进入拍照环节。先完成三二一倒数，再执行拍照。",
    "state.S5": "当前进入照片复核环节。询问用户是否满意。",
    "state.S6": "当前进入照片交付环节。告知用户照片链接已准备好。",
    "action.S2.ask_initial": "嗨～需要我帮你拍张照吗？只说这一句。",
    "action.S2.ask_retry": "再轻声询问一次用户是否需要拍照。只说一句。",
    "action.S2.decline": "友好回应用户：没问题，需要时再叫我。只说一句。",
    "action.S3.guidance": "观察当前画面，只给一句简短姿态引导；构图不错就让用户保持住。",
    "action.S3.guidance_limit": "引导已达上限，请问用户：那我先帮你拍一张？只说一句。",
    "action.S4.countdown": "请说：看镜头，三、二、一，茄子！说完后保持安静。",
    "action.S4.capture_failed": "刚才快门没有成功，抱歉，我们再试一次。只说一句。",
    "action.S4.quality_failed": "照片质检未通过：{quality_reason}，请简短提示重拍。",
    "action.S5.show_failed": "屏幕暂时无法展示照片，我会继续保留取图链接。只说一句。",
    "action.S5.ask_review": "请问用户：这张怎么样，满意吗？只说一句。",
    "action.S6.delivered": "照片链接已准备好，祝用户玩得开心。只说一句。",
    "action.S6.delivery_failed": (
        "照片链接暂时生成失败，请记住取图码 {photo_id}，工作人员可协助取图。只说一句。"
    ),
    "action.tool.followup": "根据工具执行结果，用一句简短中文继续回复用户。",
    "action.session.end_context": "会话结束原因：{reason}",
}


PROMPT_DEFINITIONS: tuple[dict[str, str], ...] = tuple(
    {
        "key": key,
        "kind": key.split(".", 1)[0],
        "state": next((part for part in key.split(".") if part in {f"S{i}" for i in range(1, 7)}), "global"),
        "title": key.rsplit(".", 1)[-1].replace("_", " "),
    }
    for key in DEFAULT_PROMPTS
)


class PromptError(RuntimeError):
    pass


class PromptConflictError(PromptError):
    pass


class PromptValidationError(PromptError):
    pass


@dataclass(frozen=True)
class PromptSnapshot:
    version: str
    updated_at: str
    prompts: dict[str, str]


class PromptSource(Protocol):
    @property
    def version(self) -> str: ...

    def get(self, key: str) -> str: ...

    def render(self, key: str, **values: Any) -> str: ...


class StaticPromptSource:
    def __init__(self, prompts: dict[str, str] | None = None) -> None:
        self._prompts = dict(prompts or DEFAULT_PROMPTS)
        self.version = _new_version(self._prompts)

    def get(self, key: str) -> str:
        return self._prompts[key]

    def render(self, key: str, **values: Any) -> str:
        return self._prompts[key].format(**values)


def _new_version(prompts: dict[str, str], nonce: int | None = None) -> str:
    payload = json.dumps(prompts, ensure_ascii=False, sort_keys=True)
    if nonce is not None:
        payload = f"{payload}:{nonce}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _default_snapshot() -> PromptSnapshot:
    return PromptSnapshot(
        version=_new_version(DEFAULT_PROMPTS),
        updated_at="1970-01-01T00:00:00+00:00",
        prompts=dict(DEFAULT_PROMPTS),
    )


class PromptRegistry:
    def __init__(self, config_path: Path, history_dir: Path, *, max_history: int = 20) -> None:
        self.config_path = config_path
        self.history_dir = history_dir
        self.max_history = max_history
        self._snapshot = self._read(self.config_path) if self.config_path.is_file() else _default_snapshot()

    @property
    def version(self) -> str:
        return self._snapshot.version

    def snapshot(self) -> PromptSnapshot:
        return PromptSnapshot(
            self._snapshot.version,
            self._snapshot.updated_at,
            dict(self._snapshot.prompts),
        )

    def get(self, key: str) -> str:
        try:
            return self._snapshot.prompts[key]
        except KeyError as exc:
            raise PromptValidationError(f"unknown prompt: {key}") from exc

    def render(self, key: str, **values: Any) -> str:
        template = self.get(key)
        required = {name for _, name, _, _ in Formatter().parse(template) if name}
        missing = required - values.keys()
        if missing:
            raise PromptValidationError(
                f"missing template value for {key}: {', '.join(sorted(missing))}"
            )
        return template.format(**values)

    def save(self, updates: dict[str, str], *, expected_version: str) -> PromptSnapshot:
        if expected_version != self._snapshot.version:
            raise PromptConflictError(
                f"prompt version changed: expected {expected_version}, current {self._snapshot.version}"
            )
        self._validate(updates)
        merged = {**self._snapshot.prompts, **{key: value.strip() for key, value in updates.items()}}
        if merged == self._snapshot.prompts:
            return self.snapshot()
        self._archive(self._snapshot)
        now = datetime.now(UTC).isoformat()
        snapshot = PromptSnapshot(
            version=_new_version(merged, time.time_ns()),
            updated_at=now,
            prompts=merged,
        )
        self._write(self.config_path, snapshot)
        self._snapshot = snapshot
        self._prune_history()
        return self.snapshot()

    def history(self) -> list[PromptSnapshot]:
        archived = [self._read(path) for path in self.history_dir.glob("*.yaml")]
        archived.sort(key=lambda item: item.updated_at, reverse=True)
        return [self.snapshot(), *archived]

    def rollback(self, version: str, *, expected_version: str) -> PromptSnapshot:
        target = self._find(version)
        return self.save(target.prompts, expected_version=expected_version)

    def diff(self, before_version: str, after_version: str) -> dict[str, dict[str, str]]:
        before = self._find(before_version)
        after = self._find(after_version)
        return {
            key: {"before": before.prompts[key], "after": after.prompts[key]}
            for key in DEFAULT_PROMPTS
            if before.prompts[key] != after.prompts[key]
        }

    def _find(self, version: str) -> PromptSnapshot:
        if version == self._snapshot.version:
            return self.snapshot()
        for item in self.history():
            if item.version == version:
                return item
        raise PromptValidationError(f"unknown prompt version: {version}")

    def _validate(self, updates: dict[str, str]) -> None:
        unknown = set(updates) - DEFAULT_PROMPTS.keys()
        if unknown:
            raise PromptValidationError(f"unknown prompt: {', '.join(sorted(unknown))}")
        empty = [key for key, value in updates.items() if not isinstance(value, str) or not value.strip()]
        if empty:
            raise PromptValidationError(f"prompt cannot be empty: {', '.join(sorted(empty))}")

    def _archive(self, snapshot: PromptSnapshot) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._write(self.history_dir / f"{time.time_ns()}-{snapshot.version}.yaml", snapshot)

    def _prune_history(self) -> None:
        paths = sorted(self.history_dir.glob("*.yaml"), key=lambda path: path.stat().st_mtime_ns)
        for path in paths[: max(0, len(paths) - self.max_history)]:
            path.unlink()

    @staticmethod
    def _read(path: Path) -> PromptSnapshot:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        prompts = {**DEFAULT_PROMPTS, **(raw.get("prompts") or {})}
        return PromptSnapshot(
            version=str(raw.get("version") or _new_version(prompts)),
            updated_at=str(raw.get("updated_at") or "1970-01-01T00:00:00+00:00"),
            prompts=prompts,
        )

    @staticmethod
    def _write(path: Path, snapshot: PromptSnapshot) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": snapshot.version,
            "updated_at": snapshot.updated_at,
            "prompts": snapshot.prompts,
        }
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
