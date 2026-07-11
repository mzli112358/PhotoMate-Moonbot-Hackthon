"""Local-only HTTP API for the Photo Agent visual test console."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.photo_agent.prompts import (
    PROMPT_DEFINITIONS,
    PromptConflictError,
    PromptSnapshot,
    PromptValidationError,
)
from app.photo_agent.test_controller import TestAlreadyRunningError, PREVIEW_FRAME_INTERVAL_S


STATE_DEFINITIONS = (
    {"id": "S1", "title": "发现用户", "role": "本地视觉检测 + 启动 Omni 会话"},
    {"id": "S2", "title": "询问意愿", "role": "Omni 询问并理解用户是否想拍照"},
    {"id": "S3", "title": "姿态引导与拍照", "role": "Omni 引导姿态，达标后 capture_photo 拍照并播报"},
    {"id": "S5", "title": "照片复核", "role": "展示照片，Omni 询问是否满意"},
    {"id": "S6", "title": "交付照片", "role": "生成本地取图链接，Omni 完成交付说明"},
)


class StartTestBody(BaseModel):
    camera_index: int | None = Field(default=None, ge=0)
    microphone_index: int | None = Field(default=None, ge=0)
    speaker_index: int | None = Field(default=None, ge=0)


class SavePromptsBody(BaseModel):
    expected_version: str
    updates: dict[str, str]


class RollbackBody(BaseModel):
    expected_version: str


def _snapshot(snapshot: PromptSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def _require_local(request: Request) -> None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded or (request.client.host if request.client else "")
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Photo Agent test console is local-only")


def create_test_console_router(controller: Any) -> APIRouter:
    router = APIRouter(prefix="/api/photo-agent", dependencies=[])

    @router.get("/schema")
    def schema(request: Request) -> dict[str, Any]:
        _require_local(request)
        return {"states": STATE_DEFINITIONS, "prompts": PROMPT_DEFINITIONS}

    @router.get("/status")
    def status(request: Request) -> dict[str, Any]:
        _require_local(request)
        return controller.status()

    @router.post("/tests/{state}/start")
    async def start_test(state: str, body: StartTestBody, request: Request) -> dict[str, Any]:
        _require_local(request)
        try:
            return await controller.start(state.upper(), **body.model_dump())
        except TestAlreadyRunningError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"音频设备不可用: {exc}。"
                    "请清空 MIC/SPEAKER INDEX 使用自动选择，"
                    "或确认 index 对应正确的输入/输出设备。"
                ),
            ) from exc

    @router.post("/tests/stop")
    async def stop_test(request: Request) -> dict[str, Any]:
        _require_local(request)
        return await controller.stop()

    @router.get("/prompts")
    def prompts(request: Request) -> dict[str, Any]:
        _require_local(request)
        return _snapshot(controller.prompt_registry.snapshot())

    @router.put("/prompts")
    def save_prompts(body: SavePromptsBody, request: Request) -> dict[str, Any]:
        _require_local(request)
        try:
            saved = controller.prompt_registry.save(
                body.updates, expected_version=body.expected_version
            )
        except PromptConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PromptValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _snapshot(saved)

    @router.get("/prompts/history")
    def prompt_history(request: Request) -> list[dict[str, Any]]:
        _require_local(request)
        return [_snapshot(item) for item in controller.prompt_registry.history()]

    @router.get("/prompts/diff")
    def prompt_diff(request: Request, before: str = Query(), after: str = Query()) -> dict:
        _require_local(request)
        try:
            return controller.prompt_registry.diff(before, after)
        except PromptValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/prompts/{version}/rollback")
    def rollback_prompt(version: str, body: RollbackBody, request: Request) -> dict[str, Any]:
        _require_local(request)
        try:
            saved = controller.prompt_registry.rollback(
                version, expected_version=body.expected_version
            )
        except PromptConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PromptValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _snapshot(saved)

    @router.get("/runs")
    def runs(request: Request) -> list[dict[str, Any]]:
        _require_local(request)
        return controller.run_store.list()

    @router.get("/events")
    async def events(request: Request, after: int = Query(default=0, ge=0)) -> StreamingResponse:
        _require_local(request)

        async def stream() -> AsyncIterator[str]:
            async for event in controller.events.subscribe(after=after):
                if await request.is_disconnected():
                    break
                yield f"id: {event['seq']}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/preview.mjpg")
    async def preview(request: Request) -> StreamingResponse:
        _require_local(request)

        async def stream() -> AsyncIterator[bytes]:
            while not await request.is_disconnected():
                jpeg = await controller.preview_jpeg()
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                await asyncio.sleep(PREVIEW_FRAME_INTERVAL_S)

        return StreamingResponse(
            stream(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    return router
