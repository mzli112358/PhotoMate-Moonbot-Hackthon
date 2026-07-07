/**
 * 地图画布：栅格底图 + 航点 + 机器人位姿（点 + 朝向线）
 */
const PhotoMateMap = (() => {
  const state = {
    meta: null,
    width: 0,
    height: 0,
    pixels: null,
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    livePose: null,
    waypoints: [],
    targetSpotId: null,
  };

  let canvas = null;
  let ctx = null;

  function init(canvasEl) {
    canvas = canvasEl;
    ctx = canvas.getContext("2d");
    window.addEventListener("resize", fitToView);
  }

  function worldToPixel(wx, wy) {
    const { origin, resolution } = state.meta;
    const px = (wx - origin[0]) / resolution - 0.5;
    const py = state.height - 1 - (wy - origin[1]) / resolution + 0.5;
    return { px, py };
  }

  function yawRadFromPose(pose) {
    if (pose.yaw_deg != null) return (Number(pose.yaw_deg) * Math.PI) / 180;
    const { qx = 0, qy = 0, qz = 0, qw = 1 } = pose;
    const siny = 2 * (qw * qz + qx * qy);
    const cosy = 1 - 2 * (qy * qy + qz * qz);
    return Math.atan2(siny, cosy);
  }

  function setWaypoints(waypoints) {
    state.waypoints = waypoints || [];
    draw();
  }

  function setLivePose(pose, targetSpotId) {
    state.livePose = pose;
    state.targetSpotId = targetSpotId || null;
    draw();
  }

  async function loadFromApi() {
    const res = await fetch("/api/map");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "地图加载失败");
    }
    const map = await res.json();
    state.meta = map.meta;
    state.width = map.width;
    state.height = map.height;
    state.pixels = Uint8Array.from(atob(map.pgm_base64), (c) => c.charCodeAt(0));
    fitToView();
    return map;
  }

  function drawMapImage() {
    if (!state.pixels) return;
    const off = document.createElement("canvas");
    off.width = state.width;
    off.height = state.height;
    const offCtx = off.getContext("2d");
    const imageData = offCtx.createImageData(state.width, state.height);
    for (let i = 0; i < state.pixels.length; i += 1) {
      const v = state.pixels[i];
      const j = i * 4;
      let r;
      let g;
      let b;
      if (v === 255) {
        r = g = b = 252;
      } else if (v === 0) {
        r = g = b = 30;
      } else {
        r = g = b = 140;
      }
      imageData.data[j] = r;
      imageData.data[j + 1] = g;
      imageData.data[j + 2] = b;
      imageData.data[j + 3] = 255;
    }
    offCtx.putImageData(imageData, 0, 0);
    ctx.drawImage(off, 0, 0, state.width, state.height);
  }

  function drawWaypoint(spot, isTarget) {
    const pose = spot.pose;
    if (!pose || pose.length < 2) return;
    const { px, py } = worldToPixel(pose[0], pose[1]);
    const r = (isTarget ? 10 : 7) / state.scale;

    ctx.fillStyle = isTarget ? "rgba(180, 83, 9, 0.35)" : "rgba(0, 0, 0, 0.08)";
    ctx.strokeStyle = isTarget ? "#b45309" : "#666";
    ctx.lineWidth = (isTarget ? 2.5 : 1.5) / state.scale;
    ctx.beginPath();
    ctx.arc(px, py, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    const fontSize = 11 / state.scale;
    ctx.font = `${fontSize}px sans-serif`;
    ctx.fillStyle = "#111";
    ctx.fillText(spot.name || spot.id, px + 8 / state.scale, py - 8 / state.scale);
  }

  function drawLiveRobot() {
    const pose = state.livePose;
    if (!pose || pose.x == null) return;
    const wx = Number(pose.x);
    const wy = Number(pose.y);
    const { px, py } = worldToPixel(wx, wy);
    const yaw = yawRadFromPose(pose);
    const tip = worldToPixel(wx + Math.cos(yaw) * 0.65, wy + Math.sin(yaw) * 0.65);

    ctx.strokeStyle = "#1a56db";
    ctx.fillStyle = "rgba(26, 86, 219, 0.25)";
    ctx.lineWidth = 3 / state.scale;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(tip.px, tip.py);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(px, py, 7 / state.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#0f2d6e";
    ctx.lineWidth = 1.5 / state.scale;
    ctx.stroke();
  }

  function draw() {
    if (!state.width || !ctx) return;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(state.offsetX, state.offsetY);
    ctx.scale(state.scale, state.scale);
    drawMapImage();
    state.waypoints.forEach((spot) => {
      drawWaypoint(spot, spot.id === state.targetSpotId);
    });
    drawLiveRobot();
    ctx.restore();
  }

  function fitToView() {
    if (!state.width || !state.height || !canvas) return;
    const wrap = canvas.parentElement;
    const pad = 12;
    const cw = wrap.clientWidth;
    const ch = wrap.clientHeight;
    canvas.width = cw;
    canvas.height = ch;
    const sx = (cw - pad * 2) / state.width;
    const sy = (ch - pad * 2) / state.height;
    state.scale = Math.min(sx, sy, 5);
    state.offsetX = (cw - state.width * state.scale) / 2;
    state.offsetY = (ch - state.height * state.scale) / 2;
    draw();
  }

  return {
    init,
    loadFromApi,
    setWaypoints,
    setLivePose,
    fitToView,
  };
})();
