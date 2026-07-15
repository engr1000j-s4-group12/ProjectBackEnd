const storageKey = "longbin-flow-lab-logs";

const state = {
  imageFile: null,
  logs: loadLogs(),
  currentLocation: null,
  lastPayload: {
    hint: "在左侧输入文本、照片或参数，然后点击按钮发送请求。",
  },
  lastResponse: {
    hint: "响应会显示在这里。",
  },
  routeSteps: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const els = {
  utterance: $("#utterance"),
  fromLocation: $("#fromLocation"),
  toLocation: $("#toLocation"),
  floorHint: $("#floorHint"),
  language: $("#language"),
  accessibleOnly: $("#accessibleOnly"),
  recognizedTexts: $("#recognizedTexts"),
  objects: $("#objects"),
  sceneDescription: $("#sceneDescription"),
  imageFile: $("#imageFile"),
  imageMeta: $("#imageMeta"),
  imagePreview: $("#imagePreview"),
  dropZone: $("#dropZone"),
  exhibitId: $("#exhibitId"),
  question: $("#question"),
  payloadView: $("#payloadView"),
  responseView: $("#responseView"),
  routeSteps: $("#routeSteps"),
  logList: $("#logList"),
  logCount: $("#logCount"),
  healthBadge: $("#healthBadge"),
  placesBadge: $("#placesBadge"),
  currentLocation: $("#currentLocation"),
  localizeSummary: $("#localizeSummary"),
  routeSummary: $("#routeSummary"),
  lastEndpoint: $("#lastEndpoint"),
  placeOptions: $("#placeOptions"),
};

function loadLogs() {
  try {
    const raw = localStorage.getItem(storageKey);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLogs() {
  localStorage.setItem(storageKey, JSON.stringify(state.logs.slice(0, 200)));
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function nowLabel() {
  return new Date().toLocaleString("zh-CN", { hour12: false });
}

function setBadge(element, text, kind) {
  element.textContent = text;
  element.classList.remove("status-muted", "status-ok", "status-warn", "status-bad");
  element.classList.add(`status-${kind}`);
}

function setNode(node, mode, detail) {
  const card = document.querySelector(`[data-node="${node}"]`);
  if (!card) return;
  card.classList.remove("active", "ok", "error");
  if (mode) card.classList.add(mode);
  if (detail) {
    const code = card.querySelector("code");
    code.textContent = detail.length > 34 ? `${detail.slice(0, 31)}...` : detail;
  }
}

function resetActiveNodes() {
  $$(".module-card").forEach((node) => {
    node.classList.remove("active", "error");
  });
}

function updateInspector(payload = state.lastPayload, response = state.lastResponse) {
  state.lastPayload = payload;
  state.lastResponse = response;
  els.payloadView.textContent = pretty(payload);
  els.responseView.textContent = pretty(response);
}

function renderRouteSteps(steps) {
  state.routeSteps = steps || [];
  els.routeSteps.textContent = "";
  if (!state.routeSteps.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无路线步骤。";
    els.routeSteps.appendChild(empty);
    return;
  }
  state.routeSteps.forEach((step) => {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = `${step.from_id} -> ${step.to_id} (${step.distance_m}m)`;
    const text = document.createElement("div");
    text.textContent = step.instruction;
    item.append(title, text);
    els.routeSteps.appendChild(item);
  });
}

function addLog(entry) {
  const normalized = {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    at: nowLabel(),
    ...entry,
  };
  state.logs.unshift(normalized);
  state.logs = state.logs.slice(0, 200);
  saveLogs();
  renderLogs();
}

function renderLogs() {
  els.logList.textContent = "";
  els.logCount.textContent = `${state.logs.length} 条`;

  if (!state.logs.length) {
    const empty = document.createElement("div");
    empty.className = "log-item";
    empty.textContent = "暂无通信记录。";
    els.logList.appendChild(empty);
    return;
  }

  state.logs.forEach((entry) => {
    const row = document.createElement("button");
    row.className = "log-item";
    row.type = "button";
    row.addEventListener("click", () => {
      updateInspector(entry.payload ?? {}, entry.response ?? {});
      renderRouteSteps(entry.response?.steps || []);
    });

    const time = document.createElement("div");
    const timeStrong = document.createElement("strong");
    timeStrong.textContent = entry.at;
    const duration = document.createElement("span");
    duration.textContent =
      entry.duration_ms === undefined ? "local" : `${entry.duration_ms} ms`;
    time.append(timeStrong, duration);

    const detail = document.createElement("div");
    const flow = document.createElement("div");
    flow.className = "log-flow";
    flow.textContent = `${entry.from} -> ${entry.to}`;
    const endpoint = document.createElement("div");
    endpoint.className = "log-endpoint";
    endpoint.textContent = `${entry.method || "LOCAL"} ${entry.endpoint}`;
    detail.append(flow, endpoint);

    const status = document.createElement("div");
    status.className = "log-status";
    status.textContent = entry.status;
    row.append(time, detail, status);
    els.logList.appendChild(row);
  });
}

async function fetchJson(endpoint, options) {
  const method = options.method || "POST";
  const payload = options.payload ?? null;
  const from = options.from || "Terminal";
  const to = options.to || "FastAPI";
  const started = performance.now();
  resetActiveNodes();
  setNode("terminal", "active", "request");
  setNode("api", "active", endpoint);
  els.lastEndpoint.textContent = endpoint;
  updateInspector(payload ?? { method, endpoint }, { status: "waiting" });

  const requestOptions = { method, headers: {} };
  if (payload !== null && method !== "GET") {
    requestOptions.headers["Content-Type"] = "application/json";
    requestOptions.body = JSON.stringify(payload);
  }

  try {
    const response = await fetch(endpoint, requestOptions);
    const body = await readResponse(response);
    const duration = Math.round(performance.now() - started);
    const entry = {
      from,
      to,
      endpoint,
      method,
      status: response.status,
      duration_ms: duration,
      payload,
      response: body,
    };
    addLog(entry);
    updateInspector(payload ?? { method, endpoint }, body);
    setNode("api", response.ok ? "ok" : "error", `${response.status}`);
    setNode("response", response.ok ? "ok" : "error", `${response.status}`);
    return { ok: response.ok, status: response.status, data: body };
  } catch (error) {
    const duration = Math.round(performance.now() - started);
    const body = { error: String(error) };
    addLog({
      from,
      to,
      endpoint,
      method,
      status: "network-error",
      duration_ms: duration,
      payload,
      response: body,
    });
    updateInspector(payload ?? { method, endpoint }, body);
    setNode("api", "error", "network");
    setNode("response", "error", "network");
    return { ok: false, status: 0, data: body };
  }
}

async function fetchForm(endpoint, formData, payloadSummary, options) {
  const started = performance.now();
  resetActiveNodes();
  setNode("terminal", "active", "image");
  setNode("api", "active", endpoint);
  setNode("vlm", "active", "VLM");
  els.lastEndpoint.textContent = endpoint;
  updateInspector(payloadSummary, { status: "waiting" });

  try {
    const response = await fetch(endpoint, { method: "POST", body: formData });
    const body = await readResponse(response);
    const duration = Math.round(performance.now() - started);
    addLog({
      from: options.from || "Terminal",
      to: options.to || "VLM Adapter",
      endpoint,
      method: "POST",
      status: response.status,
      duration_ms: duration,
      payload: payloadSummary,
      response: body,
    });
    updateInspector(payloadSummary, body);
    setNode("api", response.ok ? "ok" : "error", `${response.status}`);
    setNode("vlm", response.ok ? "ok" : "error", response.ok ? "evidence" : "failed");
    setNode("localizer", response.ok ? "ok" : "error", "candidate");
    setNode("response", response.ok ? "ok" : "error", `${response.status}`);
    return { ok: response.ok, status: response.status, data: body };
  } catch (error) {
    const duration = Math.round(performance.now() - started);
    const body = { error: String(error) };
    addLog({
      from: "Terminal",
      to: "VLM Adapter",
      endpoint,
      method: "POST",
      status: "network-error",
      duration_ms: duration,
      payload: payloadSummary,
      response: body,
    });
    updateInspector(payloadSummary, body);
    setNode("api", "error", "network");
    setNode("vlm", "error", "network");
    setNode("response", "error", "network");
    return { ok: false, status: 0, data: body };
  }
}

async function readResponse(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function parseLines(value) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function roomTokens(text) {
  return Array.from(new Set((text.match(/\b4\d{2}[A-C]?\b/gi) || []).map((v) => v.toUpperCase())));
}

function parseObjects() {
  return parseLines(els.objects.value).map((line) => {
    const [rawLabel, rawConfidence] = line.split(":");
    const confidence = Number.parseFloat(rawConfidence);
    return {
      label: rawLabel.trim(),
      confidence: Number.isFinite(confidence) ? Math.max(0, Math.min(1, confidence)) : 1,
    };
  });
}

function buildVisualPayload() {
  const utterance = els.utterance.value.trim();
  const recognized = parseLines(els.recognizedTexts.value);
  roomTokens(utterance).forEach((room) => {
    if (!recognized.includes(room)) recognized.push(room);
  });
  const floor = Number.parseInt(els.floorHint.value, 10);
  return {
    objects: parseObjects(),
    recognized_texts: recognized,
    scene_description: els.sceneDescription.value.trim() || utterance,
    floor_hint: Number.isFinite(floor) ? floor : null,
  };
}

function buildRoutePayload() {
  return {
    from_location: els.fromLocation.value.trim() || state.currentLocation || "LB-4F-ROOM-400A",
    to_location: els.toLocation.value.trim() || "LB-4F-ROOM-429B",
    language: els.language.value,
    accessible_only: els.accessibleOnly.checked,
  };
}

function buildContextPayload() {
  return {
    question: els.question.value.trim() || els.utterance.value.trim() || "这个展品在哪里？",
    language: els.language.value,
  };
}

function buildIntent() {
  const utterance = els.utterance.value.trim();
  const rooms = roomTokens(utterance);
  if (rooms.length >= 1 && !els.fromLocation.value.trim()) {
    els.fromLocation.value = rooms[0];
  }
  if (rooms.length >= 2) {
    els.fromLocation.value = rooms[0];
    els.toLocation.value = rooms[1];
  } else if (rooms.length === 1 && /去|到|前往|导航/.test(utterance)) {
    els.toLocation.value = rooms[0];
  }
  if (/机器人|robot/i.test(utterance)) {
    els.exhibitId.value = "ROBOT-001";
    if (/去|到|前往|导航/.test(utterance)) {
      els.toLocation.value = "LB-4F-ROOM-400";
    }
  }

  const intent = {
    utterance,
    inferred: {
      rooms,
      from_location: els.fromLocation.value.trim(),
      to_location: els.toLocation.value.trim(),
      exhibit_id: els.exhibitId.value.trim(),
      language: els.language.value,
      accessible_only: els.accessibleOnly.checked,
    },
    next_json: {
      visual: buildVisualPayload(),
      route: buildRoutePayload(),
      exhibit_context: buildContextPayload(),
    },
  };
  resetActiveNodes();
  setNode("terminal", "ok", "intent");
  addLog({
    from: "Terminal",
    to: "Intent Builder",
    endpoint: "local://intent",
    method: "LOCAL",
    status: "built",
    payload: { utterance },
    response: intent,
  });
  updateInspector({ utterance }, intent);
}

function applyLocalization(data) {
  const summary = data.status
    ? `${data.status}${data.node_id ? `: ${data.node_id}` : ""}`
    : "无定位结果";
  els.localizeSummary.textContent = summary;
  if (data.node_id) {
    state.currentLocation = data.node_id;
    els.fromLocation.value = data.node_id;
    setBadge(els.currentLocation, `current: ${data.node_id}`, "ok");
  } else if (data.candidates?.length) {
    const best = data.candidates[0];
    setBadge(els.currentLocation, `candidate: ${best.node_id}`, "warn");
  }
  setNode("localizer", data.status === "not_found" ? "error" : "ok", data.status || "done");
  setNode("repository", "ok", "landmarks");
}

function applyRoute(data) {
  const steps = data.steps || [];
  renderRouteSteps(steps);
  els.routeSummary.textContent =
    data.total_distance_m !== undefined
      ? `${data.total_distance_m} m / ${steps.length} 步`
      : "无路线";
  setNode("navigator", steps.length || data.total_distance_m === 0 ? "ok" : "error", "route");
  setNode("repository", "ok", "graph");
}

async function checkHealth() {
  const result = await fetchJson("/health", {
    method: "GET",
    from: "Browser",
    to: "FastAPI",
  });
  setBadge(
    els.healthBadge,
    result.ok ? `health: ${result.data.status}` : `health: ${result.status}`,
    result.ok ? "ok" : "bad",
  );
}

async function loadPlaces() {
  const result = await fetchJson("/api/v1/places", {
    method: "GET",
    from: "Browser",
    to: "Repository",
  });
  if (!result.ok) {
    setBadge(els.placesBadge, `places: ${result.status}`, "bad");
    return;
  }
  const places = result.data.places || [];
  els.placeOptions.textContent = "";
  places.forEach((place) => {
    const option = document.createElement("option");
    option.value = place.id;
    option.label = `${place.name_zh} / ${place.name_en}`;
    els.placeOptions.appendChild(option);
  });
  setBadge(els.placesBadge, `places: ${places.length}`, "ok");
  setNode("repository", "ok", `${places.length} nodes`);
}

async function sendVisual() {
  const payload = buildVisualPayload();
  const result = await fetchJson("/api/v1/localize/visual", {
    method: "POST",
    from: "Terminal",
    to: "VisualLocalizer",
    payload,
  });
  if (result.data) applyLocalization(result.data);
}

async function sendImage() {
  if (!state.imageFile) {
    updateInspector(
      { image: null },
      { error: "请先选择或拖入一张照片。" },
    );
    return;
  }
  const formData = new FormData();
  formData.append("image", state.imageFile);
  if (els.floorHint.value.trim()) {
    formData.append("floor_hint", els.floorHint.value.trim());
  }
  const payloadSummary = {
    image: {
      name: state.imageFile.name,
      size: state.imageFile.size,
      type: state.imageFile.type,
    },
    floor_hint: els.floorHint.value.trim() || null,
  };
  const result = await fetchForm("/api/v1/localize/image", formData, payloadSummary, {
    from: "Terminal",
    to: "VLM Adapter",
  });
  if (result.data) applyLocalization(result.data);
}

async function sendRoute() {
  const payload = buildRoutePayload();
  const result = await fetchJson("/api/v1/route", {
    method: "POST",
    from: "Terminal",
    to: "Navigator",
    payload,
  });
  if (result.data) applyRoute(result.data);
}

async function sendContext() {
  const exhibitId = els.exhibitId.value.trim() || "ROBOT-001";
  const payload = buildContextPayload();
  const result = await fetchJson(`/api/v1/exhibits/${encodeURIComponent(exhibitId)}/context`, {
    method: "POST",
    from: "Terminal",
    to: "Exhibit Context",
    payload,
  });
  setNode("exhibit", result.ok ? "ok" : "error", exhibitId);
}

async function runScenario() {
  buildIntent();
  if (state.imageFile) {
    await sendImage();
  } else {
    await sendVisual();
  }
  await sendRoute();
  await sendContext();
}

function setImage(file) {
  if (!file) return;
  state.imageFile = file;
  els.imageMeta.textContent = `${file.name} · ${Math.round(file.size / 1024)} KiB · ${file.type || "unknown"}`;
  if (file.type.startsWith("image/")) {
    const url = URL.createObjectURL(file);
    els.imagePreview.src = url;
    els.imagePreview.classList.remove("hidden");
  }
}

function exportLogs() {
  const blob = new Blob([pretty(state.logs)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `longbin-flow-logs-${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function bindEvents() {
  $("#checkHealth").addEventListener("click", checkHealth);
  $("#loadPlaces").addEventListener("click", loadPlaces);
  $("#buildIntent").addEventListener("click", buildIntent);
  $("#sendVisual").addEventListener("click", sendVisual);
  $("#sendImage").addEventListener("click", sendImage);
  $("#sendRoute").addEventListener("click", sendRoute);
  $("#sendContext").addEventListener("click", sendContext);
  $("#runScenario").addEventListener("click", runScenario);
  $("#exportLogs").addEventListener("click", exportLogs);
  $("#clearLogs").addEventListener("click", () => {
    state.logs = [];
    saveLogs();
    renderLogs();
  });
  $("#inputs").addEventListener("submit", (event) => event.preventDefault());

  els.imageFile.addEventListener("change", (event) => {
    setImage(event.target.files[0]);
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.remove("dragging");
    });
  });
  els.dropZone.addEventListener("drop", (event) => {
    setImage(event.dataTransfer.files[0]);
  });

  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.tab;
      els.payloadView.classList.toggle("hidden", target !== "payload");
      els.responseView.classList.toggle("hidden", target !== "response");
      els.routeSteps.classList.toggle("hidden", target !== "route");
    });
  });
}

function init() {
  bindEvents();
  updateInspector();
  renderRouteSteps([]);
  renderLogs();
  checkHealth();
  loadPlaces();
}

init();
