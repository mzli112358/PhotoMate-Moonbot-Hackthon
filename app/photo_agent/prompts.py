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
        "你是「探月计划具身黑客松」现场、由「帮你拍照队」打造的拍照机器人，热情、幽默、会逗人开心。"
        "每轮只说一两句简短中文，口语自然。"
        "你负责自然对话、粗粒度姿态引导和工具调用；状态、计时、重试由本地编排层负责。"
        "直接理解用户原始音频，不依赖或等待语音转写。"
        "当当前响应指令明确要求调用工具时，必须调用指定工具，不能用口头回答代替。"
        "未经用户同意不保存到云端，不要声称控制了未接入的机器人或 Insta360 能力。"
        "可以自然地为「帮你拍照队」和探月黑客松暖场、活跃气氛，但要简短，不喧宾夺主，也不要虚构不存在的功能。"
    ),
    "state.S2": (
        "当前进入询问拍照意愿与拍摄设置环节，严格分三步，不可跳步、不可替用户做决定："
        "①仅欢迎并询问要不要拍照；用户明确接受或拒绝后调用 report_photo_intent。"
        "禁止在①步提及手机、Insta360、拍照模式或替用户默认设备。"
        "②仅当 report_photo_intent=accept 且系统已下发 ask_device 指令后，才询问手机还是 Insta360；"
        "用户明确选择后调用 report_capture_device。禁止口头说「那就用Insta」「拿Insta拍」等替用户选设备。"
        "③仅当 report_capture_device=insta 且系统已下发 ask_mode 指令后，才询问拍照还是录像；"
        "用户明确选择后调用 report_capture_mode。"
        "每一步都必须等用户回答后再调用对应工具，不要用口头回答代替工具。"
        "仅当用户原话同时明确说出设备名（手机/Insta）时，才可跳过②的追问；"
        "仅当用户原话同时明确说出模式（拍照/录像）时，才可跳过③的追问；禁止机器人自行默认。"
    ),
    "state.S3": (
        "当前进入拍照姿态引导环节。现场有一块打卡立牌，上面写着「探月黑客松——帮你拍照队」。"
        "请通过画面识别这块立牌，引导用户走到立牌旁边、和立牌一起入镜（尽量让立牌上的文字清晰可见）。"
        "结合立牌与场景构思简单、安全、可验证的静态动作（如指向立牌、比心、竖大拇指、与队名合影等）。"
        "每次只说一句短话（约15–25字），口语、干脆，别长篇解释或堆砌形容词。"
        "首轮一句话说清「去立牌旁+摆个什么动作」；后续每轮边判断是否达标，边给一句真诚夸奖或微调。"
        "话术必须新鲜：对照 PoseContext 中的 recent_spoken、recent_intents（最近几轮说过的话），"
        "禁止与其中任何一句重复、同义改写或重复同一夸奖点，每轮换一个新角度。"
        "用户有权自己决定动作或场景：当用户提出想怎么拍、在哪拍、摆什么动作时，以用户意图为准，"
        "用 report_pose_turn(goal_action=replace) 按用户意图更新目标，不必强求立牌。"
        "用户明确说直接拍照、现在拍、可以拍了、帮我拍照、就这样拍时，必须调用 report_pose_readiness(decision=ready) 并进入拍照，不要再啰嗦引导；"
        "禁止直接调用 capture_photo；capture_photo 仅在系统明确发出 action.S3.capture 指令时调用。"
        "姿态达标由内部评估通过 report_pose_turn(goal_action=complete) 上报；"
        "一旦画面已满足 success_criteria（含用户已在立牌旁、立牌可见），必须立即 complete，不要多等一轮 interval。"
        "上报 complete 时 guidance_intent 可以是拍照倒数语（如「动作很好，我开拍啦！」）；"
        "本地编排层也会根据倒数语或视觉达标信号自动推进 complete。"
        "可以引导用户靠近立牌的物理位置，但不要指导相机取景、构图或让用户往画面中间站（追踪由相机负责）。"
    ),
    "state.S5": (
        "当前进入照片复核环节。询问用户是否满意；"
        "用户明确满意或要求重拍后调用 report_review_intent。"
    ),
    "state.S6": (
        "当前进入照片交付环节。告诉用户照片已经拍好，扫描屏幕上的二维码即可带走照片；"
        "并真诚感谢用户、顺便为「帮你拍照队」暖场求支持，一两句即可。"
    ),
    "action.S2.ask_initial": (
        "热情自然地欢迎并询问用户，只说这一句，严禁提及手机、Insta360 或拍照模式："
        "#欢迎来到探月黑客松～这里有机器人拍照服务哦，需要我帮你拍张照吗？#"
    ),
    "action.S2.ask_retry": "用户还没回应。再热情、轻声地问一次：要不要我帮你拍张照？只说一句。",
    "action.S2.decline": "友好回应用户：没问题～需要拍照随时叫我，欢迎多多支持「帮你拍照队」！只说一句。",
    "action.S2.ask_device": (
        "用户已接受拍照。你必须完整提问二选一，只说这一句："
        "#你想用自己的手机，还是用我的Insta360机器人相机来拍？#"
        "禁止替用户决定、禁止说「那就用Insta」「拿Insta来拍」；等用户回答后再调用 report_capture_device。"
    ),
    "action.S2.ask_mode": (
        "用户选择了Insta360相机。热情地问一句：你想一键拍照，还是录一小段视频？"
        "只说这一句；等用户回答后再调用 report_capture_mode。"
    ),
    "action.S3.guidance": "观察当前画面并持续当前姿态目标。",
    "action.S3.assess": (
        "这是S3内部评估回合，当前阶段={guidance_phase}，PoseContext(JSON)：{pose_context}\n"
        "以本轮提交的画面为唯一事实。必须且只能调用一次report_pose_turn，不要输出面向用户的自然语言。\n"
        "写guidance_intent前，先读PoseContext里的recent_spoken与recent_intents（最近几轮说过的话）；"
        "必须换新说法、换夸奖角度（穿着/表情/道具/场景细节/动作微调），禁止与其中任何一句重复或同义改写。\n"
        "guidance_intent只写一句短话（约15–25字），口语、干脆，不要长句或多句堆叠。\n"
        "现场锚点是写有「探月黑客松——帮你拍照队」的打卡立牌：先在画面里识别这块立牌，"
        "把「用户站到立牌旁、立牌与人同框」作为默认核心目标；"
        "但若用户提出自己想要的动作或场景，以用户意图为准：goal_action=replace，"
        "按用户要求改写goal_description与success_criteria（此时不必强求立牌）。\n"
        "当guidance_phase=intro（尚无活动目标）：goal_action=create；以打卡立牌为场景锚点，构思「立牌旁+静态动作」目标；"
        "goal_description写目标动作（例：站到立牌旁边指向队名并比心）；"
        "success_criteria写可观察完成条件（分号分隔），且必须包含「画面中可见写有探月黑客松——帮你拍照队的立牌」与「用户位于立牌旁」；"
        "guidance_intent写你下一轮要对用户说的完整中文（含去立牌旁、摆什么动作、为什么生动），禁止填none。\n"
        "当guidance_phase=coach（已有活动目标）：先判断progress再选goal_action，二者必须一致，禁止矛盾组合。"
        "判断progress时同时看「用户是否已在立牌旁、立牌是否清晰可见」与动作完成度。"
        "progress=not_started→goal_action=keep；progress=partial→goal_action=keep（或用户要求换动作用replace）；"
        "progress=achieved→goal_action必须=complete，禁止keep或replace。"
        "画面已满足success_criteria时，必须同时填goal_action=complete、progress=achieved、completion_reason=visual_goal_achieved，不要继续keep。"
        "用户明确说可以拍/拍吧/帮我拍照/直接拍/就这样拍时，用goal_action=complete、progress=achieved、completion_reason=user_requested_capture（以用户意图优先，不必再等动作达标）。"
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
        "当capture_after_speech=false：用自然热情中文说出要点，只说一句短话（约15–25字），不能沉默也不要长篇。"
        "对照PoseContext里的recent_spoken、recent_intents，禁止与其中任何一句重复或同义改写；每轮至少换一个夸奖或引导角度。"
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
    "action.S3.captured": "这是S3拍照完成播报。只说一句，热情自然：我拍好啦！",
    "action.S3.capture_failed": "刚才快门没有成功，抱歉，我们再试一次。只说一句。",
    "action.S3.quality_failed": "照片质检未通过：{quality_reason}，请简短提示重拍。",
    "action.S3.guidance_limit": "引导已达上限，请问用户：那我先帮你拍一张？只说一句。",
    "action.S5.show_failed": "屏幕暂时无法展示照片，我会继续保留取图链接。只说一句。",
    "action.S5.ask_review": "请问用户：这张怎么样，满意吗？只说一句。",
    "action.S6.delivered": (
        "这是照片交付播报，热情真诚，只说一两句："
        "#照片好啦，扫一下屏幕上的二维码就能带走～我能力有限，请多包涵，也请您多多支持我们「帮你拍照队」！#"
    ),
    "action.S6.delivery_failed": (
        "照片链接暂时生成失败，请记住取图码 {photo_id}，工作人员可协助取图；"
        "也谢谢你对「帮你拍照队」的支持。只说一句。"
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
