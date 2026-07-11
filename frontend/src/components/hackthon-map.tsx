import { useEffect, useMemo, useRef, useState } from "react";
import { useHackthonBridge, type RobotPose, type Waypoint } from "./hackthon-bridge";

type MapPayload = {
  width: number;
  height: number;
  pgm_base64: string;
  has_floor_plan?: boolean;
  meta: {
    origin: [number, number, number?];
    resolution: number;
    source?: string;
    point_count?: number;
    z_slice?: [number, number];
    bounds?: {
      xmin?: number;
      xmax?: number;
      ymin?: number;
      ymax?: number;
    };
  };
};

type MapState = {
  map: MapPayload;
  pixels: Uint8Array;
};

function decodeBase64(raw: string) {
  return Uint8Array.from(atob(raw), (char) => char.charCodeAt(0));
}

function yawRadFromPose(pose: RobotPose) {
  if (pose.yaw_deg != null) return (Number(pose.yaw_deg) * Math.PI) / 180;
  const { qx = 0, qy = 0, qz = 0, qw = 1 } = pose;
  const siny = 2 * (qw * qz + qx * qy);
  const cosy = 1 - 2 * (qy * qy + qz * qz);
  return Math.atan2(siny, cosy);
}

function formatMapMeta(map?: MapPayload) {
  if (!map) return "地图加载中";
  const meta = map.meta || {};
  const bounds = meta.bounds || {};
  if (meta.source === "pcd") {
    const count = meta.point_count != null ? `${(meta.point_count / 1000).toFixed(0)}k 点` : "PCD";
    const slice = meta.z_slice ? `z ${meta.z_slice[0]}-${meta.z_slice[1]}m` : "";
    return `点云 ${count} · ${slice} · ${bounds.xmin?.toFixed(1)}~${bounds.xmax?.toFixed(1)} m`;
  }
  if (map.has_floor_plan) return "floor_plan.png";
  return `演示栅格 · ${bounds.xmin}~${bounds.xmax} m x ${bounds.ymin}~${bounds.ymax} m`;
}

export function HackthonMap() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [mapState, setMapState] = useState<MapState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { activeSpotId, status, waypoints } = useHackthonBridge();

  useEffect(() => {
    let alive = true;
    fetch("/api/map")
      .then((res) => {
        if (!res.ok) throw new Error("地图加载失败");
        return res.json();
      })
      .then((map: MapPayload) => {
        if (alive) setMapState({ map, pixels: decodeBase64(map.pgm_base64) });
      })
      .catch((err) => {
        if (alive) setError(String(err.message || err));
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap || !mapState) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { map, pixels } = mapState;
    const worldToPixel = (wx: number, wy: number) => {
      const { origin, resolution } = map.meta;
      const px = (wx - origin[0]) / resolution - 0.5;
      const py = map.height - 1 - (wy - origin[1]) / resolution + 0.5;
      return { px, py };
    };

    const drawMapImage = () => {
      const offscreen = document.createElement("canvas");
      offscreen.width = map.width;
      offscreen.height = map.height;
      const offCtx = offscreen.getContext("2d");
      if (!offCtx) return;

      const imageData = offCtx.createImageData(map.width, map.height);
      for (let i = 0; i < pixels.length; i += 1) {
        const value = pixels[i];
        const target = i * 4;
        let shade = 140;
        if (value === 255) shade = 252;
        if (value === 0) shade = 30;
        imageData.data[target] = shade;
        imageData.data[target + 1] = shade;
        imageData.data[target + 2] = shade;
        imageData.data[target + 3] = 255;
      }
      offCtx.putImageData(imageData, 0, 0);
      ctx.drawImage(offscreen, 0, 0, map.width, map.height);
    };

    const drawWaypoint = (spot: Waypoint, scale: number) => {
      const pose = spot.pose;
      if (!pose || pose.length < 2) return;
      const { px, py } = worldToPixel(pose[0], pose[1]);
      const isTarget = spot.id === activeSpotId;
      const radius = (isTarget ? 10 : 7) / scale;

      ctx.fillStyle = isTarget ? "rgba(112, 54, 12, 0.35)" : "rgba(0, 0, 0, 0.08)";
      ctx.strokeStyle = isTarget ? "#b45309" : "#666";
      ctx.lineWidth = (isTarget ? 2.5 : 1.5) / scale;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.font = `${11 / scale}px sans-serif`;
      ctx.fillStyle = "#111";
      ctx.fillText(spot.name || spot.id, px + 8 / scale, py - 8 / scale);
    };

    const drawLiveRobot = (scale: number) => {
      const pose = status?.pose;
      if (!pose || pose.x == null || pose.y == null) return;
      const wx = Number(pose.x);
      const wy = Number(pose.y);
      const { px, py } = worldToPixel(wx, wy);
      const yaw = yawRadFromPose(pose);
      const tip = worldToPixel(wx + Math.cos(yaw) * 0.65, wy + Math.sin(yaw) * 0.65);

      ctx.strokeStyle = "#1a56db";
      ctx.fillStyle = "rgba(26, 86, 219, 0.25)";
      ctx.lineWidth = 3 / scale;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(tip.px, tip.py);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(px, py, 7 / scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#0f2d6e";
      ctx.lineWidth = 1.5 / scale;
      ctx.stroke();
    };

    const draw = () => {
      const pad = 16;
      const cw = wrap.clientWidth;
      const ch = wrap.clientHeight;
      canvas.width = cw;
      canvas.height = ch;

      const sx = (cw - pad * 2) / map.width;
      const sy = (ch - pad * 2) / map.height;
      const scale = Math.min(sx, sy, 5);
      const offsetX = (cw - map.width * scale) / 2;
      const offsetY = (ch - map.height * scale) / 2;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.translate(offsetX, offsetY);
      ctx.scale(scale, scale);
      drawMapImage();
      waypoints.forEach((spot) => drawWaypoint(spot, scale));
      drawLiveRobot(scale);
    };

    draw();
    const resizeObserver = new ResizeObserver(draw);
    resizeObserver.observe(wrap);
    return () => resizeObserver.disconnect();
  }, [activeSpotId, mapState, status?.pose, waypoints]);

  const meta = useMemo(() => formatMapMeta(mapState?.map), [mapState]);

  return (
    <section className="relative flex h-full min-h-[620px] flex-1 flex-col overflow-hidden rounded-[36px] border border-robot-hairline bg-robot-surface shadow-[0_30px_80px_-50px_rgba(20,15,10,0.5)]">
      <div className="flex items-center justify-between gap-4 border-b border-robot-hairline bg-white/70 px-6 py-4 backdrop-blur-sm">
        <div>
          <div className="text-[10px] font-semibold tracking-[0.22em] text-robot-orange">
            准备
          </div>
          <h1 className="mt-1 font-display text-xl font-medium text-robot-ink">会场地图</h1>
        </div>
        <span className="rounded-full border border-robot-hairline bg-white px-3 py-1.5 text-[11px] font-medium text-robot-muted">
          {meta}
        </span>
      </div>

      <div ref={wrapRef} className="relative min-h-0 flex-1">
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-label="地图与机器人位姿" />
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-robot-muted">
            {error}
          </div>
        )}
      </div>

      <p className="border-t border-robot-hairline bg-white/70 px-6 py-3 text-[12px] leading-relaxed text-robot-muted">
        蓝点为机器人当前位置，圆点为后端点位；地图由 /api/map 生成，位姿由 /ws/pose 实时更新。
      </p>
    </section>
  );
}
