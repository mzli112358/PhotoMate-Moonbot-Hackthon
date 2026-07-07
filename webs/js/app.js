const $ = (id) => document.getElementById(id);

let ws = null;
let waypoints = [];
let selectedSpotId = null;

function log(line) {
  const el = $("taskLog");
  const ts = new Date().toLocaleTimeString();
  el.textContent = `[${ts}] ${line}\n` + el.textContent.slice(0, 2000);
}

function fmtPose(pose) {
  if (!pose || pose.x == null) return "—";
  return `(${Number(pose.x).toFixed(2)}, ${Number(pose.y).toFixed(2)}) · ${Number(pose.yaw_deg || 0).toFixed(1)}°`;
}

function renderStatus(snap) {
  $("modeValue").textContent = snap.mock ? "演示 (mock)" : "Galbot 真机";
  $("localizedValue").textContent = snap.localized ? "已定位" : "未定位";
  $("navValue").textContent = snap.navigation_status || "—";
  $("poseValue").textContent = fmtPose(snap.pose);
  $("poseHint").textContent = snap.message || "—";
  PhotoMateMap.setLivePose(snap.pose, snap.target_spot_id);
  highlightActiveSpot(snap.target_spot_id);
}

function highlightActiveSpot(spotId) {
  document.querySelectorAll(".spot-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.spotId === spotId);
  });
}

function renderSpotList() {
  const list = $("spotList");
  list.innerHTML = "";
  waypoints.forEach((spot) => {
    const li = document.createElement("li");
    li.className = "spot-item";
    li.dataset.spotId = spot.id;
    const p = spot.pose || [];
    li.innerHTML = `
      <h3>${escapeHtml(spot.name)}</h3>
      <p>${escapeHtml(spot.description || "")}</p>
      <div class="coords">(${p[0]?.toFixed?.(2) ?? p[0]}, ${p[1]?.toFixed?.(2) ?? p[1]})</div>
      <button type="button" class="btn btn-primary btn-go">前往</button>
    `;
    li.querySelector(".btn-go").addEventListener("click", () => goToSpot(spot.id));
    list.appendChild(li);
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadWaypoints() {
  const res = await fetch("/api/waypoints");
  if (!res.ok) throw new Error("航点加载失败");
  waypoints = await res.json();
  PhotoMateMap.setWaypoints(waypoints);
  renderSpotList();
}

async function goToSpot(spotId) {
  selectedSpotId = spotId;
  log(`请求导航 → ${spotId}`);
  const res = await fetch("/api/navigation/go", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spot_id: spotId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    log(`失败: ${data.detail || res.status}`);
    alert(data.detail || "导航失败");
    return;
  }
  log(data.message || "已启动");
}

async function stopNav() {
  const res = await fetch("/api/navigation/stop", { method: "POST" });
  const data = await res.json();
  log(data.message || "已停止");
}

function connectWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/pose`);

  ws.onopen = () => {
    $("connStatus").textContent = "WebSocket 已连接";
    $("connStatus").className = "top-status ok";
    log("WebSocket 已连接");
  };

  ws.onmessage = (ev) => {
    try {
      const snap = JSON.parse(ev.data);
      renderStatus(snap);
    } catch (err) {
      console.warn(err);
    }
  };

  ws.onclose = () => {
    $("connStatus").textContent = "连接断开，3s 后重连…";
    $("connStatus").className = "top-status err";
    setTimeout(connectWs, 3000);
  };

  ws.onerror = () => {
    $("connStatus").className = "top-status err";
  };
}

function formatMapMeta(map) {
  const m = map.meta || {};
  const b = m.bounds || {};
  if (m.source === "pcd") {
    const n = m.point_count != null ? `${(m.point_count / 1000).toFixed(0)}k 点` : "PCD";
    const z = m.z_slice ? `z ${m.z_slice[0]}–${m.z_slice[1]}m` : "";
    return `点云 ${n} · ${z} · ${b.xmin?.toFixed(1)}~${b.xmax?.toFixed(1)} m`;
  }
  if (map.has_floor_plan) return "floor_plan.png";
  return `演示栅格 · ${b.xmin}~${b.xmax} m × ${b.ymin}~${b.ymax} m`;
}

async function boot() {
  PhotoMateMap.init($("mapCanvas"));
  try {
    const map = await PhotoMateMap.loadFromApi();
    $("mapMeta").textContent = formatMapMeta(map);
    await loadWaypoints();
    connectWs();
    log("Dashboard 就绪");
  } catch (err) {
    log(String(err.message || err));
    $("connStatus").textContent = "初始化失败";
    $("connStatus").className = "top-status err";
  }
}

$("btnStop").addEventListener("click", () => stopNav().catch((e) => alert(e.message)));

boot();
