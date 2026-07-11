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

    def create_response(
        self,
        instructions: str | None = None,
        output_modalities: list | None = None,
    ) -> None:
        self.calls.append(
            (
                "create_response",
                {"instructions": instructions, "output_modalities": output_modalities},
            )
        )

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


def test_tools_include_all_omni_voice_intent_contracts() -> None:
    tools = {tool["function"]["name"]: tool["function"] for tool in omni_tools()}

    assert set(tools) == {
        "report_photo_intent",
        "report_capture_device",
        "report_capture_mode",
        "report_pose_turn",
        "report_pose_readiness",
        "report_review_intent",
        "capture_photo",
        "show_on_screen",
        "generate_download_qr",
        "end_session",
    }
    assert tools["report_photo_intent"]["parameters"]["properties"]["decision"]["enum"] == [
        "accept",
        "deny",
    ]
    assert tools["report_capture_device"]["parameters"]["properties"]["device"]["enum"] == [
        "phone",
        "insta",
    ]
    assert tools["report_capture_mode"]["parameters"]["properties"]["mode"]["enum"] == [
        "photo",
        "video",
    ]
    assert tools["report_pose_readiness"]["parameters"]["properties"]["decision"]["enum"] == [
        "ready"
    ]
    pose_turn = tools["report_pose_turn"]["parameters"]
    assert pose_turn["properties"]["goal_action"]["enum"] == [
        "create",
        "keep",
        "replace",
        "complete",
    ]
    assert pose_turn["properties"]["progress"]["enum"] == [
        "not_started",
        "partial",
        "achieved",
    ]
    assert pose_turn["properties"]["goal_description"]["type"] == "string"
    assert pose_turn["properties"]["success_criteria"]["type"] == "string"
    assert pose_turn["required"] == [
        "goal_action",
        "progress",
        "visual_observation",
        "user_feedback_summary",
        "guidance_intent",
        "completion_reason",
    ]
    assert "active_goal" not in pose_turn["properties"]
    assert pose_turn["properties"]["completion_reason"]["type"] == "string"
    assert None not in pose_turn["properties"]["completion_reason"]["enum"]
    assert tools["report_review_intent"]["parameters"]["properties"]["decision"]["enum"] == [
        "accept",
        "retake",
    ]


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
async def test_real_client_disables_input_transcription_for_entire_session() -> None:
    client, made = make_client()
    await client.connect()

    await client.configure()
    await client.update_instructions("UPDATED SYSTEM")

    updates = [value for name, value in made[0].calls if name == "update_session"]
    assert updates[0]["enable_input_audio_transcription"] is False
    assert updates[1]["enable_input_audio_transcription"] is False


@pytest.mark.asyncio
async def test_append_image_primes_audio_even_after_real_audio_was_sent() -> None:
    client, made = make_client()
    await client.connect()

    await client.append_audio(b"real-pcm")
    await client.append_image(np.zeros((8, 8, 3), dtype=np.uint8))

    assert [name for name, _ in made[0].calls].count("append_audio") == 2


@pytest.mark.asyncio
async def test_append_image_always_primes_audio_even_when_already_primed() -> None:
    client, made = make_client()
    await client.connect()
    await client.append_audio(b"pcm")
    await client.append_image(np.zeros((8, 8, 3), dtype=np.uint8))

    assert [name for name, _ in made[0].calls].count("append_audio") == 2


@pytest.mark.asyncio
async def test_server_vad_commit_requires_audio_to_be_primed_again_before_image() -> None:
    client, made = make_client()
    await client.connect()
    await client.append_audio(b"first-turn-pcm")
    made[0].callback.on_event({"type": "input_audio_buffer.committed"})

    await client.append_image(np.zeros((8, 8, 3), dtype=np.uint8))

    assert [name for name, _ in made[0].calls].count("append_audio") == 2


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
            "response_id": "response-1",
        }
    )
    callback.on_event({"type": "error", "error": {"code": "bad_request"}})
    await asyncio.sleep(0)

    assert await client.next_event() == {"type": "speech_started"}
    assert await client.next_event() == {
        "type": "tool_call",
        "response_id": "response-1",
        "tool_call": ToolCall("capture_photo", {"mode": "photo"}, "call-1"),
    }
    assert (await client.next_event())["type"] == "error"


@pytest.mark.asyncio
async def test_callback_ignores_sidecar_input_transcription_events() -> None:
    client, made = make_client()
    await client.connect()

    made[0].callback.on_event(
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "transcript": "不应进入运行时",
        }
    )
    made[0].callback.on_event({"type": "input_audio_buffer.speech_started"})
    await asyncio.sleep(0)

    assert await client.next_event() == {"type": "speech_started"}


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
async def test_response_can_override_output_to_text_only_or_audio() -> None:
    client, made = make_client()
    await client.connect()

    await client.create_response("assess", output_audio=False)
    await client.create_response("speak", output_audio=True)

    responses = [value for name, value in made[0].calls if name == "create_response"]
    assert [item.value for item in responses[0]["output_modalities"]] == ["text"]
    assert [item.value for item in responses[1]["output_modalities"]] == ["text", "audio"]


@pytest.mark.asyncio
async def test_configure_can_disable_tools_for_speech_turns() -> None:
    client, made = make_client()
    await client.connect()

    await client.configure(enable_vad=True, output_audio=True, tools=[])

    update = [value for name, value in made[0].calls if name == "update_session"][-1]
    assert update["tools"] == []


@pytest.mark.asyncio
async def test_callback_correlates_transcript_text_and_done_with_response_id() -> None:
    client, made = make_client()
    await client.connect()
    callback = made[0].callback

    callback.on_event(
        {
            "type": "response.audio_transcript.done",
            "response_id": "speech-1",
            "transcript": "一起比个心吧",
        }
    )
    callback.on_event(
        {
            "type": "response.text.done",
            "response_id": "assess-1",
            "text": "unexpected assessment prose",
        }
    )
    callback.on_event({"type": "response.done", "response": {"id": "speech-1"}})
    await asyncio.sleep(0)

    assert await client.next_event() == {
        "type": "assistant_text",
        "response_id": "speech-1",
        "text": "一起比个心吧",
    }
    assert await client.next_event() == {
        "type": "assistant_text",
        "response_id": "assess-1",
        "text": "unexpected assessment prose",
        "source": "text",
    }
    assert await client.next_event() == {
        "type": "response_done",
        "response_id": "speech-1",
        "audio_delta_count": 0,
    }


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
async def test_connect_timeout_surfaces_api_key_hint_when_socket_never_opens() -> None:
    class DeadSocketConversation(FakeConversation):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.ws = None
            self.thread = type("Thread", (), {"is_alive": lambda self: False})()

        def connect(self) -> None:
            self.calls.append(("connect", None))
            raise TimeoutError(
                "websocket connection could not established within 5s. "
                "Please check your network connection, firewall settings, or server status."
            )

    made: list[DeadSocketConversation] = []

    def factory(**kwargs):
        conversation = DeadSocketConversation(**kwargs)
        made.append(conversation)
        return conversation

    client = DashscopeOmniClient(
        OmniSettings("test-key", "workspace.cn-beijing.maas.aliyuncs.com"),
        conversation_factory=factory,
    )

    with pytest.raises(ConnectionError, match="DASHSCOPE_API_KEY"):
        await client.connect()

    assert ("close", None) in made[0].calls


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


@pytest.mark.asyncio
async def test_reconnect_discards_events_and_callbacks_from_the_previous_session() -> None:
    client, made = make_client()
    await client.connect()
    previous_callback = made[0].callback
    await client.close()

    await client.connect()
    previous_callback.on_event({"type": "error", "error": {"code": "stale"}})
    made[1].callback.on_event({"type": "input_audio_buffer.speech_started"})
    await asyncio.sleep(0)

    assert await client.next_event() == {"type": "speech_started"}


@pytest.mark.asyncio
async def test_call_rechecks_connection_after_waiting_for_write_lock() -> None:
    client, _ = make_client()
    await client.connect()
    await client._write_lock.acquire()
    append_task = asyncio.create_task(client.append_audio(b"pcm"))
    await asyncio.sleep(0)
    client._conversation = None
    client._write_lock.release()

    with pytest.raises(ConnectionError, match="not connected"):
        await append_task


@pytest.mark.asyncio
async def test_end_session_does_not_send_unsupported_session_finish_event() -> None:
    client, made = make_client()
    await client.connect()

    await client.end_session("timeout")

    assert ("end_session_async", None) not in made[0].calls
