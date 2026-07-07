from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PoseOut(BaseModel):
    x: float
    y: float
    z: float = 0.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0
    qw: float = 1.0
    yaw_deg: float
    frame_id: str = "map"


class RobotStatusOut(BaseModel):
    mock: bool
    localized: bool
    navigation_status: str
    pose: PoseOut | None
    target_spot_id: str | None = None
    message: str = ""


class WaypointOut(BaseModel):
    id: str
    name: str
    description: str = ""
    pose: list[float]


class NavigateRequest(BaseModel):
    spot_id: str


class MapMetaOut(BaseModel):
    origin: list[float]
    resolution: float
    frame: str = "map"
    bounds: dict[str, float]
    source: str | None = None
    point_cloud: str | None = None
    point_count: int | None = None
    z_slice: list[float] | None = None


class MapOut(BaseModel):
    meta: MapMetaOut
    width: int
    height: int
    pgm_base64: str
    has_floor_plan: bool = False
    has_point_cloud: bool = False


class TaskOut(BaseModel):
    ok: bool
    message: str
    spot_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class PatrolRequest(BaseModel):
    loop: bool = True


class PatrolThroughRequest(BaseModel):
    spot_ids: list[str] = Field(default_factory=list)


class AgentStartRequest(BaseModel):
    shoot_mode: str = "phone"
    spot_id: str | None = None
    loop_patrol: bool = True


class AgentConfirmRequest(BaseModel):
    accept: bool = True
    spot_id: str | None = None
