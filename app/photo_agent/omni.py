"""Qwen Omni Realtime adapter based on the official DashScope SDK."""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

from app.photo_agent.camera import encode_frame
from app.photo_agent.models import ToolCall

BASE_PROMPT = (
    "你是热情、幽默、会逗人开心的活动摄影师。每轮只说一两句简短中文。"
    "你负责自然对话、粗粒度姿态引导和工具调用；状态、计时、重试由本地编排层负责。"
    "未经用户同意不保存到云端，不要声称控制了未接入的机器人或 Insta360 能力。"
)


@dataclass(frozen=True)
class OmniSettings:
    api_key: str
    workspace_host: str
    model: str = "qwen3.5-omni-flash-2026-03-15"
    voice: str = "Tina"
    vad_type: str = "server_vad"
    vad_silence_ms: int = 800


def build_workspace_url(host: str) -> str:
    normalized = host.strip().rstrip("/")
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    if not parsed.hostname:
        raise ValueError("invalid workspace host")
    return f"wss://{parsed.hostname}/api-ws/v1/realtime"


def omni_tools() -> list[dict[str, Any]]:
    def tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    return [
        tool(
            "capture_photo",
            "在倒数结束后拍照。",
            {"mode": {"type": "string", "enum": ["photo"]}},
            ["mode"],
        ),
        tool(
            "show_on_screen",
            "展示指定照片供用户复核。",
            {"photo_id": {"type": "string"}},
            ["photo_id"],
        ),
        tool(
            "generate_download_qr",
            "为指定照片生成可交付的下载链接。前端可据此生成二维码。",
            {"photo_id": {"type": "string"}},
            ["photo_id"],
        ),
        tool(
            "end_session",
            "结束服务并复位。",
            {"reason": {"type": "string", "enum": ["delivered", "user_declined", "timeout"]}},
            ["reason"],
        ),
    ]


class _Callback:
    def __init__(self, owner: "DashscopeOmniClient") -> None:
        self.owner = owner

    def on_open(self) -> None:
        return

    def on_close(self, code: int | None, message: str | None) -> None:
        if not self.owner._closing:
            self.owner._emit({"type": "disconnected", "code": code, "message": message})

    def on_event(self, response: dict[str, Any]) -> None:
        event_type = response.get("type", "")
        if event_type == "session.created":
            self.owner.session_id = response.get("session", {}).get("id")
        elif event_type == "response.created":
            self.owner._emit(
                {"type": "response_created", "response_id": response.get("response", {}).get("id")}
            )
        elif event_type == "response.audio.delta":
            delta = response.get("delta")
            if delta and self.owner.audio_sink:
                self.owner.audio_sink(base64.b64decode(delta))
        elif event_type == "response.audio_transcript.done":
            self.owner._emit({"type": "assistant_text", "text": response.get("transcript", "")})
        elif event_type == "response.done":
            if self.owner._loop is not None:
                self.owner._loop.call_soon_threadsafe(self.owner._response_done.set)
            self.owner._emit({"type": "response_done"})
        elif event_type == "conversation.item.input_audio_transcription.completed":
            text = response.get("transcript", "").strip()
            if text:
                self.owner._emit({"type": "user_text", "text": text})
        elif event_type == "input_audio_buffer.speech_started":
            self.owner._emit({"type": "speech_started"})
        elif event_type == "input_audio_buffer.speech_stopped":
            self.owner._emit({"type": "speech_stopped"})
        elif event_type == "response.function_call_arguments.done":
            try:
                arguments = json.loads(response.get("arguments") or "{}")
                call = ToolCall(response["name"], arguments, response["call_id"])
                self.owner._emit({"type": "tool_call", "tool_call": call})
            except (KeyError, json.JSONDecodeError) as exc:
                self.owner._emit({"type": "error", "error": {"code": "invalid_tool_call", "message": str(exc)}})
        elif event_type == "error":
            self.owner._emit({"type": "error", "error": response.get("error", {})})


class DashscopeOmniClient:
    def __init__(
        self,
        settings: OmniSettings,
        *,
        conversation_factory: Callable[..., Any] | None = None,
        audio_sink: Callable[[bytes], None] | None = None,
    ) -> None:
        self.settings = settings
        self.conversation_factory = conversation_factory
        self.audio_sink = audio_sink
        self.session_id: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._conversation: Any | None = None
        self._callback = _Callback(self)
        self._write_lock = asyncio.Lock()
        self._response_done = asyncio.Event()
        self._primed = False
        self._closing = False

    def _emit(self, event: dict[str, Any]) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._events.put_nowait, event)

    async def next_event(self, timeout: float | None = None) -> dict[str, Any]:
        if timeout is None:
            return await self._events.get()
        return await asyncio.wait_for(self._events.get(), timeout)

    async def connect(self) -> str:
        if not self.settings.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is missing")
        self._loop = asyncio.get_running_loop()
        factory = self.conversation_factory
        if factory is None:
            from dashscope.audio.qwen_omni import OmniRealtimeConversation

            factory = OmniRealtimeConversation
        self._conversation = factory(
            model=self.settings.model,
            callback=self._callback,
            url=build_workspace_url(self.settings.workspace_host),
            api_key=self.settings.api_key,
        )
        try:
            await asyncio.to_thread(self._conversation.connect)
        except Exception:
            self._closing = True
            try:
                await asyncio.to_thread(self._conversation.close)
            finally:
                self._conversation = None
                self._closing = False
            raise
        session_id = self.session_id or getattr(self._conversation, "session_id", None)
        if not session_id:
            raise RuntimeError("Omni session was not created")
        self.session_id = session_id
        return session_id

    async def configure(self) -> None:
        if self._conversation is None:
            raise ConnectionError("Omni is not connected")
        from dashscope.audio.qwen_omni import MultiModality

        await asyncio.to_thread(
            self._conversation.update_session,
            output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],
            voice=self.settings.voice,
            enable_turn_detection=True,
            turn_detection_type=self.settings.vad_type,
            turn_detection_silence_duration_ms=self.settings.vad_silence_ms,
            instructions=BASE_PROMPT,
            tools=omni_tools(),
            enable_search=False,
        )

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        if self._conversation is None:
            raise ConnectionError("Omni is not connected")
        async with self._write_lock:
            return await asyncio.to_thread(getattr(self._conversation, method), *args, **kwargs)

    async def prime_audio(self) -> None:
        await self.append_audio(b"\x00\x00" * 1600)
        self._primed = True

    async def append_audio(self, pcm: bytes) -> None:
        await self._call("append_audio", base64.b64encode(pcm).decode("ascii"))

    async def append_image(self, frame: Any) -> None:
        if not self._primed:
            await self.prime_audio()
        encoded = encode_frame(frame)
        if encoded is None:
            raise ValueError("frame cannot be encoded within Omni image limit")
        await self._call("append_video", encoded)

    async def commit_input(self) -> None:
        await self._call("commit")

    async def inject_context(self, text: str) -> None:
        await self._call(
            "create_item",
            {
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": text}],
            },
        )

    async def create_response(self, instructions: str) -> None:
        self._response_done.clear()
        await self._call("create_response", instructions=instructions)

    async def wait_response_done(self, timeout: float) -> None:
        await asyncio.wait_for(self._response_done.wait(), timeout)

    async def cancel_response(self) -> None:
        await self._call("cancel_response")

    async def submit_tool_result(self, call_id: str, output: dict[str, Any]) -> None:
        await self._call(
            "create_item",
            {"type": "function_call_output", "call_id": call_id, "output": json.dumps(output, ensure_ascii=False)},
        )
        await self.create_response("根据工具执行结果，用一句简短中文继续回复用户。")

    async def end_session(self, reason: str) -> None:
        if self._conversation is None:
            return
        await self.inject_context(f"会话结束原因：{reason}")
        await self._call("end_session_async")

    async def close(self) -> None:
        if self._conversation is None:
            return
        self._closing = True
        try:
            await self._call("close")
        finally:
            self._conversation = None
            self._primed = False
            self._closing = False
