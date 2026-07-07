from __future__ import annotations

import base64
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from app.config import ROOT_DIR, MapBounds, MapConfig
from app.pcd_loader import bounds_from_xyz, load_pcd_xyz, rasterize_xyz


def yaw_deg_from_quat(qx: float, qy: float, qz: float, qw: float) -> float:
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


def _bounds_size(bounds: MapBounds, resolution: float) -> tuple[int, int, list[float]]:
    width_m = bounds.xmax - bounds.xmin
    height_m = bounds.ymax - bounds.ymin
    width = max(1, int(math.ceil(width_m / resolution)))
    height = max(1, int(math.ceil(height_m / resolution)))
    origin = [bounds.xmin, bounds.ymin]
    return width, height, origin


def _raster_from_floor_plan(path: Path, bounds: MapBounds, resolution: float) -> tuple[np.ndarray, list[float]]:
    img = Image.open(path).convert("L")
    width, height, origin = _bounds_size(bounds, resolution)
    resized = img.resize((width, height), Image.Resampling.BILINEAR)
    arr = np.array(resized, dtype=np.uint8)
    pixels = np.where(arr > 180, 255, 0).astype(np.uint8)
    return pixels, origin


def _raster_demo_grid(bounds: MapBounds, resolution: float) -> tuple[np.ndarray, list[float]]:
    width, height, origin = _bounds_size(bounds, resolution)
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    step_px = max(1, int(1.0 / resolution))
    for x in range(0, width, step_px):
        draw.line([(x, 0), (x, height)], fill=230)
    for y in range(0, height, step_px):
        draw.line([(0, y), (width, y)], fill=230)
    draw.rectangle([width // 4, height // 3, width // 3, height // 2], fill=40)
    draw.rectangle([width * 2 // 3, height // 4, width * 5 // 6, height // 2], fill=40)
    arr = np.array(img, dtype=np.uint8)
    pixels = np.where(arr > 200, 255, 0).astype(np.uint8)
    return pixels, origin


def _map_cache_key(config: MapConfig) -> tuple:
    b = config.bounds
    pcd_path = ROOT_DIR / config.point_cloud
    png_path = ROOT_DIR / config.floor_plan
    return (
        config.point_cloud,
        config.floor_plan,
        config.resolution,
        config.z_min,
        config.z_max,
        config.auto_bounds,
        b.xmin,
        b.ymin,
        b.xmax,
        b.ymax,
        pcd_path.stat().st_mtime_ns if pcd_path.is_file() else 0,
        png_path.stat().st_mtime_ns if png_path.is_file() else 0,
    )


_map_cache: dict[tuple, dict] = {}


def build_map_payload(config: MapConfig) -> dict:
    key = _map_cache_key(config)
    if key in _map_cache:
        return _map_cache[key]

    resolution = config.resolution
    bounds = config.bounds
    source = "demo"
    point_count = 0

    pcd_path = ROOT_DIR / config.point_cloud
    floor_path = ROOT_DIR / config.floor_plan

    if pcd_path.is_file():
        xyz = load_pcd_xyz(pcd_path)
        point_count = len(xyz)
        if config.auto_bounds:
            bounds = bounds_from_xyz(xyz)
        pixels, origin = rasterize_xyz(
            xyz,
            bounds,
            resolution,
            z_min=config.z_min,
            z_max=config.z_max,
        )
        source = "pcd"
    elif floor_path.is_file():
        pixels, origin = _raster_from_floor_plan(floor_path, bounds, resolution)
        source = "png"
    else:
        pixels, origin = _raster_demo_grid(bounds, resolution)
        source = "demo"

    height, width = pixels.shape
    pgm_b64 = base64.b64encode(pixels.tobytes()).decode("ascii")

    result = {
        "meta": {
            "origin": origin,
            "resolution": resolution,
            "frame": "map",
            "bounds": {
                "xmin": bounds.xmin,
                "ymin": bounds.ymin,
                "xmax": bounds.xmax,
                "ymax": bounds.ymax,
            },
            "source": source,
            "point_cloud": config.point_cloud if source == "pcd" else None,
            "point_count": point_count if source == "pcd" else None,
            "z_slice": [config.z_min, config.z_max] if source == "pcd" else None,
        },
        "width": width,
        "height": height,
        "pgm_base64": pgm_b64,
        "has_floor_plan": source == "png",
        "has_point_cloud": source == "pcd",
    }
    _map_cache[key] = result
    return result


def clear_map_cache() -> None:
    _map_cache.clear()
