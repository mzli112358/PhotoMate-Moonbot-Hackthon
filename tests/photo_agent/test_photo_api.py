from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.photo_agent.api import create_photo_router
from app.photo_agent.delivery import GLOBAL_PHOTO_STORE, PhotoStore


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
        missing = await client.get("/api/photos/nope")

    assert ok.status_code == 200
    assert ok.content == b"fake-jpeg"
    assert missing.status_code == 404


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
