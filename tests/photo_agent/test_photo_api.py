from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.photo_agent.api import create_photo_router
from app.photo_agent.delivery import FileDeliveryAdapter, GLOBAL_PHOTO_STORE, PhotoStore
from app.photo_agent.fsm import PhotoAgentFSM
from app.photo_agent.mocks import MockCamera, MockOmni, MockQualityChecker, MockWakeDetector
from app.photo_agent.models import CaptureResult, DeliveryResult, PoseContext, PoseTurnState, QualityResult, State


@pytest.mark.asyncio
async def test_photo_api_returns_registered_file_and_404_for_unknown(tmp_path: Path) -> None:
    photo = tmp_path / "p1.jpg"
    photo.write_bytes(b"fake-jpeg")
    store = PhotoStore()
    store.register("p1", photo)
    app = FastAPI()
    app.include_router(create_photo_router(store))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get("/api/photos/p1")
        metadata = await client.get("/api/photos/p1/meta")
        missing = await client.get("/api/photos/nope")

    assert ok.status_code == 200
    assert ok.content == b"fake-jpeg"
    assert metadata.status_code == 200
    assert metadata.json() == {
        "photo_id": "p1",
        "photo_url": "http://test/api/photos/p1",
    }
    assert missing.status_code == 404

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        deleted = await client.delete("/api/photos/p1")
        after_delete = await client.get("/api/photos/p1")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "photo_id": "p1"}
    assert after_delete.status_code == 404
    assert photo.exists() is False


@pytest.mark.asyncio
async def test_dashboard_app_exposes_global_photo_store(tmp_path: Path) -> None:
    from app.main import app

    photo = tmp_path / "main.jpg"
    photo.write_bytes(b"main-photo")
    GLOBAL_PHOTO_STORE.register("main-photo", photo)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/photos/main-photo")

    assert response.status_code == 200
    assert response.content == b"main-photo"


@pytest.mark.asyncio
async def test_full_chain_photo_url_fetches_the_captured_file(tmp_path: Path) -> None:
    photo = tmp_path / "captured.jpg"
    photo.write_bytes(b"captured-photo-bytes")
    store = PhotoStore()
    delivery = FileDeliveryAdapter(store, "http://test")
    fsm = PhotoAgentFSM(
        wake_detector=MockWakeDetector([]),
        omni=MockOmni(),
        camera=MockCamera(captures=[CaptureResult("captured", photo, True, frame=object())]),
        quality_checker=MockQualityChecker([QualityResult(True, True, True)]),
        delivery=delivery,
    )
    fsm.context.state = State.POSE_GUIDANCE
    fsm.context.session_id = "session-1"
    fsm.context.pose_context = PoseContext()
    fsm.context.pose_turn = PoseTurnState(
        source="test",
        phase="capturing",
        pending_capture=True,
    )

    result, quality_ok = await fsm.run_capture_from_pose()
    await fsm.handle_pose_capture_result(
        {
            "ok": result.ok,
            "quality_ok": quality_ok,
            "photo_id": result.photo_id,
            "error": result.error,
        }
    )
    await fsm.handle_pose_speech_done("我拍好啦")
    await fsm.handle_review_intent("accept")
    result: DeliveryResult = await fsm.run_delivery()

    app = FastAPI()
    app.include_router(create_photo_router(store))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(result.photo_url)

    assert result.photo_id == "captured"
    assert response.status_code == 200
    assert response.content == b"captured-photo-bytes"
