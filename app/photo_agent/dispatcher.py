from __future__ import annotations

from typing import Any

from app.photo_agent.fsm import PhotoAgentFSM
from app.photo_agent.models import State, ToolCall


class FunctionCallDispatcher:
    """Validates and executes the four PRD tool contracts against local adapters."""

    def __init__(self, fsm: PhotoAgentFSM) -> None:
        self.fsm = fsm

    async def dispatch(self, call: ToolCall) -> dict[str, Any]:
        if call.name == "capture_photo":
            if call.arguments.get("mode") != "photo":
                return {"ok": False, "error": "unsupported_capture_mode"}
            if self.fsm.context.state is State.POSE_GUIDANCE:
                await self.fsm.handle_user_text("拍吧")
            if self.fsm.context.state is not State.SHOOT:
                return {"ok": False, "error": f"invalid_state:{self.fsm.context.state.value}"}
            result = await self.fsm.run_shoot()
            return {
                "ok": result.ok,
                "photo_id": result.photo_id,
                "path": str(result.path),
                "quality_ok": self.fsm.context.state is State.REVIEW,
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
