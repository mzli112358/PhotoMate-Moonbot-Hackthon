from __future__ import annotations

import pytest

from app.photo_agent.fsm import FSMConfig, PhotoAgentFSM
from app.photo_agent.mocks import MockCamera, MockDelivery, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import DeliveryResult, QualityResult, State, WakeSignal
from app.photo_agent.omni import DashscopeOmniClient, OmniSettings
from app.photo_agent.prompts import DEFAULT_PROMPTS
from app.photo_agent.runtime import PhotoAgentRuntime


class MutablePrompts:
    def __init__(self, **overrides: str) -> None:
        self.values = {**DEFAULT_PROMPTS, **overrides}
        self.version = "prompt-v1"

    def get(self, key: str) -> str:
        return self.values[key]

    def render(self, key: str, **values) -> str:
        return self.values[key].format(**values)


def make_fsm(prompts: MutablePrompts, omni: MockOmni | None = None) -> tuple[PhotoAgentFSM, MockOmni]:
    omni = omni or MockOmni()
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([WakeSignal(True, 3.1, True)]),
        omni=omni,
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[DeliveryResult("p", "http://local/p", True)]),
        config=FSMConfig(wake_consecutive_frames=1),
        prompts=prompts,
    )
    return fsm, omni


@pytest.mark.asyncio
async def test_fsm_reads_state_and_action_prompts_from_registry() -> None:
    prompts = MutablePrompts(
        **{
            "state.S2": "CUSTOM S2 CONTEXT",
            "action.S2.ask_initial": "CUSTOM INITIAL QUESTION",
            "action.S2.ask_retry": "CUSTOM RETRY QUESTION",
        }
    )
    fsm, omni = make_fsm(prompts)

    await fsm.start()
    await fsm.poll_wake()
    await fsm.handle_timeout()

    assert ("inject_context", "CUSTOM S2 CONTEXT") in omni.calls
    assert (
        "create_response",
        {"instructions": "CUSTOM INITIAL QUESTION", "output_audio": True},
    ) in omni.calls
    assert (
        "create_response",
        {"instructions": "CUSTOM RETRY QUESTION", "output_audio": True},
    ) in omni.calls


class FakeConversation:
    def __init__(self, **kwargs) -> None:
        self.callback = kwargs["callback"]
        self.calls: list[tuple[str, object]] = []
        self.session_id = "session-prompts"

    def connect(self) -> None:
        self.callback.on_event({"type": "session.created", "session": {"id": self.session_id}})

    def update_session(self, **kwargs) -> None:
        self.calls.append(("update_session", kwargs))

    def create_item(self, item) -> None:
        self.calls.append(("create_item", item))

    def create_response(self, instructions=None, output_modalities=None) -> None:
        self.calls.append(
            (
                "create_response",
                {"instructions": instructions, "output_modalities": output_modalities},
            )
        )

    def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_omni_reads_system_and_tool_prompts_from_registry() -> None:
    prompts = MutablePrompts(
        **{
            "system.base": "CUSTOM SYSTEM",
            "action.tool.followup": "CUSTOM TOOL FOLLOWUP",
            "action.session.end_context": "CUSTOM END {reason}",
        }
    )
    made: list[FakeConversation] = []

    def factory(**kwargs):
        made.append(FakeConversation(**kwargs))
        return made[-1]

    client = DashscopeOmniClient(
        OmniSettings("key", "workspace.example.com"),
        conversation_factory=factory,
        prompt_source=prompts,
    )
    await client.connect()

    await client.configure()
    await client.submit_tool_result("call-1", {"ok": True})
    await client.end_session("timeout")

    update = next(value for name, value in made[0].calls if name == "update_session")
    assert update["instructions"] == "CUSTOM SYSTEM"
    followup = next(value for name, value in made[0].calls if name == "create_response")
    assert followup["instructions"] == "CUSTOM TOOL FOLLOWUP"
    end_item = [value for name, value in made[0].calls if name == "create_item"][-1]
    assert end_item["content"][0]["text"] == "CUSTOM END timeout"


@pytest.mark.asyncio
async def test_runtime_applies_saved_system_prompt_at_next_idle_turn() -> None:
    prompts = MutablePrompts(**{"system.base": "SYSTEM V1"})
    fsm, omni = make_fsm(prompts)
    fsm.context.state = State.ASK_INTENT
    fsm.context.session_id = "session-1"
    runtime = PhotoAgentRuntime(fsm, prompt_source=prompts)

    prompts.values["system.base"] = "SYSTEM V2"
    prompts.version = "prompt-v2"
    await runtime.sync_prompt_version()

    assert ("update_instructions", "SYSTEM V2") in omni.calls
    assert runtime.active_prompt_version == "prompt-v2"


@pytest.mark.asyncio
async def test_runtime_defers_hot_switch_while_response_is_in_flight() -> None:
    prompts = MutablePrompts()
    fsm, omni = make_fsm(prompts)
    fsm.context.session_id = "session-1"
    fsm.context.response_in_flight = True
    runtime = PhotoAgentRuntime(fsm, prompt_source=prompts)
    prompts.version = "prompt-v2"

    await runtime.sync_prompt_version()

    assert omni.count("update_instructions") == 0
    assert runtime.active_prompt_version == "prompt-v1"


def test_s3_prompts_manage_pose_goals_without_composition_guidance() -> None:
    combined = " ".join(
        DEFAULT_PROMPTS[key]
        for key in ("state.S3", "action.S3.assess", "action.S3.speak")
    )

    assert "report_pose_turn" in combined
    assert "场景" in combined
    assert "guidance_intent" in combined
    assert "progress=achieved" in combined
    assert "goal_action必须=complete" in combined
    assert "禁止keep" in combined
    assert "report_pose_readiness" in combined
    assert "禁止直接调用 capture_photo" in combined
    # De-dup now relies on rolling history windows, not just the last line.
    assert "recent_spoken" in combined
    assert "recent_intents" in combined
    # Users may drive their own pose/scene or request an immediate capture.
    assert "goal_action=replace" in combined
    assert "帮我拍照" in combined
    assert "我开拍啦" in combined
    assert "capture_after_speech" in combined
    assert "不要改变" in combined
    assert "往中间站" not in combined
    assert "调整取景" not in combined
