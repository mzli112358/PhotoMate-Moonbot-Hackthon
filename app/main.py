from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import CONFIG_DIR, DATA_DIR, resolve_settings
from app.docs_service import catalog as docs_catalog
from app.docs_service import load_document
from app.map_loader import build_map_payload, clear_map_cache
from app.photo_agent.api import create_photo_router
from app.photo_agent.delivery import GLOBAL_PHOTO_STORE
from app.photo_agent.config import load_runtime_config
from app.photo_agent.prompts import PromptRegistry
from app.photo_agent.runtime import build_local_runtime
from app.photo_agent.test_console_api import create_test_console_router
from app.photo_agent.test_controller import PhotoAgentTestController, TestRunStore
from app.perception import PerceptionConfig
from app.robot import RobotBridge
from app.schemas import (
    AgentConfirmRequest,
    AgentStartRequest,
    MapOut,
    NavigateRequest,
    PatrolRequest,
    PatrolThroughRequest,
    RobotStatusOut,
    TaskOut,
    WaypointOut,
)
from app.task_fsm import PhotoMateFSM

WEBS_DIR = Path(__file__).resolve().parents[1] / "webs"
app_yaml, _ = resolve_settings()
robot_bridge = RobotBridge(app_yaml)


def _perception_config() -> PerceptionConfig:
    import yaml

    path = Path(__file__).resolve().parents[1] / "config" / "app.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    p = raw.get("perception") or {}
    return PerceptionConfig(
        loiter_threshold_sec=float(p.get("loiter_threshold_sec", 3.0)),
        approach_distance_m=float(p.get("approach_distance_m", 2.5)),
        mock_signal_interval_sec=float(p.get("mock_signal_interval_sec", 25.0)),
        enabled=bool(p.get("enabled", True)),
    )


task_agent = PhotoMateFSM(
    perception=_perception_config(),
    mock=robot_bridge.is_mock,
    on_start_patrol=lambda: robot_bridge.start_patrol(loop=True),
    on_stop_patrol=robot_bridge.stop_patrol,
    on_navigate=lambda sid: robot_bridge.navigate_to_spot(sid),
    on_speak=lambda text: None,  # 7/9 接 TTS
)

robot_bridge.set_on_arrived(task_agent.on_navigation_arrived)

photo_agent_prompts = PromptRegistry(
    CONFIG_DIR / "photo_agent_prompts.yaml",
    DATA_DIR / "photo_agent" / "prompt_history",
)
photo_agent_test_controller = PhotoAgentTestController(
    prompt_registry=photo_agent_prompts,
    run_store=TestRunStore(DATA_DIR / "photo_agent" / "test_runs.json"),
    config_loader=load_runtime_config,
    runtime_builder=build_local_runtime,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await photo_agent_test_controller.stop()
    robot_bridge.shutdown()


app = FastAPI(
    title="PhotoMate",
    description="拍照机器人控制台",
    version="0.1.0",
    lifespan=lifespan,
    # 嘉宾文档页占用 /docs；Swagger 改到 /api/swagger
    docs_url="/api/swagger",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.include_router(create_photo_router(GLOBAL_PHOTO_STORE))
app.include_router(create_test_console_router(photo_agent_test_controller))


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "mock": robot_bridge.is_mock}


@app.get("/api/robot/status", response_model=RobotStatusOut)
def robot_status() -> RobotStatusOut:
    return RobotStatusOut(**robot_bridge.status_snapshot())


@app.get("/api/waypoints", response_model=list[WaypointOut])
def waypoints() -> list[WaypointOut]:
    items = []
    for spot in robot_bridge.list_spots():
        items.append(
            WaypointOut(
                id=spot["id"],
                name=spot.get("name", spot["id"]),
                description=spot.get("description", ""),
                pose=spot["pose"],
            )
        )
    return items


@app.get("/api/map", response_model=MapOut)
def get_map() -> MapOut:
    payload = build_map_payload(app_yaml.map)
    return MapOut(**payload)


@app.post("/api/map/reload")
def reload_map() -> dict:
    clear_map_cache()
    return {"ok": True}


@app.post("/api/navigation/go", response_model=TaskOut)
def navigation_go(body: NavigateRequest) -> TaskOut:
    result = robot_bridge.navigate_to_spot(body.spot_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return TaskOut(**result)


@app.post("/api/navigation/stop", response_model=TaskOut)
def navigation_stop() -> TaskOut:
    robot_bridge.stop_patrol()
    robot_bridge.stop_navigation()
    return TaskOut(ok=True, message="已发送停止")


@app.post("/api/navigation/patrol/start", response_model=TaskOut)
def patrol_start(body: PatrolRequest) -> TaskOut:
    result = robot_bridge.start_patrol(loop=body.loop)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return TaskOut(ok=True, message=result.get("message", ""), detail=result)


@app.post("/api/navigation/patrol/stop", response_model=TaskOut)
def patrol_stop() -> TaskOut:
    robot_bridge.stop_patrol()
    return TaskOut(ok=True, message="巡航已停止")


@app.post("/api/navigation/through", response_model=TaskOut)
def navigation_through(body: PatrolThroughRequest) -> TaskOut:
    spot_ids = body.spot_ids
    if not spot_ids:
        spot_ids = robot_bridge.patrol_spot_ids()
    result = robot_bridge.navigate_through_spots(spot_ids)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return TaskOut(ok=True, message=result.get("message", ""), detail=result)


@app.get("/api/task/status")
def task_status() -> dict:
    snap = task_agent.snapshot()
    snap["robot"] = robot_bridge.status_snapshot()
    return snap


@app.post("/api/task/agent/start", response_model=TaskOut)
def agent_start(body: AgentStartRequest) -> TaskOut:
    result = task_agent.start_patrol_mode(
        shoot_mode=body.shoot_mode,
        spot_id=body.spot_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return TaskOut(ok=True, message=result.get("message", ""), detail=result)


@app.post("/api/task/agent/stop", response_model=TaskOut)
def agent_stop() -> TaskOut:
    result = task_agent.stop()
    return TaskOut(ok=True, message=result.get("message", ""))


@app.post("/api/task/guest/confirm", response_model=TaskOut)
def guest_confirm(body: AgentConfirmRequest) -> TaskOut:
    result = task_agent.confirm_guest(accept=body.accept, spot_id=body.spot_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return TaskOut(ok=True, message=result.get("message", ""), detail=result)


@app.post("/api/task/guest/request-photo", response_model=TaskOut)
def guest_request_photo() -> TaskOut:
    result = task_agent.notify_web_photo_request()
    return TaskOut(ok=True, message=result.get("message", ""))


@app.get("/api/perception/snapshot")
def perception_snapshot() -> dict:
    obs = task_agent.detector.poll()
    return {
        "signal": obs.signal.value,
        "confidence": obs.confidence,
        "person_count": obs.person_count,
        "dwell_sec": obs.dwell_sec,
        "message": obs.message,
        "source": obs.source,
    }


@app.websocket("/ws/pose")
async def ws_pose(websocket: WebSocket) -> None:
    await websocket.accept()
    hz = app_yaml.navigation.pose_poll_hz

    async def push(snap: dict) -> None:
        await websocket.send_json(snap)

    try:
        await robot_bridge.pose_stream(push, hz=hz)
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return


@app.get("/api/docs/catalog")
def get_docs_catalog() -> list:
    return docs_catalog()


@app.get("/api/docs/{doc_id}")
def get_doc(doc_id: str) -> dict:
    try:
        return load_document(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="源文件缺失") from exc


@app.get("/docs")
def docs_page() -> FileResponse:
    return FileResponse(WEBS_DIR / "docs.html")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEBS_DIR / "index.html")


@app.get("/photo-agent")
def photo_agent_page() -> FileResponse:
    return FileResponse(WEBS_DIR / "photo-agent.html")


app.mount("/assets", StaticFiles(directory=WEBS_DIR), name="assets")
