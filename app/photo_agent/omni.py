"""Qwen Omni Realtime adapter based on the official DashScope SDK."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

from app.photo_agent.camera import encode_frame
from app.photo_agent.models import ToolCall
from app.photo_agent.prompts import DEFAULT_PROMPTS, PromptSource, StaticPromptSource

BASE_PROMPT = DEFAULT_PROMPTS["system.base"]
LOGGER = logging.getLogger("photomate.photo_agent.omni")


@dataclass(frozen=True)
class OmniSettings:
    api_key: str
    workspace_host: str
    model: str = "qwen3.5-omni-flash-realtime"
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
            "report_photo_intent",
            (
                "仅在S2第①步（ask_intent）使用。用户明确愿意或拒绝拍照后必须调用；"
                "禁止在调用前口头替用户选设备或提及 Insta360/手机。"
            ),
            {
                "decision": {
                    "type": "string",
                    "enum": ["accept", "deny"],
                    "description": "accept表示愿意拍照，deny表示拒绝拍照。",
                }
            },
            ["decision"],
        ),
        tool(
            "report_capture_device",
            (
                "仅在S2第②步（ask_device）使用：用户已 accept 且系统已问过手机/Insta360 二选一之后。"
                "根据用户原话判断设备；禁止在用户未选择前默认 insta。"
            ),
            {
                "device": {
                    "type": "string",
                    "enum": ["phone", "insta"],
                    "description": "phone表示用户自己的手机，insta表示Insta360机器人相机。",
                }
            },
            ["device"],
        ),
        tool(
            "report_capture_mode",
            (
                "仅在S2用户已选好Insta360相机、系统询问一键拍照还是录像之后使用。"
                "根据用户原始语音判断所选模式；意图明确后必须调用此工具，不要用口头回答代替。"
            ),
            {
                "mode": {
                    "type": "string",
                    "enum": ["photo", "video"],
                    "description": "photo表示一键拍照，video表示录像。",
                }
            },
            ["mode"],
        ),
        tool(
            "report_pose_turn",
            (
                "仅在S3使用。观察当前画面并结合已提供的PoseContext，创建、维持、替换或完成"
                "一个姿态目标。评估响应中必须且只能调用一次本工具。"
            ),
            {
                "goal_action": {
                    "type": "string",
                    "enum": ["create", "keep", "replace", "complete"],
                    "description": (
                        "只能取create、keep、replace、complete之一。"
                        "progress=achieved时必须填complete，禁止填keep。"
                    ),
                },
                "goal_description": {"type": "string"},
                "success_criteria": {
                    "type": "string",
                    "description": "用分号分隔多个可观察的完成条件。",
                },
                "progress": {
                    "type": "string",
                    "enum": ["not_started", "partial", "achieved"],
                    "description": (
                        "只能取not_started、partial、achieved之一。"
                        "填achieved时goal_action必须=complete。"
                    ),
                },
                "visual_observation": {"type": "string"},
                "user_feedback_summary": {"type": "string"},
                "replace_reason": {"type": "string"},
                "guidance_intent": {
                    "type": "string",
                    "description": (
                        "下一轮要对用户说的中文要点。"
                        "intro示例：您可以站在这块牌子前，双手比一个心，这样会更生动。"
                        "coach示例：黑色T恤很上镜，手再靠近一点就完美啦。禁止填none。"
                    ),
                },
                "completion_reason": {
                    "type": "string",
                    "enum": ["none", "visual_goal_achieved", "user_requested_capture"],
                },
            },
            [
                "goal_action",
                "progress",
                "visual_observation",
                "user_feedback_summary",
                "guidance_intent",
                "completion_reason",
            ],
        ),
        tool(
            "report_pose_readiness",
            (
                "仅在S3姿态引导环节使用。用户明确表示直接拍照、现在拍、可以拍了或已经准备好时"
                "必须调用；此时不要直接调用capture_photo。"
            ),
            {
                "decision": {
                    "type": "string",
                    "enum": ["ready"],
                    "description": "ready表示用户明确要求现在拍照。",
                }
            },
            ["decision"],
        ),
        tool(
            "report_review_intent",
            "仅在S5照片复核环节使用。直接根据用户原始语音判断接受照片还是要求重拍；意图明确后必须调用此工具。",
            {
                "decision": {
                    "type": "string",
                    "enum": ["accept", "retake"],
                    "description": "accept表示满意并交付，retake表示不满意并重拍。",
                }
            },
            ["decision"],
        ),
        tool(
            "capture_photo",
            (
                "仅当当前response的instructions明确要求执行action.S3.capture时调用，"
                "触发相机/Insta360快门；用户口头要求直接拍照时不要直接调用本工具，"
                "应先调用report_pose_readiness。"
            ),
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
    def __init__(self, owner: "DashscopeOmniClient", generation: int) -> None:
        self.owner = owner
        self.generation = generation

    def _is_current(self) -> bool:
        return self.owner._callback is self and self.owner._generation == self.generation

    def on_open(self) -> None:
        return

    def on_close(self, code: int | None, message: str | None) -> None:
        if self._is_current() and not self.owner._closing:
            self.owner._emit({"type": "disconnected", "code": code, "message": message})

    def on_event(self, response: dict[str, Any]) -> None:
        if not self._is_current():
            return
        event_type = response.get("type", "")
        if event_type == "session.created":
            self.owner.session_id = response.get("session", {}).get("id")
        elif event_type == "response.created":
            self.owner._active_response_audio_deltas = 0
            self.owner._emit(
                {"type": "response_created", "response_id": response.get("response", {}).get("id")}
            )
        elif event_type == "response.audio.delta":
            self.owner._active_response_audio_deltas += 1
            delta = response.get("delta")
            if delta and self.owner.audio_sink:
                try:
                    self.owner.audio_sink(base64.b64decode(delta))
                except Exception as exc:  # noqa: BLE001 - audio output boundary
                    self.owner._emit(
                        {
                            "type": "error",
                            "error": {"code": "audio_output_failed", "message": str(exc)},
                        }
                    )
        elif event_type == "response.audio_transcript.done":
            self.owner._emit(
                {
                    "type": "assistant_text",
                    "response_id": response.get("response_id"),
                    "text": response.get("transcript", ""),
                }
            )
        elif event_type == "response.text.done":
            self.owner._emit(
                {
                    "type": "assistant_text",
                    "response_id": response.get("response_id"),
                    "text": response.get("text", ""),
                    "source": "text",
                }
            )
        elif event_type == "response.done":
            if self.owner._loop is not None:
                self.owner._loop.call_soon_threadsafe(self.owner._response_done.set)
            response_id = response.get("response_id") or response.get("response", {}).get("id")
            LOGGER.info(
                "response_audio_summary",
                extra={
                    "response_id": response_id,
                    "audio_delta_count": self.owner._active_response_audio_deltas,
                    "session_output_audio": self.owner.output_audio_enabled,
                    "has_audio_sink": self.owner.audio_sink is not None,
                },
            )
            self.owner._emit(
                {
                    "type": "response_done",
                    "response_id": response_id,
                    "audio_delta_count": self.owner._active_response_audio_deltas,
                }
            )
        elif event_type == "input_audio_buffer.speech_started":
            self.owner._emit({"type": "speech_started"})
        elif event_type == "input_audio_buffer.speech_stopped":
            self.owner._emit({"type": "speech_stopped"})
        elif event_type == "input_audio_buffer.committed":
            self.owner._primed = False
        elif event_type == "response.function_call_arguments.done":
            try:
                arguments = json.loads(response.get("arguments") or "{}")
                call = ToolCall(response["name"], arguments, response["call_id"])
                event = {"type": "tool_call", "tool_call": call}
                if response.get("response_id"):
                    event["response_id"] = response["response_id"]
                self.owner._emit(event)
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
        prompt_source: PromptSource | None = None,
    ) -> None:
        self.settings = settings
        self.conversation_factory = conversation_factory
        self.audio_sink = audio_sink
        self.prompt_source = prompt_source or StaticPromptSource()
        self._enable_vad = True
        self._output_audio_enabled = True
        self.session_id: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._conversation: Any | None = None
        self._callback: _Callback | None = None
        self._generation = 0
        self._write_lock = asyncio.Lock()
        self._response_done = asyncio.Event()
        self._primed = False
        self._closing = False
        self._active_response_audio_deltas = 0

    @property
    def vad_enabled(self) -> bool:
        return self._enable_vad

    @property
    def output_audio_enabled(self) -> bool:
        return self._output_audio_enabled

    def _raise_connect_failure(self, exc: Exception) -> None:
        message = str(exc)
        if isinstance(exc, TimeoutError) and "websocket connection could not established" in message:
            ws = getattr(self._conversation, "ws", None)
            thread = getattr(self._conversation, "thread", None)
            thread_alive = bool(thread and thread.is_alive())
            if ws is None or not thread_alive:
                raise ConnectionError(
                    "Omni WebSocket handshake failed before session creation. "
                    "This is usually caused by a missing, expired, or workspace-mismatched "
                    "DASHSCOPE_API_KEY, not a network timeout. "
                    "Re-export the key in the same shell that starts uvicorn, then retry."
                ) from exc
        raise exc

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
        self._generation += 1
        self._events = asyncio.Queue()
        self.session_id = None
        self._primed = False
        self._callback = _Callback(self, self._generation)
        self._conversation = factory(
            model=self.settings.model,
            callback=self._callback,
            url=build_workspace_url(self.settings.workspace_host),
            api_key=self.settings.api_key,
        )
        try:
            await asyncio.to_thread(self._conversation.connect)
            deadline = self._loop.time() + 5.0
            session_id = self.session_id or getattr(self._conversation, "session_id", None)
            while not session_id and self._loop.time() < deadline:
                await asyncio.sleep(0.01)
                session_id = self.session_id or getattr(self._conversation, "session_id", None)
            if not session_id:
                raise RuntimeError("Omni session was not created")
        except Exception as exc:
            self._closing = True
            try:
                await asyncio.to_thread(self._conversation.close)
            finally:
                self._conversation = None
                self._callback = None
                self._closing = False
            self._raise_connect_failure(exc)
        self.session_id = session_id
        return session_id

    async def configure(
        self,
        *,
        enable_vad: bool = True,
        output_audio: bool = True,
        tools: list[dict[str, Any]] | None = None,
    ) -> None:
        if self._conversation is None:
            raise ConnectionError("Omni is not connected")
        from dashscope.audio.qwen_omni import MultiModality

        self._enable_vad = enable_vad
        self._output_audio_enabled = output_audio
        modalities = [MultiModality.TEXT]
        if output_audio:
            modalities.append(MultiModality.AUDIO)
        session_tools = omni_tools() if tools is None else tools
        await asyncio.to_thread(
            self._conversation.update_session,
            output_modalities=modalities,
            voice=self.settings.voice,
            enable_input_audio_transcription=False,
            enable_turn_detection=enable_vad,
            turn_detection_type=self.settings.vad_type,
            turn_detection_silence_duration_ms=self.settings.vad_silence_ms,
            instructions=self.prompt_source.get("system.base"),
            tools=session_tools,
            enable_search=False,
        )

    async def update_instructions(self, instructions: str) -> None:
        if self._conversation is None:
            raise ConnectionError("Omni is not connected")
        from dashscope.audio.qwen_omni import MultiModality

        modalities = [MultiModality.TEXT]
        if self._output_audio_enabled:
            modalities.append(MultiModality.AUDIO)
        await self._call(
            "update_session",
            output_modalities=modalities,
            voice=self.settings.voice,
            enable_input_audio_transcription=False,
            enable_turn_detection=self._enable_vad,
            turn_detection_type=self.settings.vad_type,
            turn_detection_silence_duration_ms=self.settings.vad_silence_ms,
            instructions=instructions,
            tools=omni_tools(),
            enable_search=False,
        )

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        async with self._write_lock:
            conversation = self._conversation
            if conversation is None:
                raise ConnectionError("Omni is not connected")
            return await asyncio.to_thread(getattr(conversation, method), *args, **kwargs)

    async def prime_audio(self) -> None:
        await self.append_audio(b"\x00\x00" * 1600)
        self._primed = True

    async def append_audio(self, pcm: bytes) -> None:
        await self._call("append_audio", base64.b64encode(pcm).decode("ascii"))
        self._primed = True

    async def append_image(self, frame: Any) -> None:
        # Server VAD commits clear the audio buffer; always prime immediately before
        # each image so we never race committed events with a stale _primed flag.
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

    async def create_response(self, instructions: str, *, output_audio: bool = True) -> None:
        from dashscope.audio.qwen_omni import MultiModality

        self._response_done.clear()
        self._active_response_audio_deltas = 0
        modalities = [MultiModality.TEXT]
        if output_audio:
            modalities.append(MultiModality.AUDIO)
        await self._call(
            "create_response",
            instructions=instructions,
            output_modalities=modalities,
        )

    async def wait_response_done(self, timeout: float) -> None:
        await asyncio.wait_for(self._response_done.wait(), timeout)

    async def cancel_response(self) -> None:
        await self._call("cancel_response")

    async def submit_tool_result(
        self,
        call_id: str,
        output: dict[str, Any],
        *,
        create_followup: bool = True,
    ) -> None:
        await self._call(
            "create_item",
            {"type": "function_call_output", "call_id": call_id, "output": json.dumps(output, ensure_ascii=False)},
        )
        if create_followup:
            await self.create_response(self.prompt_source.get("action.tool.followup"))

    async def end_session(self, reason: str) -> None:
        if self._conversation is None:
            return
        await self.inject_context(
            self.prompt_source.render("action.session.end_context", reason=reason)
        )

    async def close(self) -> None:
        if self._conversation is None:
            return
        self._closing = True
        try:
            await self._call("close")
        finally:
            self._conversation = None
            self._callback = None
            self._primed = False
            self._closing = False
