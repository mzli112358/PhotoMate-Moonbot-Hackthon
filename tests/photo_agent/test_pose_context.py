from __future__ import annotations

import pytest

from app.photo_agent.dispatcher import FunctionCallDispatcher
from app.photo_agent.fsm import PhotoAgentFSM
from app.photo_agent.mocks import MockCamera, MockDelivery, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import PoseContext, PoseGoal, QualityResult, State, ToolCall


def build_dispatcher() -> tuple[FunctionCallDispatcher, PhotoAgentFSM]:
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=MockOmni(),
        camera=MockCamera(captures=[]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=MockDelivery(results=[]),
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.pose_context = PoseContext()
    return FunctionCallDispatcher(fsm), fsm


@pytest.mark.asyncio
async def test_pose_context_create_keep_replace_and_complete() -> None:
    dispatcher, fsm = build_dispatcher()

    created = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "双手在胸前比心",
                "success_criteria": "双手可见;形成明显心形",
                "progress": "not_started",
                "visual_observation": "用户自然站立",
                "guidance_intent": "邀请用户一起比心",
                "completion_reason": "none",
            },
            "pose-1",
        )
    )
    first_goal_id = created["active_goal_id"]

    kept = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "partial",
                "visual_observation": "双手已经抬起",
                "guidance_intent": "鼓励用户把双手靠近",
            },
            "pose-2",
        )
    )
    replaced = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "replace",
                "active_goal": {
                    "description": "举起右手比耶",
                    "success_criteria": ["右手可见", "食指和中指张开"],
                },
                "progress": "not_started",
                "visual_observation": "用户表示想换动作",
                "user_feedback_summary": "用户不想比心",
                "replace_reason": "用户明确要求更换",
                "guidance_intent": "邀请用户举手比耶",
            },
            "pose-3",
        )
    )
    completed = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "complete",
                "progress": "achieved",
                "visual_observation": "右手已经完成比耶",
                "guidance_intent": "确认姿势完成并请用户保持",
                "completion_reason": "visual_goal_achieved",
            },
            "pose-4",
        )
    )

    assert created["ok"] is True
    assert kept["active_goal_id"] == first_goal_id
    assert replaced["active_goal_id"] != first_goal_id
    assert fsm.context.pose_context.goal_history[0].status == "replaced"
    assert completed["complete"] is True
    assert fsm.context.pose_context.active_goal.status == "completed"
    assert fsm.context.state is State.POSE_GUIDANCE


@pytest.mark.asyncio
async def test_pose_context_rejects_invalid_transition_and_duplicate_call() -> None:
    dispatcher, fsm = build_dispatcher()
    keep_without_goal = ToolCall(
        "report_pose_turn",
        {
            "goal_action": "keep",
            "progress": "partial",
            "visual_observation": "没有活动目标",
            "guidance_intent": "继续",
        },
        "same-call",
    )

    rejected = await dispatcher.dispatch(keep_without_goal)
    repeated = await dispatcher.dispatch(keep_without_goal)

    assert rejected == {"ok": False, "error": "pose_goal_missing"}
    assert repeated == {"ok": False, "error": "pose_goal_missing"}
    assert fsm.context.pose_context.revision == 0


def test_pose_context_snapshot_is_compact_json_for_next_turn() -> None:
    context = PoseContext()
    context.last_spoken_text = "我们一起比个心吧"

    snapshot = context.snapshot_for_prompt()

    assert context.episode_id in snapshot
    assert "我们一起比个心吧" in snapshot
    assert "processed_call_ids" not in snapshot


@pytest.mark.asyncio
async def test_pose_context_normalizes_keep_with_achieved_to_complete() -> None:
    dispatcher, fsm = build_dispatcher()
    await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "站在窗户前，双手自然放在胸前",
                "success_criteria": "身体正对窗户;双手在胸前",
                "progress": "not_started",
                "visual_observation": "用户尚未摆好",
                "guidance_intent": "请站到窗户前",
                "completion_reason": "none",
            },
            "pose-create",
        )
    )

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "achieved",
                "visual_observation": "用户已完全符合目标动作要求",
                "guidance_intent": "太棒了，保持住别动",
                "completion_reason": "visual_goal_achieved",
            },
            "pose-achieved-keep",
        )
    )

    assert result["ok"] is True
    assert result["complete"] is True
    assert fsm.context.pose_context.progress == "achieved"
    assert fsm.context.pose_context.active_goal.status == "completed"
    assert fsm.context.pose_context.completion_reason == "visual_goal_achieved"


@pytest.mark.asyncio
async def test_pose_context_rejects_guidance_intent_none() -> None:
    dispatcher, fsm = build_dispatcher()

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "保持自然微笑",
                "success_criteria": "面向镜头;表情自然",
                "progress": "not_started",
                "visual_observation": "用户正对镜头",
                "guidance_intent": "none",
                "completion_reason": "none",
            },
            "pose-none",
        )
    )

    assert result == {"ok": False, "error": "missing_guidance_intent"}
    assert fsm.context.pose_context.active_goal is None


@pytest.mark.asyncio
async def test_pose_context_allows_user_requested_capture_without_active_goal() -> None:
    dispatcher, fsm = build_dispatcher()

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "complete",
                "progress": "achieved",
                "visual_observation": "用户明确要求直接拍照",
                "guidance_intent": "好的，保持一下，我马上拍照。",
                "completion_reason": "user_requested_capture",
            },
            "pose-direct-capture",
        )
    )

    assert result["ok"] is True
    assert result["complete"] is True
    assert fsm.context.pose_context.active_goal is None
    assert fsm.context.pose_context.completion_reason == "user_requested_capture"


@pytest.mark.asyncio
async def test_pose_context_create_derives_goal_from_guidance_intent() -> None:
    """goal_description is schema-optional; a create that omits it must still
    succeed (deriving the goal from guidance_intent) so S3 never goes mute."""
    dispatcher, fsm = build_dispatcher()

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "progress": "not_started",
                "visual_observation": "用户站在花墙前",
                "guidance_intent": "把水瓶举到胸前比个耶",
                "completion_reason": "none",
            },
            "pose-no-description",
        )
    )

    assert result["ok"] is True
    goal = fsm.context.pose_context.active_goal
    assert goal is not None
    assert goal.description == "把水瓶举到胸前比个耶"


@pytest.mark.asyncio
async def test_pose_context_normalizes_keep_partial_when_guidance_counts_down() -> None:
    """Reproduce live bug: model says 马上开拍 but fields stay keep/partial."""
    dispatcher, fsm = build_dispatcher()
    await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "双手比心",
                "success_criteria": "双手可见;形成心形",
                "progress": "not_started",
                "visual_observation": "用户自然站立",
                "guidance_intent": "我们一起比个心吧",
                "completion_reason": "none",
            },
            "pose-setup",
        )
    )

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "partial",
                "visual_observation": "用户双手比出一个完整的心形手势，位置适中，手指清晰可见，表情自然微笑。",
                "guidance_intent": "太棒了！这个爱心手势完美到位，保持住别动，咱们马上开拍啦！",
                "completion_reason": "none",
            },
            "pose-ready-speech",
        )
    )

    assert result["ok"] is True
    assert result["complete"] is True
    assert fsm.context.pose_context.progress == "achieved"
    assert fsm.context.pose_context.completion_reason == "visual_goal_achieved"


@pytest.mark.asyncio
async def test_pose_context_does_not_complete_when_guidance_still_adjusts() -> None:
    dispatcher, fsm = build_dispatcher()
    await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "双手比心",
                "success_criteria": "双手可见;形成心形",
                "progress": "not_started",
                "visual_observation": "用户自然站立",
                "guidance_intent": "我们一起比个心吧",
                "completion_reason": "none",
            },
            "pose-setup-2",
        )
    )

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "partial",
                "visual_observation": "用户双手比心，但手部位置稍高，靠近脸部，且手指细节不够清晰。",
                "guidance_intent": "手再往下放一点点，让爱心更完整就完美啦。",
                "completion_reason": "none",
            },
            "pose-still-adjusting",
        )
    )

    assert result["ok"] is True
    assert result["complete"] is False
    assert fsm.context.pose_context.progress == "partial"


@pytest.mark.asyncio
async def test_pose_context_completes_from_visual_only_when_clearly_achieved() -> None:
    dispatcher, fsm = build_dispatcher()
    await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "create",
                "goal_description": "双手比心",
                "success_criteria": "双手可见;形成心形",
                "progress": "not_started",
                "visual_observation": "用户自然站立",
                "guidance_intent": "我们一起比个心吧",
                "completion_reason": "none",
            },
            "pose-setup-3",
        )
    )

    result = await dispatcher.dispatch(
        ToolCall(
            "report_pose_turn",
            {
                "goal_action": "keep",
                "progress": "partial",
                "visual_observation": "用户双手比出完整心形，位置适中，手指清晰可见，表情自然微笑。",
                "guidance_intent": "太棒了，这个角度特别好看，保持这个姿势！",
                "completion_reason": "none",
            },
            "pose-visual-ready",
        )
    )

    assert result["ok"] is True
    assert result["complete"] is True
