const storageKey = "longbin-flow-lab-communications";

const connections = {
  "user>terminal": ["user", "terminal", "User -> Terminal"],
  "terminal>vlm": ["terminal", "vlm", "Terminal -> VLM"],
  "vlm>localizer": ["vlm", "localizer", "VLM -> Localizer"],
  "terminal>context": ["terminal", "context", "Terminal -> RAG / DB"],
  "localizer>navigator": ["localizer", "navigator", "Localizer -> Navigator"],
  "context>navigator": ["context", "navigator", "RAG / DB -> Navigator"],
  "navigator>composer": ["navigator", "composer", "Navigator -> Response"],
  "composer>tts": ["composer", "tts", "Response -> TTS"],
};

const state = {
  imageFile: null,
  places: [],
  guideContext: null,
  localization: null,
  route: null,
  logs: loadLogs(),
  selectedModule: null,
  activeEdge: "user>terminal",
  edgeData: {},
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const els = {
  healthBadge: $("#healthBadge"),
  placesBadge: $("#placesBadge"),
  contextBadge: $("#contextBadge"),
  currentNodeStat: $("#currentNodeStat"),
  targetNodeStat: $("#targetNodeStat"),
  requestCountStat: $("#requestCountStat"),
  ttsLengthStat: $("#ttsLengthStat"),
  utterance: $("#utterance"),
  language: $("#language"),
  floorHint: $("#floorHint"),
  imageFile: $("#imageFile"),
  imageMeta: $("#imageMeta"),
  imagePreview: $("#imagePreview"),
  dropZone: $("#dropZone"),
  recognizedTexts: $("#recognizedTexts"),
  objects: $("#objects"),
  sceneDescription: $("#sceneDescription"),
  visitorCard: $("#visitorCard"),
  fromLocation: $("#fromLocation"),
  toLocation: $("#toLocation"),
  accessibleOnly: $("#accessibleOnly"),
  routeCard: $("#routeCard"),
  moduleBoard: $("#moduleBoard"),
  selectedEdgeLabel: $("#selectedEdgeLabel"),
  detailTitle: $("#detailTitle"),
  detailStatus: $("#detailStatus"),
  payloadView: $("#payloadView"),
  responseView: $("#responseView"),
  logList: $("#logList"),
  logCount: $("#logCount"),
  ttsText: $("#ttsText"),
  outputState: $("#outputState"),
  localizeSummary: $("#localizeSummary"),
  routeSummary: $("#routeSummary"),
  visitSummary: $("#visitSummary"),
  routeSteps: $("#routeSteps"),
  placeOptions: $("#placeOptions"),
};

function loadLogs() {
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "[]");
  } catch {
    return [];
  }
}

function saveLogs() {
  localStorage.setItem(storageKey, JSON.stringify(state.logs.slice(0, 200)));
}

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function nowLabel() {
  return new Date().toLocaleString("zh-CN", { hour12: false });
}

function setPill(element, text, kind = "muted") {
  element.textContent = text;
  element.classList.remove("muted", "ok", "warn", "bad");
  element.classList.add(kind);
}

function setModule(module, kind = "") {
  const node = $(`[data-module="${module}"]`);
  if (!node) return;
  node.classList.remove("active", "ok", "error");
  if (kind) node.classList.add(kind);
}

function resetModuleState() {
  $$(".module-node").forEach((node) => {
    node.classList.remove("active", "ok", "error", "selected");
  });
}

function updateStats() {
  els.currentNodeStat.textContent = state.localization?.node_id || els.fromLocation.value || "未定位";
  els.targetNodeStat.textContent = els.toLocation.value || "未设置";
  els.requestCountStat.textContent = String(state.logs.length);
  const ttsText = els.ttsText.value.trim();
  els.ttsLengthStat.textContent = ttsText.startsWith("运行流程后") ? "0" : String(ttsText.length);
}

function selectEdge(edgeKey) {
  if (!connections[edgeKey]) return;
  state.activeEdge = edgeKey;
  $$(".edge").forEach((edge) => edge.classList.toggle("active", edge.dataset.edge === edgeKey));
  $$(".module-node").forEach((node) => node.classList.remove("selected"));
  const [from, to, label] = connections[edgeKey];
  $(`[data-module="${from}"]`)?.classList.add("selected");
  $(`[data-module="${to}"]`)?.classList.add("selected");
  const data = state.edgeData[edgeKey] || {
    status: "未运行",
    payload: { edge: edgeKey },
    response: { message: "运行流程后，这里会出现这两个模块之间的通信内容。" },
  };
  els.selectedEdgeLabel.textContent = label;
  els.detailTitle.textContent = label;
  els.detailStatus.textContent = `${data.method || "LOCAL"} ${data.status}`;
  els.payloadView.textContent = pretty(data.payload);
  els.responseView.textContent = pretty(data.response);
}

function recordEdge(edgeKey, payload, response, meta = {}) {
  if (!connections[edgeKey]) return;
  const entry = {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    at: nowLabel(),
    edge: edgeKey,
    from: connections[edgeKey][0],
    to: connections[edgeKey][1],
    label: connections[edgeKey][2],
    method: meta.method || "LOCAL",
    endpoint: meta.endpoint || "local",
    status: meta.status || "ok",
    duration_ms: meta.duration_ms,
    payload,
    response,
  };
  state.edgeData[edgeKey] = entry;
  state.logs.unshift(entry);
  state.logs = state.logs.slice(0, 200);
  saveLogs();
  renderLogs();
  if (state.activeEdge === edgeKey || meta.focus) selectEdge(edgeKey);
  updateStats();
}

function renderLogs() {
  els.logList.textContent = "";
  els.logCount.textContent = `${state.logs.length} 条`;
  if (!state.logs.length) {
    const empty = document.createElement("div");
    empty.className = "info-card";
    empty.textContent = "暂无通信记录。";
    els.logList.appendChild(empty);
    updateStats();
    return;
  }
  state.logs.forEach((entry) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "log-item";
    row.addEventListener("click", () => selectEdge(entry.edge));

    const time = document.createElement("div");
    const timeStrong = document.createElement("strong");
    timeStrong.textContent = entry.at.split(" ").pop();
    const duration = document.createElement("span");
    duration.textContent =
      entry.duration_ms === undefined ? entry.method : `${entry.duration_ms} ms`;
    time.append(timeStrong, duration);

    const detail = document.createElement("div");
    const flow = document.createElement("div");
    flow.className = "log-flow";
    flow.textContent = entry.label;
    const endpoint = document.createElement("div");
    endpoint.className = "log-endpoint";
    endpoint.textContent = `${entry.method} ${entry.endpoint}`;
    detail.append(flow, endpoint);

    const status = document.createElement("div");
    status.className = "log-status";
    status.textContent = entry.status;
    row.append(time, detail, status);
    els.logList.appendChild(row);
  });
  updateStats();
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

async function requestJson(endpoint, options = {}) {
  const method = options.method || "GET";
  const payload = options.payload;
  const started = performance.now();
  const requestOptions = { method, headers: {} };
  if (payload !== undefined && method !== "GET") {
    requestOptions.headers["Content-Type"] = "application/json";
    requestOptions.body = JSON.stringify(payload);
  }
  if (options.activeModules) {
    options.activeModules.forEach((module) => setModule(module, "active"));
  }
  try {
    const response = await fetch(endpoint, requestOptions);
    const body = await readResponse(response);
    const duration = Math.round(performance.now() - started);
    if (options.edge) {
      recordEdge(options.edge, payload ?? { method, endpoint }, body, {
        method,
        endpoint,
        status: response.status,
        duration_ms: duration,
        focus: options.focus,
      });
    }
    (options.okModules || []).forEach((module) => setModule(module, response.ok ? "ok" : "error"));
    return { ok: response.ok, status: response.status, data: body };
  } catch (error) {
    const duration = Math.round(performance.now() - started);
    const body = { error: String(error) };
    if (options.edge) {
      recordEdge(options.edge, payload ?? { method, endpoint }, body, {
        method,
        endpoint,
        status: "network-error",
        duration_ms: duration,
        focus: true,
      });
    }
    (options.okModules || []).forEach((module) => setModule(module, "error"));
    return { ok: false, status: 0, data: body };
  }
}

async function requestForm(endpoint, formData, payloadSummary, options = {}) {
  const started = performance.now();
  (options.activeModules || []).forEach((module) => setModule(module, "active"));
  try {
    const response = await fetch(endpoint, { method: "POST", body: formData });
    const body = await readResponse(response);
    const duration = Math.round(performance.now() - started);
    recordEdge(options.edge || "terminal>vlm", payloadSummary, body, {
      method: "POST",
      endpoint,
      status: response.status,
      duration_ms: duration,
      focus: options.focus,
    });
    (options.okModules || []).forEach((module) => setModule(module, response.ok ? "ok" : "error"));
    return { ok: response.ok, status: response.status, data: body };
  } catch (error) {
    const duration = Math.round(performance.now() - started);
    const body = { error: String(error) };
    recordEdge(options.edge || "terminal>vlm", payloadSummary, body, {
      method: "POST",
      endpoint,
      status: "network-error",
      duration_ms: duration,
      focus: true,
    });
    (options.okModules || []).forEach((module) => setModule(module, "error"));
    return { ok: false, status: 0, data: body };
  }
}

function parseLines(value) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function roomTokens(text) {
  return Array.from(
    new Set((text.match(/\b[1-4]\d{2}[A-C]?\b/gi) || []).map((value) => value.toUpperCase())),
  );
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
    from_location: state.localization?.node_id || els.fromLocation.value.trim(),
    to_location: els.toLocation.value.trim(),
    language: els.language.value,
    accessible_only: els.accessibleOnly.checked,
  };
}

function inferIntent() {
  const utterance = els.utterance.value.trim();
  const rooms = roomTokens(utterance);
  if (rooms.length >= 2) {
    els.fromLocation.value = `LB-${rooms[0][0]}F-ROOM-${rooms[0]}`;
    els.toLocation.value = `LB-${rooms[1][0]}F-ROOM-${rooms[1]}`;
  } else if (rooms.length === 1 && /去|到|前往|导航|找/.test(utterance)) {
    els.toLocation.value = `LB-${rooms[0][0]}F-ROOM-${rooms[0]}`;
  }
  if (/李政道|画展|艺术展/.test(utterance)) {
    els.fromLocation.value = "LB-3F-EVENT-LEE-ART";
    els.toLocation.value = "LB-3F-ROOM-300";
    els.floorHint.value = "3";
    els.recognizedTexts.value = "李政道画展\nLEEA ART";
    els.sceneDescription.value = "三楼开放区域有李政道画展展板";
  }
  if (/学院|介绍|college/i.test(utterance)) {
    els.toLocation.value = "LB-4F-PERMANENT-COLLEGE-INTRO";
  }
  const payload = {
    utterance,
    language: els.language.value,
    current_image: state.imageFile
      ? { name: state.imageFile.name, size: state.imageFile.size, type: state.imageFile.type }
      : { mode: "visual_json", evidence: buildVisualPayload() },
    inferred_route: buildRoutePayload(),
  };
  recordEdge("user>terminal", { spoken_text: utterance }, payload, { focus: true });
  setModule("user", "ok");
  setModule("terminal", "ok");
  updateStats();
  return payload;
}

function renderVisitorContext(data) {
  const visit = data?.visit;
  const records = data?.location_records || [];
  if (!visit) {
    els.visitorCard.textContent = "数据库中没有活跃代表团任务。";
    els.visitSummary.textContent = "无活跃任务";
  } else {
    const lines = [
      `代表团：${visit.delegation_name || "未命名"}`,
      `机构：${visit.institution || "未填写"}`,
      `国家：${visit.country || "未填写"}`,
      `目的：${visit.purpose || "未填写"}`,
    ];
    els.visitorCard.innerHTML = lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
    els.visitSummary.textContent = visit.delegation_name || `Visit #${visit.id}`;
  }
  if (records.length) {
    els.visitorCard.insertAdjacentHTML(
      "beforeend",
      `<div class="context-mini">当前位置资料：${records.slice(0, 3).map((item) => escapeHtml(item.title_zh || item.node_id)).join(" / ")}</div>`,
    );
  }
}

async function loadContext() {
  const currentNode = state.localization?.node_id || els.fromLocation.value.trim();
  const params = new URLSearchParams();
  if (currentNode) params.set("current_node", currentNode);
  const endpoint = `/api/v1/guide/context${params.toString() ? `?${params}` : ""}`;
  const result = await requestJson(endpoint, {
    method: "GET",
    edge: "terminal>context",
    activeModules: ["terminal", "context"],
    okModules: ["context"],
    focus: true,
  });
  if (result.ok) {
    state.guideContext = result.data;
    renderVisitorContext(result.data);
    setPill(els.contextBadge, "数据库已读取", "ok");
  } else {
    setPill(els.contextBadge, `数据库 ${result.status}`, "bad");
  }
  return result;
}

async function checkHealth() {
  const result = await requestJson("/health", {
    method: "GET",
    activeModules: ["terminal"],
  });
  setPill(
    els.healthBadge,
    result.ok ? `后端 ${result.data.status}` : `后端 ${result.status}`,
    result.ok ? "ok" : "bad",
  );
}

async function loadPlaces() {
  const result = await requestJson("/api/v1/places", {
    method: "GET",
    activeModules: ["context"],
    okModules: ["context"],
  });
  if (!result.ok) {
    setPill(els.placesBadge, `节点 ${result.status}`, "bad");
    return;
  }
  state.places = result.data.places || [];
  els.placeOptions.textContent = "";
  state.places.forEach((place) => {
    const option = document.createElement("option");
    option.value = place.id;
    option.label = `${place.name_zh} / ${place.name_en}`;
    els.placeOptions.appendChild(option);
  });
  setPill(els.placesBadge, `节点 ${state.places.length}`, "ok");
}

function applyLocalization(data) {
  state.localization = data;
  const ok = data.status === "matched";
  if (data.node_id) {
    els.fromLocation.value = data.node_id;
  }
  els.localizeSummary.textContent = data.node_id
    ? `${data.status}: ${data.node_id}`
    : `${data.status || "unknown"} / ${data.candidates?.length || 0} 个候选`;
  setModule("localizer", ok ? "ok" : data.status === "ambiguous" ? "active" : "error");
  recordEdge(
    "localizer>navigator",
    { current_node: data.node_id, confidence: data.confidence, status: data.status },
    {
      accepted_start_node: data.node_id || null,
      candidates: data.candidates || [],
      needs_confirmation: data.needs_confirmation,
    },
  );
  updateStats();
}

async function sendVisual() {
  const evidence = buildVisualPayload();
  recordEdge(
    "terminal>vlm",
    { mode: "visual_json", source: "manual fields", evidence },
    { evidence, note: "未上传图片，直接使用结构化视觉证据模拟 VLM 输出。" },
  );
  const result = await requestJson("/api/v1/localize/visual", {
    method: "POST",
    payload: evidence,
    edge: "vlm>localizer",
    activeModules: ["vlm", "localizer"],
    okModules: ["vlm", "localizer"],
    focus: true,
  });
  if (result.data) applyLocalization(result.data);
  return result;
}

async function sendImage() {
  if (!state.imageFile) return sendVisual();
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
  const result = await requestForm("/api/v1/localize/image", formData, payloadSummary, {
    edge: "terminal>vlm",
    activeModules: ["terminal", "vlm", "localizer"],
    okModules: ["vlm", "localizer"],
    focus: true,
  });
  recordEdge(
    "vlm>localizer",
    { image_analysis_result: "由后端 VLM 适配器生成，详情见上一段响应。" },
    result.data,
  );
  if (result.data) applyLocalization(result.data);
  return result;
}

function renderRouteSteps(steps = []) {
  els.routeSteps.textContent = "";
  if (!steps.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无内部步骤。";
    els.routeSteps.appendChild(empty);
    return;
  }
  steps.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = `${step.from_id} -> ${step.to_id} · ${step.distance_m}m · ${step.instruction}`;
    els.routeSteps.appendChild(item);
  });
}

function applyRoute(data) {
  state.route = data;
  const steps = data.steps || [];
  renderRouteSteps(steps);
  const summary =
    data.total_distance_m !== undefined
      ? `${data.total_distance_m} m / ${steps.length} 步`
      : "路线不可用";
  els.routeSummary.textContent = summary;
  els.routeCard.innerHTML = data.announcement
    ? `<strong>${escapeHtml(data.announcement)}</strong><div class="context-mini">${escapeHtml(summary)}</div>`
    : "路线生成失败。";
  recordEdge(
    "navigator>composer",
    data,
    {
      announcement: data.announcement,
      compact_for_device: true,
      internal_steps_count: steps.length,
    },
  );
  setModule("navigator", data.announcement ? "ok" : "error");
  updateStats();
}

async function sendRoute() {
  const payload = buildRoutePayload();
  recordEdge(
    "context>navigator",
    {
      visit: state.guideContext?.visit || null,
      location_records_count: state.guideContext?.location_records?.length || 0,
      route_request: payload,
    },
    { note: "Navigator 使用 SQLite 地图节点和边生成确定性路线。" },
  );
  const result = await requestJson("/api/v1/route", {
    method: "POST",
    payload,
    edge: "context>navigator",
    activeModules: ["context", "navigator"],
    okModules: ["navigator"],
    focus: true,
  });
  if (result.data) applyRoute(result.data);
  return result;
}

function composeTts() {
  let text = "";
  if (state.route?.announcement) {
    text = state.route.announcement;
  } else if (state.localization?.status === "ambiguous") {
    text = "我暂时无法确认当前位置，请将设备朝向门牌或展板后再拍一次。";
  } else if (state.localization?.status === "not_found") {
    text = "没有识别到当前位置，请靠近门牌或展板后再试一次。";
  } else {
    text = "当前流程还没有生成可播报结果。";
  }
  els.ttsText.value = text;
  setPill(els.outputState, text ? "已生成" : "等待运行", text ? "ok" : "muted");
  setModule("composer", "ok");
  setModule("tts", "ok");
  recordEdge(
    "composer>tts",
    {
      language: els.language.value,
      route_announcement: state.route?.announcement || null,
      localization_status: state.localization?.status || null,
    },
    { tts_text: text, speak_immediately: true },
    { focus: true },
  );
  updateStats();
}

async function runFlow() {
  resetModuleState();
  inferIntent();
  await loadContext();
  if (state.imageFile) {
    await sendImage();
  } else {
    await sendVisual();
  }
  await sendRoute();
  composeTts();
}

function setScenario(name) {
  state.imageFile = null;
  els.imageFile.value = "";
  els.imagePreview.classList.add("hidden");
  if (name === "lee") {
    els.utterance.value = "我在三楼李政道画展附近，想去300会议室。";
    els.language.value = "zh";
    els.floorHint.value = "3";
    els.fromLocation.value = "LB-3F-EVENT-LEE-ART";
    els.toLocation.value = "LB-3F-ROOM-300";
    els.recognizedTexts.value = "李政道画展\nLEE ART";
    els.objects.value = "展板:0.92\n画展:0.88";
    els.sceneDescription.value = "三楼开放区域可见李政道画展展板";
  } else if (name === "college") {
    els.utterance.value = "我从访客电梯出来，带来宾去学院介绍区域。";
    els.language.value = "zh";
    els.floorHint.value = "4";
    els.fromLocation.value = "LB-1F-OPEN-08";
    els.toLocation.value = "LB-4F-PERMANENT-COLLEGE-INTRO";
    els.recognizedTexts.value = "出口\n电梯";
    els.objects.value = "电梯:0.91\n出口:0.83";
    els.sceneDescription.value = "一楼访客电梯附近，面向大厅出口";
  } else {
    els.utterance.value = "我现在在400A附近，想去429B。";
    els.language.value = "zh";
    els.floorHint.value = "4";
    els.fromLocation.value = "LB-4F-ROOM-400A";
    els.toLocation.value = "LB-4F-ROOM-429B";
    els.recognizedTexts.value = "400A";
    els.objects.value = "400A:0.98\n门牌:0.82";
    els.sceneDescription.value = "走廊左侧可见400A房间门牌";
  }
  els.imageMeta.textContent = "未选择图片时使用下方视觉 JSON 模拟";
  state.localization = null;
  state.route = null;
  renderRouteSteps([]);
  updateStats();
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
  link.download = `longbin-flow-communications-${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  $("#loadContext").addEventListener("click", loadContext);
  $("#runFlow").addEventListener("click", runFlow);
  $("#sendVisual").addEventListener("click", sendVisual);
  $("#sendRoute").addEventListener("click", sendRoute);
  $("#clearLogs").addEventListener("click", () => {
    state.logs = [];
    state.edgeData = {};
    saveLogs();
    renderLogs();
    selectEdge("user>terminal");
  });
  $("#exportLogs").addEventListener("click", exportLogs);
  $("#scenario4f").addEventListener("click", () => setScenario("4f"));
  $("#scenarioLee").addEventListener("click", () => setScenario("lee"));
  $("#scenarioCollege").addEventListener("click", () => setScenario("college"));

  els.imageFile.addEventListener("change", (event) => setImage(event.target.files[0]));
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

  $$(".edge").forEach((edge) => {
    edge.addEventListener("click", () => selectEdge(edge.dataset.edge));
  });
  $$(".module-node").forEach((node) => {
    node.addEventListener("click", () => {
      const module = node.dataset.module;
      if (!state.selectedModule) {
        state.selectedModule = module;
        $$(".module-node").forEach((item) => item.classList.remove("selected"));
        node.classList.add("selected");
        return;
      }
      const forward = `${state.selectedModule}>${module}`;
      const backward = `${module}>${state.selectedModule}`;
      if (connections[forward]) selectEdge(forward);
      else if (connections[backward]) selectEdge(backward);
      else {
        $$(".module-node").forEach((item) => item.classList.remove("selected"));
        node.classList.add("selected");
      }
      state.selectedModule = module;
    });
  });

  ["fromLocation", "toLocation", "utterance"].forEach((id) => {
    $(`#${id}`).addEventListener("input", updateStats);
  });
}

function init() {
  Object.keys(connections).forEach((edgeKey) => {
    state.edgeData[edgeKey] = {
      method: "LOCAL",
      status: "pending",
      payload: { edge: edgeKey },
      response: { message: "等待运行流程。" },
    };
  });
  bindEvents();
  renderLogs();
  renderRouteSteps([]);
  selectEdge("user>terminal");
  updateStats();
  checkHealth();
  loadPlaces();
  loadContext();
}

init();
