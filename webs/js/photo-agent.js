const API = "/api/photo-agent";

const appState = {
  schema: null,
  selected: "S1",
  status: {},
  promptSnapshot: null,
  originalPrompts: {},
  showAll: false,
  lastEventId: 0,
};

const $ = (id) => document.getElementById(id);

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `请求失败 (${response.status})`);
  }
  return response.json();
}

function toast(message) {
  const node = $("toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2400);
}

function renderStates() {
  $("stateRail").innerHTML = appState.schema.states.map((state) => `
    <button class="state-card ${state.id === appState.selected ? "active" : ""} ${appState.status.active && appState.status.selected_state === state.id ? "running" : ""}" data-state="${state.id}">
      <span class="num">FRAME / ${state.id}</span>
      <b>${state.title}</b>
      <small>${state.role.split("，")[0]}</small>
    </button>
  `).join("");
  document.querySelectorAll(".state-card").forEach((button) => {
    button.addEventListener("click", () => selectState(button.dataset.state));
  });
}

function selectState(stateId) {
  appState.selected = stateId;
  const state = appState.schema.states.find((item) => item.id === stateId);
  $("activeStateTitle").textContent = `${state.id} · ${state.title}`;
  $("stateRole").textContent = state.role;
  renderStates();
  renderPrompts();
}

function visiblePromptDefinitions() {
  if (appState.showAll) return appState.schema.prompts;
  return appState.schema.prompts.filter((item) => {
    if (item.key === "system.base") return true;
    if (appState.selected === "S1") return item.key === "action.tool.followup";
    return item.state === appState.selected;
  });
}

function promptTitle(definition) {
  if (definition.key === "system.base") return "GLOBAL SYSTEM PROMPT";
  if (definition.kind === "state") return `${definition.state} CONTEXT`;
  return definition.key.replace("action.", "ACTION / ").toUpperCase();
}

function renderPrompts() {
  if (!appState.promptSnapshot) return;
  const form = $("promptForm");
  form.innerHTML = visiblePromptDefinitions().map((definition) => `
    <label class="prompt-field ${definition.kind === "system" ? "system" : ""}">
      <span><b>${promptTitle(definition)}</b><em>${definition.key}</em></span>
      <textarea data-prompt-key="${definition.key}" spellcheck="false"></textarea>
    </label>
  `).join("");
  form.querySelectorAll("textarea").forEach((textarea) => {
    textarea.value = appState.promptSnapshot.prompts[textarea.dataset.promptKey] || "";
    textarea.addEventListener("input", onPromptInput);
  });
  updateDirtyState();
}

function collectVisiblePrompts() {
  return Object.fromEntries([...document.querySelectorAll("[data-prompt-key]")].map((node) => [node.dataset.promptKey, node.value]));
}

function onPromptInput(event) {
  appState.promptSnapshot.prompts[event.target.dataset.promptKey] = event.target.value;
  updateDirtyState();
}

function changedPrompts() {
  return Object.fromEntries(Object.entries(appState.promptSnapshot.prompts).filter(([key, value]) => value !== appState.originalPrompts[key]));
}

function updateDirtyState() {
  const dirty = Object.keys(changedPrompts()).length > 0;
  $("dirtyBadge").textContent = dirty ? "未保存" : "已保存";
  $("dirtyBadge").classList.toggle("dirty", dirty);
  $("savePrompts").disabled = !dirty;
}

async function savePrompts() {
  const updates = changedPrompts();
  if (!Object.keys(updates).length) return;
  try {
    const saved = await request("/prompts", {
      method: "PUT",
      body: JSON.stringify({ expected_version: appState.promptSnapshot.version, updates }),
    });
    appState.promptSnapshot = saved;
    appState.originalPrompts = { ...saved.prompts };
    $("savedVersion").textContent = saved.version;
    renderPrompts();
    toast("Prompt 已保存；下一轮对话生效");
    await refreshStatus();
  } catch (error) {
    toast(error.message.includes("version") ? "版本冲突，请刷新后重试" : error.message);
  }
}

function numberOrNull(id) {
  const value = $(id).value.trim();
  return value === "" ? null : Number(value);
}

async function startTest() {
  try {
    await request(`/tests/${appState.selected}/start`, {
      method: "POST",
      body: JSON.stringify({
        camera_index: numberOrNull("cameraIndex"),
        microphone_index: numberOrNull("microphoneIndex"),
        speaker_index: numberOrNull("speakerIndex"),
      }),
    });
    toast(`${appState.selected} 真实测试已启动`);
    await refreshStatus();
  } catch (error) { toast(error.message); }
}

async function stopTest() {
  try {
    await request("/tests/stop", { method: "POST", body: "{}" });
    toast("测试已停止，设备已释放");
    await Promise.all([refreshStatus(), loadRuns()]);
  } catch (error) { toast(error.message); }
}

function renderStatus() {
  const status = appState.status;
  $("runtimeBadge").textContent = status.active ? "● LIVE" : "IDLE";
  $("runtimeBadge").classList.toggle("live", Boolean(status.active));
  $("startButton").disabled = Boolean(status.active);
  $("stopButton").disabled = !status.active;
  $("vfState").textContent = `STATE ${status.runtime_state || status.selected_state || "—"}`;
  const quality = status.last_quality;
  $("vfQuality").textContent = `QUALITY ${quality ? (quality.ok ? "PASS" : "RETRY") : "—"}`;
  $("savedVersion").textContent = status.saved_prompt_version || appState.promptSnapshot?.version || "—";
  $("activeVersion").textContent = status.active_prompt_version || "等待会话";
  const devices = status.devices || {};
  $("deviceInfo").textContent = Object.keys(devices).length
    ? Object.entries(devices).map(([key, value]) => `${key.toUpperCase()}: ${value}`).join("  ·  ")
    : "设备将在测试启动后显示";
  renderStates();
}

async function refreshStatus() {
  try {
    appState.status = await request("/status");
    $("connectionBadge").classList.add("online");
    $("connectionBadge").lastChild.textContent = "已连接";
    renderStatus();
  } catch (error) {
    $("connectionBadge").classList.remove("online");
    $("connectionBadge").lastChild.textContent = "服务离线";
  }
}

function addLog(event) {
  const stream = $("logStream");
  const line = document.createElement("div");
  line.className = "log-line";
  const time = new Date(event.ts || Date.now()).toLocaleTimeString("zh-CN", { hour12: false });
  const details = { ...event };
  delete details.ts; delete details.seq; delete details.type;
  line.innerHTML = `<time>${time}</time><b>${event.type || "event"}</b><span></span>`;
  line.querySelector("span").textContent = JSON.stringify(details);
  stream.appendChild(line);
  while (stream.children.length > 200) stream.firstChild.remove();
  stream.scrollTop = stream.scrollHeight;
}

function connectEvents() {
  const source = new EventSource(`${API}/events?after=${appState.lastEventId}`);
  source.onmessage = async (message) => {
    const event = JSON.parse(message.data);
    appState.lastEventId = event.seq || appState.lastEventId;
    addLog(event);
    await refreshStatus();
    if (["test_completed", "test_failed", "test_stopped"].includes(event.type)) loadRuns();
  };
  source.onerror = () => source.close();
}

async function loadRuns() {
  const list = $("runList");
  try {
    const runs = await request("/runs");
    list.innerHTML = runs.length ? runs.slice(0, 8).map((run) => `
      <div class="run-item"><b>${run.state}</b><span>${new Date(run.finished_at).toLocaleString("zh-CN", { hour12: false })}</span><em>${run.stop_reason || "—"}</em></div>
    `).join("") : `<div class="empty">暂无测试记录</div>`;
  } catch { list.innerHTML = `<div class="empty">记录读取失败</div>`; }
}

async function openHistory() {
  try {
    const versions = await request("/prompts/history");
    $("historyList").innerHTML = versions.map((item, index) => `
      <div class="history-item"><div><code>${item.version}${index === 0 ? " · CURRENT" : ""}</code><small>${item.updated_at}</small></div>${index ? `<div class="history-actions"><button data-diff="${item.version}">查看差异</button><button data-rollback="${item.version}">回滚到此版本</button></div>` : ""}</div>
    `).join("");
    $("historyDiff").textContent = "选择历史版本查看与当前版本的差异";
    document.querySelectorAll("[data-diff]").forEach((button) => button.addEventListener("click", () => showDiff(button.dataset.diff)));
    document.querySelectorAll("[data-rollback]").forEach((button) => button.addEventListener("click", () => rollback(button.dataset.rollback)));
    $("historyDialog").showModal();
  } catch (error) { toast(error.message); }
}

async function showDiff(version) {
  try {
    const diff = await request(`/prompts/diff?before=${encodeURIComponent(version)}&after=${encodeURIComponent(appState.promptSnapshot.version)}`);
    const entries = Object.entries(diff);
    $("historyDiff").textContent = entries.length ? entries.map(([key, value]) => `${key}\n− ${value.before}\n+ ${value.after}`).join("\n\n") : "两个版本没有内容差异";
  } catch (error) { toast(error.message); }
}

async function rollback(version) {
  if (!window.confirm(`确认回滚到 ${version}？当前版本仍会保留在历史中。`)) return;
  try {
    const snapshot = await request(`/prompts/${version}/rollback`, {
      method: "POST",
      body: JSON.stringify({ expected_version: appState.promptSnapshot.version }),
    });
    appState.promptSnapshot = snapshot;
    appState.originalPrompts = { ...snapshot.prompts };
    renderPrompts();
    $("historyDialog").close();
    toast("已创建一个回滚版本");
    refreshStatus();
  } catch (error) { toast(error.message); }
}

async function init() {
  try {
    [appState.schema, appState.promptSnapshot] = await Promise.all([request("/schema"), request("/prompts")]);
    appState.originalPrompts = { ...appState.promptSnapshot.prompts };
    selectState("S1");
    await Promise.all([refreshStatus(), loadRuns()]);
    connectEvents();
  } catch (error) { toast(`初始化失败：${error.message}`); }
}

$("startButton").addEventListener("click", startTest);
$("stopButton").addEventListener("click", stopTest);
$("savePrompts").addEventListener("click", savePrompts);
$("showAllPrompts").addEventListener("click", () => {
  appState.showAll = !appState.showAll;
  $("showAllPrompts").textContent = appState.showAll ? "只显示当前模块" : "显示全部 Prompt";
  renderPrompts();
});
$("historyButton").addEventListener("click", openHistory);
$("closeHistory").addEventListener("click", () => $("historyDialog").close());
$("clearLogs").addEventListener("click", () => { $("logStream").innerHTML = ""; });
window.addEventListener("beforeunload", (event) => {
  if (Object.keys(changedPrompts()).length) { event.preventDefault(); event.returnValue = ""; }
});

init();
setInterval(refreshStatus, 2000);
