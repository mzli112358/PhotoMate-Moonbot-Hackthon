from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"


class MapBounds(BaseModel):
    xmin: float = -5.0
    ymin: float = -5.0
    xmax: float = 8.0
    ymax: float = 8.0


class MapConfig(BaseModel):
    # 优先级：point_cloud > floor_plan > 演示栅格
    point_cloud: str = "data/maps/global_cloud.pcd"
    floor_plan: str = "data/maps/floor_plan.png"
    bounds: MapBounds = Field(default_factory=MapBounds)
    resolution: float = 0.05
    z_min: float = 0.05
    z_max: float = 2.5
    auto_bounds: bool = True


class RobotConfig(BaseModel):
    model: str = "g1"
    mock: bool = True


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class NavigationConfig(BaseModel):
    goal_timeout_sec: int = 60
    pose_poll_hz: float = 5.0


class AppYaml(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    robot: RobotConfig = Field(default_factory=RobotConfig)
    map: MapConfig = Field(default_factory=MapConfig)
    navigation: NavigationConfig = Field(default_factory=NavigationConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PHOTOMATE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    mock: bool | None = None
    robot_model: str | None = None


@lru_cache
def load_app_yaml() -> AppYaml:
    path = CONFIG_DIR / "app.yaml"
    if not path.exists():
        return AppYaml()
    with path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return AppYaml.model_validate(raw)


@lru_cache
def load_waypoints() -> dict[str, Any]:
    path = CONFIG_DIR / "waypoints.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_settings() -> tuple[AppYaml, Settings]:
    app_yaml = load_app_yaml()
    env = Settings()
    if env.mock is not None:
        app_yaml.robot.mock = env.mock
    if env.robot_model:
        app_yaml.robot.model = env.robot_model
    return app_yaml, env
