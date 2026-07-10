from __future__ import annotations

import asyncio
import base64
import threading

import numpy as np
import pytest

from app.photo_agent.models import ToolCall
from app.photo_agent.omni import (
    BASE_PROMPT,
    DashscopeOmniClient,
    OmniSettings,
    build_workspace_url,
    omni_tools,
)


class FakeConversation:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.callback = kwargs["callback"]
        self.calls: list[tuple[str, object]] = []
        self.session_id = "session-real-test"

    def connect(self) -> None:
        self.calls.append(("connect", None))
        self.callback.on_open()
        self.callback.on_event({"type": "session.created", "session": {"id": self.session_id}})

    def update_session(self, **kwargs) -> None:
        self.calls.append(("update_session", kwargs))

    def append_audio(self, audio: str) -> None:
        self.calls.append(("append_audio", audio))

    def append_video(self, image: str) -> None:
        self.calls.append(("append_video", image))

    def create_item(self, item: dict) -> None:
        self.calls.append(("create_item", item))

    def create_response(self, instructions: str | None = None) -> None:
        self.calls.append(("create_response", instructions))

    def cancel_response(self) -> None:
        self.calls.append(("cancel_response", None))

    def end_session_async(self) -> None:
        self.calls.append(("end_session_async", None))

    def close(self) -> None:
        self.calls.append(("close", None))


def make_client() -> tuple[DashscopeOmniClient, list[FakeConversation]]:
    made: list[FakeConversation] = []

    def factory(**kwargs) -> FakeConversation:
        conv = FakeConversation(**kwargs)
        made.append(conv)
        return conv

    settings = OmniSettings(
        api_key="test-key-not-secret",
        workspace_host="workspace.cn-beijing.maas.aliyuncs.com",
        model="qwen3.5-omni-flash-realtime",
        voice="Tina",
    )
    return DashscopeOmniClient(settings, conversation_factory=factory), made


def test_workspace_url_is_https_host_normalized_to_wss() -> None:
    assert build_workspace_url("https://workspace.cn-beijing.maas.aliyuncs.com/") == (
        "wss://workspace.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime"
    )


def test_tools_match_s4_to_s6_contract() -> None:
    names = {tool["function"]["name"] for tool in omni_tools()}
    assert names == {"capture_photo", "show_on_screen", "generate_download_qr", "end_session"}


def test_system_prompt_forbids_replacing_required_tool_calls_with_speech() -> None:
    assert "不能用口头回答代替" in BASE_PROMPT


@pytest.mark.asyncio
async def test_real_client_configures_vad_tools_and_primes_audio_before_image() -> None:
    client, made = make_client()
    session_id = await client.connect()
    await client.configure()
    await client.prime_audio()
    await client.append_image(np.zeros((8, 8, 3), dtype=np.uint8))

    assert session_id == "session-real-test"
    update = next(value for name, value in made[0].calls if name == "update_session")
    assert update["enable_turn_detection"] is True
    assert update["enable_search"] is False
    assert update["tools"] == omni_tools()
    names = [name for name, _ in made[0].calls]
    assert names.index("append_audio") < names.index("append_video")


@pytest.mark.asyncio
async def test_real_client_can_configure_manual_turn_detection() -> None:
    client, made = make_client()
    await client.connect()

    await client.configure(enable_vad=False)

    update = next(value for name, value in made[0].calls if name == "update_session")
    assert update["enable_turn_detection"] is False


@pytest.mark.asyncio
async def test_real_audio_counts_as_image_primer_without_duplicate_silence() -> None:
    client, made = make_client()
    await client.connect()

    await client.append_audio(b"real-pcm")
    await client.append_image(np.zeros((8, 8, 3), dtype=np.uint8))

    assert [name for name, _ in made[0].calls].count("append_audio") == 1


@pytest.mark.asyncio
async def test_callback_surfaces_vad_function_call_output_and_errors() -> None:
    client, made = make_client()
    await client.connect()
    callback = made[0].callback
    callback.on_event({"type": "input_audio_buffer.speech_started"})
    callback.on_event(
        {
            "type": "response.function_call_arguments.done",
            "name": "capture_photo",
            "arguments": '{"mode":"photo"}',
            "call_id": "call-1",
        }
    )
    callback.on_event({"type": "error", "error": {"code": "bad_request"}})
    await asyncio.sleep(0)

    assert await client.next_event() == {"type": "speech_started"}
    assert await client.next_event() == {
        "type": "tool_call",
        "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "call-1"),
    }
    assert (await client.next_event())["type"] == "error"


@pytest.mark.asyncio
async def test_unexpected_websocket_close_surfaces_disconnected_event() -> None:
    client, made = make_client()
    await client.connect()

    made[0].callback.on_close(1006, "network lost")
    await asyncio.sleep(0)

    event = await client.next_event()
    assert event == {"type": "disconnected", "code": 1006, "message": "network lost"}


@pytest.mark.asyncio
async def test_tool_result_is_returned_before_followup_response() -> None:
    client, made = make_client()
    await client.connect()

    await client.submit_tool_result("call-1", {"ok": True, "photo_id": "p1"})

    create_item = next(value for name, value in made[0].calls if name == "create_item")
    assert create_item["type"] == "function_call_output"
    assert create_item["call_id"] == "call-1"
    assert '"photo_id": "p1"' in create_item["output"]
    names = [name for name, _ in made[0].calls]
    assert names.index("create_item") < names.index("create_response")


@pytest.mark.asyncio
async def test_audio_delta_is_decoded_to_sink() -> None:
    chunks: list[bytes] = []
    client, made = make_client()
    client.audio_sink = chunks.append
    await client.connect()
    made[0].callback.on_event(
        {"type": "response.audio.delta", "delta": base64.b64encode(b"pcm").decode()}
    )
    await asyncio.sleep(0)

    assert chunks == [b"pcm"]


@pytest.mark.asyncio
async def test_audio_output_error_is_reported_as_runtime_event() -> None:
    client, made = make_client()

    def failing_sink(pcm: bytes) -> None:
        raise OSError("speaker unavailable")

    client.audio_sink = failing_sink
    await client.connect()

    made[0].callback.on_event(
        {"type": "response.audio.delta", "delta": base64.b64encode(b"pcm").decode()}
    )
    await asyncio.sleep(0)

    event = await client.next_event()
    assert event["type"] == "error"
    assert event["error"]["code"] == "audio_output_failed"


@pytest.mark.asyncio
async def test_failed_connect_closes_partial_websocket() -> None:
    class FailingConversation(FakeConversation):
        def connect(self) -> None:
            self.calls.append(("connect", None))
            raise TimeoutError("connect timeout")

    made: list[FailingConversation] = []

    def factory(**kwargs):
        conversation = FailingConversation(**kwargs)
        made.append(conversation)
        return conversation

    client = DashscopeOmniClient(
        OmniSettings("test-key", "workspace.cn-beijing.maas.aliyuncs.com"),
        conversation_factory=factory,
    )

    with pytest.raises(TimeoutError, match="connect timeout"):
        await client.connect()

    assert ("close", None) in made[0].calls


@pytest.mark.asyncio
async def test_connect_waits_for_delayed_session_created_callback() -> None:
    class DelayedSessionConversation(FakeConversation):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.session_id = None

        def connect(self) -> None:
            self.calls.append(("connect", None))
            threading.Timer(
                0.05,
                lambda: self.callback.on_event(
                    {"type": "session.created", "session": {"id": "session-delayed"}}
                ),
            ).start()

    client = DashscopeOmniClient(
        OmniSettings("test-key", "workspace.cn-beijing.maas.aliyuncs.com"),
        conversation_factory=lambda **kwargs: DelayedSessionConversation(**kwargs),
    )

    assert await client.connect() == "session-delayed"
