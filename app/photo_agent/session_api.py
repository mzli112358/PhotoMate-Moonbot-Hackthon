"""Production HTTP API that lets the kiosk browser follow the live session."""

from __future__ import annotations

import asyncio
import io
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.photo_agent.session_service import PREVIEW_INTERVAL_S, LiveSessionService


class StartSessionBody(BaseModel):
    camera_index: int | None = Field(default=None, ge=0)
    microphone_index: int | None = Field(default=None, ge=0)
    speaker_index: int | None = Field(default=None, ge=0)


def _render_qr_png(data: str) -> bytes:
    import segno

    qr = segno.make(data, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=8, border=2, dark="#0f172a", light="#ffffff")
    return buffer.getvalue()


def create_session_router(service: LiveSessionService) -> APIRouter:
    router = APIRouter(prefix="/api/photo-agent/session")

    @router.post("/start")
    async def start(body: StartSessionBody) -> dict[str, Any]:
        try:
            return await service.start(**body.model_dump())
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"设备不可用: {exc}。请确认相机/麦克风/扬声器已连接并可用。",
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/stop")
    async def stop() -> dict[str, Any]:
        return await service.stop()

    @router.get("/state")
    async def state() -> dict[str, Any]:
        return service.snapshot()

    @router.get("/stream")
    async def stream(request: Request, after: int = 0) -> StreamingResponse:
        async def gen() -> AsyncIterator[str]:
            async for event in service.events.subscribe(after=after):
                if await request.is_disconnected():
                    break
                yield f"id: {event['seq']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.get("/preview.mjpg")
    async def preview(request: Request) -> StreamingResponse:
        async def gen() -> AsyncIterator[bytes]:
            while not await request.is_disconnected():
                jpeg = await service.preview_jpeg()
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                await asyncio.sleep(PREVIEW_INTERVAL_S)

        return StreamingResponse(
            gen(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    return router


def create_qr_router(service: LiveSessionService) -> APIRouter:
    router = APIRouter(prefix="/api/photo-agent")

    @router.get("/qr/{photo_id}.png")
    def qr(photo_id: str) -> Response:
        url = service.download_url_for(photo_id)
        try:
            png = _render_qr_png(url)
        except Exception as exc:  # noqa: BLE001 - encoding boundary
            raise HTTPException(status_code=500, detail=f"二维码生成失败: {exc}") from exc
        return Response(content=png, media_type="image/png")

    return router
