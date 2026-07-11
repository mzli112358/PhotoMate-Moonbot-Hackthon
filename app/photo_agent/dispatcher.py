from __future__ import annotations

import logging
from typing import Any

from app.photo_agent.fsm import PhotoAgentFSM
from app.photo_agent.models import PoseContext, PoseGoal, State, ToolCall

LOGGER = logging.getLogger("photomate.photo_agent.dispatcher")


class FunctionCallDispatcher:
    """Validates Omni tool calls and executes deterministic local actions."""

    # name -> (expected_state, argument_key, allowed_values, required_s2_phase|None)
    INTENT_TOOLS = {
        "report_photo_intent": (State.ASK_INTENT, "decision", {"accept", "deny"}, "ask_intent"),
        "report_capture_device": (State.ASK_INTENT, "device", {"phone", "insta"}, "ask_device"),
        "report_capture_mode": (State.ASK_INTENT, "mode", {"photo", "video"}, "ask_mode"),
        "report_pose_readiness": (State.POSE_GUIDANCE, "decision", {"ready"}, None),
        "report_review_intent": (State.REVIEW, "decision", {"accept", "retake"}, None),
    }

    def __init__(self, fsm: PhotoAgentFSM) -> None:
        self.fsm = fsm

    def is_intent_call(self, call: ToolCall) -> bool:
        return call.name in self.INTENT_TOOLS

    def validate_intent(self, call: ToolCall) -> dict[str, Any]:
        contract = self.INTENT_TOOLS.get(call.name)
        if contract is None:
            return {"ok": False, "error": f"unsupported_intent_tool:{call.name}"}
        expected_state, arg_key, allowed, required_phase = contract
        if self.fsm.context.state is not expected_state:
            return {"ok": False, "error": f"invalid_state:{self.fsm.context.state.value}"}
        if required_phase is not None and self.fsm.context.s2_phase != required_phase:
            return {"ok": False, "error": f"invalid_phase:{self.fsm.context.s2_phase}"}
        value = call.arguments.get(arg_key)
        if value not in allowed:
            return {"ok": False, "error": f"invalid_{arg_key}:{value}"}
        return {"ok": True, arg_key: value}

    async def apply_intent(self, call: ToolCall) -> None:
        arg_key = self.INTENT_TOOLS[call.name][1]
        value = str(call.arguments[arg_key])
        if call.name == "report_photo_intent":
            await self.fsm.handle_photo_intent(value)
        elif call.name == "report_capture_device":
            await self.fsm.handle_capture_device(value)
        elif call.name == "report_capture_mode":
            await self.fsm.handle_capture_mode(value)
        elif call.name == "report_pose_readiness":
            await self.fsm.handle_pose_readiness(value)
        elif call.name == "report_review_intent":
            await self.fsm.handle_review_intent(value)

    async def dispatch(self, call: ToolCall) -> dict[str, Any]:
        if self.is_intent_call(call):
            return self.validate_intent(call)
        if call.name == "report_pose_turn":
            return self._apply_pose_turn(call)
        if call.name == "capture_photo":
            if call.arguments.get("mode") != "photo":
                return {"ok": False, "error": "unsupported_capture_mode"}
            turn = self.fsm.context.pose_turn
            if self.fsm.context.state is not State.POSE_GUIDANCE:
                return {"ok": False, "error": f"invalid_state:{self.fsm.context.state.value}"}
            if turn is not None and turn.source == "user_vad" and turn.phase == "assessing":
                # Defensive normalization: the preferred user-speech tool is
                # report_pose_readiness, but older/live model sessions may still
                # call capture_photo directly. Defer it into the same safe flow.
                await self.fsm.handle_pose_readiness("ready")
                return {"ok": True, "deferred": True, "reason": "user_requested_capture"}
            if turn is None or turn.phase != "capturing":
                return {"ok": False, "error": "invalid_state:S3_not_capturing"}
            result, quality_ok = await self.fsm.run_capture_from_pose()
            return {
                "ok": result.ok,
                "photo_id": result.photo_id,
                "path": str(result.path) if result.path else "",
                "quality_ok": quality_ok,
                "error": result.error,
            }
        if call.name == "show_on_screen":
            photo_id = str(call.arguments.get("photo_id") or "")
            return {"ok": bool(photo_id) and await self.fsm.delivery.show(photo_id)}
        if call.name == "generate_download_qr":
            photo_id = str(call.arguments.get("photo_id") or "")
            result = await self.fsm.delivery.deliver(photo_id)
            return {
                "ok": result.ok,
                "photo_id": result.photo_id,
                "download_url": result.photo_url,
                "qr_url": result.photo_url,
                "error": result.error,
            }
        if call.name == "end_session":
            await self.fsm.finish_session(str(call.arguments.get("reason") or "delivered"))
            return {"ok": True}
        return {"ok": False, "error": f"unsupported_tool:{call.name}"}

    def _apply_pose_turn(self, call: ToolCall) -> dict[str, Any]:
        if self.fsm.context.state is not State.POSE_GUIDANCE:
            return {"ok": False, "error": f"invalid_state:{self.fsm.context.state.value}"}
        context = self.fsm.context.pose_context
        if context is None:
            context = PoseContext()
            self.fsm.context.pose_context = context
        if call.call_id in context.processed_call_ids:
            return {"ok": False, "error": "duplicate_call"}

        args = call.arguments
        action = str(args.get("goal_action") or "")
        progress = str(args.get("progress") or "")
        raw_intent = str(args.get("guidance_intent") or "").strip()
        completion_reason = args.get("completion_reason")
        if completion_reason == "none":
            completion_reason = None
        visual_observation = str(args.get("visual_observation") or "")
        action, progress, completion_reason, normalized = self._normalize_pose_turn(
            action,
            progress,
            completion_reason,
            raw_intent,
            visual_observation,
        )
        if normalized:
            LOGGER.info(
                "pose_turn_normalized",
                extra={
                    "call_id": call.call_id,
                    "from_goal_action": args.get("goal_action"),
                    "to_goal_action": action,
                    "progress": progress,
                    "completion_reason": completion_reason,
                },
            )
        if action not in {"create", "keep", "replace", "complete"}:
            return {"ok": False, "error": "invalid_goal_action"}
        if progress not in {"not_started", "partial", "achieved"}:
            return {"ok": False, "error": "invalid_pose_progress"}
        if not raw_intent or raw_intent.lower() == "none":
            return {"ok": False, "error": "missing_guidance_intent"}
        if action in {"keep", "replace"} and context.active_goal is None:
            return {"ok": False, "error": "pose_goal_missing"}
        if (
            action == "complete"
            and context.active_goal is None
            and completion_reason != "user_requested_capture"
        ):
            return {"ok": False, "error": "pose_goal_missing"}

        if action in {"create", "replace"}:
            goal_data = args.get("active_goal")
            if isinstance(goal_data, dict):
                description = str(goal_data.get("description") or "").strip()
                raw_criteria = goal_data.get("success_criteria", [])
            else:
                description = str(args.get("goal_description") or "").strip()
                raw_criteria = str(args.get("success_criteria") or "").split(";")
            if not description:
                # goal_description is optional in the tool schema, so the model
                # often omits it while still supplying the (required) guidance
                # intent. Derive the goal from what we do have instead of
                # rejecting the whole assessment — a rejection would leave the
                # turn with no tool result and mute S3 entirely.
                description = raw_intent or str(args.get("visual_observation") or "").strip()
            if not description:
                return {"ok": False, "error": "invalid_pose_goal"}
            if action == "create" and context.active_goal is not None:
                return {"ok": False, "error": "pose_goal_already_active"}
            if action == "replace" and context.active_goal is not None:
                context.active_goal.status = "replaced"
                context.goal_history.append(context.active_goal)
            context.active_goal = PoseGoal(
                goal_id=f"pose-{len(context.goal_history) + 1}",
                description=description,
                success_criteria=[
                    str(item).strip()
                    for item in raw_criteria
                    if str(item).strip()
                ],
            )

        if action == "complete":
            if progress != "achieved" and completion_reason != "user_requested_capture":
                return {"ok": False, "error": "pose_not_achieved"}
            if context.active_goal is None:
                if completion_reason != "user_requested_capture":
                    return {"ok": False, "error": "pose_goal_missing"}
            else:
                context.active_goal.status = "completed"
            context.completion_reason = str(completion_reason or "visual_goal_achieved")

        context.progress = progress
        context.last_visual_observation = str(args.get("visual_observation") or "")
        context.last_user_feedback_summary = str(args.get("user_feedback_summary") or "")
        context.note_intent(raw_intent)
        context.revision += 1
        context.processed_call_ids.add(call.call_id)
        return {
            "ok": True,
            "revision": context.revision,
            "active_goal_id": context.active_goal.goal_id if context.active_goal else None,
            "complete": action == "complete",
            "guidance_intent": context.last_guidance_intent,
        }

    @staticmethod
    def _normalize_pose_turn(
        action: str,
        progress: str,
        completion_reason: str | None,
        guidance_intent: str = "",
        visual_observation: str = "",
    ) -> tuple[str, str, str | None, bool]:
        """Coerce contradictory model output before deterministic local handling.

        UX goal: once the model (or vision) signals readiness, advance to complete
        immediately — do not wait for another interval round because structured
        fields lag behind natural-language guidance.
        """
        original_action = action
        original_progress = progress
        original_reason = completion_reason
        if action == "complete":
            return action, progress, completion_reason, False
        if progress == "achieved" and action == "keep":
            action = "complete"
        elif completion_reason in {"visual_goal_achieved", "user_requested_capture"}:
            action = "complete"
            if progress != "achieved":
                progress = "achieved"
        elif FunctionCallDispatcher._readiness_implies_capture(
            guidance_intent, visual_observation
        ):
            action = "complete"
            progress = "achieved"
            completion_reason = "visual_goal_achieved"
        return (
            action,
            progress,
            completion_reason,
            action != original_action
            or progress != original_progress
            or completion_reason != original_reason,
        )

    @staticmethod
    def _readiness_implies_capture(guidance_intent: str, visual_observation: str) -> bool:
        if FunctionCallDispatcher._guidance_implies_capture(guidance_intent):
            return True
        if FunctionCallDispatcher._guidance_needs_adjustment(guidance_intent):
            return False
        return FunctionCallDispatcher._visual_implies_achieved(visual_observation)

    @staticmethod
    def _guidance_implies_capture(guidance_intent: str) -> bool:
        """Speech already counts down to shutter — treat as complete even if fields lag."""
        text = "".join(guidance_intent.split())
        if not text:
            return False
        negative_markers = ("不能开拍", "不要开拍", "别开拍", "还不能", "还不拍", "暂时别拍")
        if any(marker in text for marker in negative_markers):
            return False
        capture_markers = (
            "我开拍",
            "马上开拍",
            "咱们开拍",
            "这就开拍",
            "准备开拍",
            "开始拍",
            "开拍啦",
            "开拍了",
            "准备拍照",
            "完美到位",
            "保持住别动",
            "保持别动",
        )
        return any(marker in text for marker in capture_markers)

    @staticmethod
    def _guidance_needs_adjustment(guidance_intent: str) -> bool:
        text = "".join(guidance_intent.split())
        if not text:
            return False
        adjustment_markers = (
            "再放",
            "再往下",
            "再往上",
            "再靠近",
            "再高一点",
            "再低一点",
            "稍高",
            "稍低",
            "稍微",
            "一点点",
            "还不够",
            "不够清晰",
            "再调整",
        )
        return any(marker in text for marker in adjustment_markers)

    @staticmethod
    def _visual_implies_achieved(visual_observation: str) -> bool:
        text = "".join(visual_observation.split())
        if not text:
            return False
        blocking_markers = (
            "稍",
            "不够",
            "缺少",
            "未",
            "没有",
            "偏高",
            "偏低",
            "不完整",
            "不清晰",
        )
        if any(marker in text for marker in blocking_markers):
            return False
        positive_markers = (
            "完整",
            "清晰可见",
            "位置适中",
            "完美",
            "达标",
            "自然微笑",
            "符合",
        )
        return sum(1 for marker in positive_markers if marker in text) >= 2
