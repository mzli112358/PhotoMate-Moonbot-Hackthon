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
        "直接理解用户原始音频，不依赖或等待语音转写。"
        "当当前响应指令明确要求调用工具时，必须调用指定工具，不能用口头回答代替。"
        "未经用户同意不保存到云端，不要声称控制了未接入的机器人或 Insta360 能力。"
    ),
    "state.S2": (
        "当前进入询问拍照意愿环节。主动询问用户是否需要拍照；"
        "用户明确接受或拒绝后调用 report_photo_intent。"
    ),
    "state.S3": (
        "当前进入拍照姿态引导环节。结合画面中的场景元素（如背景招牌、装饰、道具）构思简单、安全、可验证的静态动作目标。"
        "首轮用语音向用户完整介绍「场景+动作+为什么好看」；后续每轮在判断是否达标的同时，"
        "用语音提供情绪价值（可描述穿着、表情、动作并真诚夸奖）。"
        "每轮话术必须新鲜多样：对照 PoseContext 中的 last_spoken_text、last_guidance_intent，"
        "禁止重复相同句子、相同夸奖点或同义改写。"
        "用户明确说直接拍照、现在拍、可以拍了时，必须调用 report_pose_readiness(decision=ready)，"
        "禁止直接调用 capture_photo；capture_photo 仅在系统明确发出 action.S3.capture 指令时调用。"
        "姿态达标由内部评估通过 report_pose_turn(goal_action=complete) 上报；"
        "一旦画面已满足 success_criteria，必须立即 complete，不要多等一轮 interval。"
        "上报 complete 时 guidance_intent 可以是拍照倒数语（如「动作很好，我开拍啦！」）；"
        "本地编排层也会根据倒数语或视觉达标信号自动推进 complete。"
        "不要指导相机取景、构图或站位居中。"
    ),
    "state.S5": (
        "当前进入照片复核环节。询问用户是否满意；"
        "用户明确满意或要求重拍后调用 report_review_intent。"
    ),
    "state.S6": "当前进入照片交付环节。告知用户照片链接已准备好。",
    "action.S2.ask_initial": "嗨～需要我帮你拍张照吗？只说这一句。",
    "action.S2.ask_retry": "再轻声询问一次用户是否需要拍照。只说一句。",
    "action.S2.decline": "友好回应用户：没问题，需要时再叫我。只说一句。",
    "action.S3.guidance": "观察当前画面并持续当前姿态目标。",
    "action.S3.assess": (
        "这是S3内部评估回合，当前阶段={guidance_phase}，PoseContext(JSON)：{pose_context}\n"
        "以本轮提交的画面为唯一事实。必须且只能调用一次report_pose_turn，不要输出面向用户的自然语言。\n"
        "写guidance_intent前，先读PoseContext里的last_spoken_text与last_guidance_intent；"
        "每轮必须换说法、换夸奖角度（穿着/表情/道具/场景细节/动作微调），禁止重复或同义改写。\n"
        "当guidance_phase=intro（尚无活动目标）：goal_action=create；观察背景/场景，构思「场景锚点+静态动作」目标；"
        "goal_description写目标动作；success_criteria写可观察完成条件（分号分隔）；"
        "guidance_intent写你下一轮要对用户说的完整中文（含场景、动作、为什么生动），禁止填none。\n"
        "当guidance_phase=coach（已有活动目标）：先判断progress再选goal_action，二者必须一致，禁止矛盾组合。"
        "progress=not_started→goal_action=keep；progress=partial→goal_action=keep（或用户要求换动作用replace）；"
        "progress=achieved→goal_action必须=complete，禁止keep或replace。"
        "画面已满足success_criteria时，必须同时填goal_action=complete、progress=achieved、completion_reason=visual_goal_achieved，不要继续keep。"
        "用户明确说可以拍/拍吧时，用goal_action=complete、progress=achieved、completion_reason=user_requested_capture。"
        "goal_action=complete时，guidance_intent写拍照倒数语（如「动作很好，我开拍啦！」「完美到位，保持别动，咱们马上开拍啦！」）。"
        "goal_action≠complete时，guidance_intent写下一轮微调引导；若画面已明显达标，应直接complete而不是继续keep。"
        "completion_reason仅在goal_action=complete时填写规定枚举，否则填none。"
        "硬性禁止：progress=achieved时goal_action=keep；completion_reason=visual_goal_achieved时goal_action≠complete。\n"
        "guidance_intent必须是即将播报的中文要点，禁止填none或留空。"
    ),
    "action.S3.speak": (
        "这是S3面向用户的播报回合。PoseContext(JSON)：{pose_context}\n"
        "拍照倒计时={capture_after_speech}。本轮要点：{guidance_intent}。上一轮实际说过：{last_spoken_text}。\n"
        "当capture_after_speech=true：这是快门前最后一句话，必须热情清晰说出「动作很好，我开拍啦！」"
        "（可微调节奏或加「保持别动」，语义不变）；禁止调用工具；禁止再布置新动作；说完系统会自动快门。\n"
        "当capture_after_speech=false：用自然热情中文说出要点，可略扩展语气，但必须至少一句、不能沉默。"
        "对照PoseContext禁止与last_spoken_text、last_guidance_intent重复或同义改写；每轮至少换一个夸奖或引导角度。"
        "禁止调用任何工具，必须输出语音。不要改变已保存的动作目标，不要讨论站位、取景或构图。"
    ),
    "action.S3.speak_retry": (
        "这是S3语音重试回合。你必须用语音说出下面这句话，禁止调用任何工具，禁止沉默：\n"
        "{guidance_intent}"
    ),
    "action.S3.capture": (
        "姿态已达标。必须且只能调用一次 capture_photo(mode=photo) 触发相机快门，"
        "不要输出面向用户的自然语言。"
    ),
    "action.S3.captured": "这是S3拍照完成播报。只说：我拍好啦。只说一句，热情自然。",
    "action.S3.capture_failed": "刚才快门没有成功，抱歉，我们再试一次。只说一句。",
    "action.S3.quality_failed": "照片质检未通过：{quality_reason}，请简短提示重拍。",
    "action.S3.guidance_limit": "引导已达上限，请问用户：那我先帮你拍一张？只说一句。",
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
