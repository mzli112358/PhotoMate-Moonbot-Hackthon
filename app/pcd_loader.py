from __future__ import annotations

from pathlib import Path

import numpy as np

from app.config import MapBounds


def _parse_pcd_header(path: Path) -> tuple[dict[str, str], int]:
    header_lines: list[str] = []
    with path.open("rb") as f:
        while True:
            line = f.readline()
            if not line:
                break
            header_lines.append(line.decode("ascii", errors="ignore").strip())
            if line.strip().upper().startswith(b"DATA"):
                break
    fields: dict[str, str] = {}
    for line in header_lines:
        if " " not in line:
            continue
        key, val = line.split(" ", 1)
        fields[key.upper()] = val.strip()
    points = int(fields.get("POINTS", fields.get("WIDTH", "0")))
    return fields, points


def _point_stride(fields: dict[str, str]) -> int:
    sizes = [int(x) for x in fields.get("SIZE", "4").split()]
    counts = [int(x) for x in fields.get("COUNT", "1").split()]
    if len(sizes) != len(counts):
        sizes = [4] * len(fields.get("FIELDS", "x").split())
        counts = [1] * len(sizes)
    return sum(s * c for s, c in zip(sizes, counts))


def load_pcd_xyz(path: Path, max_points: int = 800_000) -> np.ndarray:
    """读取 PCD 的 x,y,z（支持 binary / ascii，多字段）。"""
    fields, n_points = _parse_pcd_header(path)
    data_type = fields.get("DATA", "binary").lower()
    field_names = fields.get("FIELDS", "x y z").split()
    try:
        xi = field_names.index("x")
        yi = field_names.index("y")
        zi = field_names.index("z")
    except ValueError as exc:
        raise ValueError(f"PCD 缺少 x/y/z 字段: {field_names}") from exc

    stride = _point_stride(fields)
    n_floats = stride // 4

    with path.open("rb") as f:
        while True:
            line = f.readline()
            if line.strip().upper().startswith(b"DATA"):
                break

        if data_type == "ascii":
            coords: list[list[float]] = []
            for _ in range(n_points):
                row = f.readline().decode("ascii", errors="ignore").strip()
                if not row:
                    continue
                parts = row.split()
                if len(parts) < len(field_names):
                    continue
                coords.append([float(parts[xi]), float(parts[yi]), float(parts[zi])])
            arr = np.asarray(coords, dtype=np.float64)
        else:
            raw = np.fromfile(f, dtype=np.float32)
            if raw.size < n_points * n_floats:
                usable = raw.size // n_floats
                raw = raw[: usable * n_floats]
            else:
                usable = n_points
                raw = raw[: usable * n_floats]
            mat = raw.reshape(-1, n_floats)
            arr = mat[:, [xi, yi, zi]].astype(np.float64)

    if arr.size == 0:
        raise ValueError("PCD 无有效点")

    # 去掉 NaN / Inf
    mask = np.isfinite(arr).all(axis=1)
    arr = arr[mask]
    if len(arr) > max_points:
        idx = np.linspace(0, len(arr) - 1, max_points, dtype=np.int64)
        arr = arr[idx]
    return arr


def bounds_from_xyz(xyz: np.ndarray, padding: float = 0.5) -> MapBounds:
    xmin, ymin = float(xyz[:, 0].min()), float(xyz[:, 1].min())
    xmax, ymax = float(xyz[:, 0].max()), float(xyz[:, 1].max())
    return MapBounds(
        xmin=xmin - padding,
        ymin=ymin - padding,
        xmax=xmax + padding,
        ymax=ymax + padding,
    )


def rasterize_xyz(
    xyz: np.ndarray,
    bounds: MapBounds,
    resolution: float,
    z_min: float = 0.05,
    z_max: float = 2.5,
    min_points_per_cell: int = 2,
) -> tuple[np.ndarray, list[float]]:
    """3D 点云 → 2D 占据栅格（255=可通行，0=障碍）。"""
    z = xyz[:, 2]
    mask = (z >= z_min) & (z <= z_max)
    pts = xyz[mask]
    if len(pts) == 0:
        pts = xyz

    width, height, origin = _grid_size(bounds, resolution)
    ix = ((pts[:, 0] - origin[0]) / resolution).astype(np.int64)
    iy = ((pts[:, 1] - origin[1]) / resolution).astype(np.int64)
    valid = (ix >= 0) & (ix < width) & (iy >= 0) & (iy < height)
    ix, iy = ix[valid], iy[valid]

    # 图像行 0 在顶部 → y 翻转
    rows = height - 1 - iy
    flat_idx = rows * width + ix
    counts = np.bincount(flat_idx, minlength=width * height)

    pixels = np.full(width * height, 255, dtype=np.uint8)
    occupied = counts >= min_points_per_cell
    pixels[occupied] = 0
    return pixels.reshape(height, width), origin


def _grid_size(bounds: MapBounds, resolution: float) -> tuple[int, int, list[float]]:
    width_m = bounds.xmax - bounds.xmin
    height_m = bounds.ymax - bounds.ymin
    width = max(1, int(np.ceil(width_m / resolution)))
    height = max(1, int(np.ceil(height_m / resolution)))
    return width, height, [bounds.xmin, bounds.ymin]
