from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.photo_agent.prompts import PromptRegistry
from app.photo_agent.test_console_api import create_test_console_router


class FakeController:
    def __init__(self, tmp_path: Path) -> None:
        self.prompt_registry = PromptRegistry(tmp_path / "prompts.yaml", tmp_path / "history")
        self.run_store = SimpleNamespace(list=lambda: [{"state": "S2", "stop_reason": "completed"}])
        self.events = SimpleNamespace(subscribe=self._subscribe)
        self.started: list[tuple[str, dict]] = []
        self.stopped = False

    def status(self) -> dict:
        return {"active": bool(self.started) and not self.stopped, "selected_state": "S2"}

    async def start(self, state: str, **devices) -> dict:
        self.started.append((state, devices))
        return self.status()

    async def stop(self) -> dict:
        self.stopped = True
        return self.status()

    async def preview_jpeg(self) -> bytes:
        return b"\xff\xd8preview\xff\xd9"

    async def _subscribe(self, *, after: int = 0):
        yield {"seq": after + 1, "type": "ready"}
        await asyncio.sleep(10)


def make_client(tmp_path: Path) -> tuple[TestClient, FakeController]:
    controller = FakeController(tmp_path)
    app = FastAPI()
    app.include_router(create_test_console_router(controller))
    return TestClient(app), controller


def test_schema_status_start_stop_and_runs(tmp_path: Path) -> None:
    client, controller = make_client(tmp_path)

    schema = client.get("/api/photo-agent/schema")
    started = client.post(
        "/api/photo-agent/tests/S2/start",
        json={"camera_index": 1, "microphone_index": 2, "speaker_index": 3},
    )
    status = client.get("/api/photo-agent/status")
    runs = client.get("/api/photo-agent/runs")
    stopped = client.post("/api/photo-agent/tests/stop")

    assert schema.status_code == 200
    assert [item["id"] for item in schema.json()["states"]] == ["S1", "S2", "S3", "S5", "S6"]
    assert started.status_code == 200
    assert controller.started == [
        ("S2", {"camera_index": 1, "microphone_index": 2, "speaker_index": 3})
    ]
    assert status.json()["active"] is True
    assert runs.json()[0]["state"] == "S2"
    assert stopped.json()["active"] is False


def test_prompt_save_history_diff_and_rollback(tmp_path: Path) -> None:
    client, controller = make_client(tmp_path)
    current = client.get("/api/photo-agent/prompts").json()

    saved = client.put(
        "/api/photo-agent/prompts",
        json={
            "expected_version": current["version"],
            "updates": {"action.S2.ask_initial": "现在拍一张吗？"},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["prompts"]["action.S2.ask_initial"] == "现在拍一张吗？"

    history = client.get("/api/photo-agent/prompts/history").json()
    diff = client.get(
        "/api/photo-agent/prompts/diff",
        params={"before": current["version"], "after": saved.json()["version"]},
    )
    rolled_back = client.post(
        f"/api/photo-agent/prompts/{current['version']}/rollback",
        json={"expected_version": saved.json()["version"]},
    )

    assert len(history) == 2
    assert diff.json()["action.S2.ask_initial"]["before"] != diff.json()["action.S2.ask_initial"]["after"]
    assert rolled_back.status_code == 200
    assert controller.prompt_registry.get("action.S2.ask_initial") == current["prompts"]["action.S2.ask_initial"]


def test_prompt_conflict_and_validation_are_explicit(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    conflict = client.put(
        "/api/photo-agent/prompts",
        json={"expected_version": "stale", "updates": {"action.S2.ask_initial": "hello"}},
    )
    invalid = client.put(
        "/api/photo-agent/prompts",
        json={
            "expected_version": client.get("/api/photo-agent/prompts").json()["version"],
            "updates": {"unknown": "hello"},
        },
    )

    assert conflict.status_code == 409
    assert invalid.status_code == 422


def test_remote_clients_are_rejected(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    response = client.get("/api/photo-agent/status", headers={"x-forwarded-for": "192.168.1.9"})

    assert response.status_code == 403
