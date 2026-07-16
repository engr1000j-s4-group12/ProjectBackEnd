const state = {
  entries: [], visits: [], floorplans: [], kinds: {}, map_summary: null,
  map_nodes: [], map_edges: [],
  drawMode: false, drawing: null, editingId: null,
};

const locale = document.documentElement.lang.toLowerCase().startsWith("en") ? "en" : "zh";
const messages = {
  zh: {
    backendOk: (status) => `后端 ${status}`, mapNodes: (count) => `SQLite ${count} 个地图节点`, regionCount: (count) => `${count} 个区域`,
    cancelDraw: "取消圈选", startDraw: "圈选新区域", newRegion: "新区域",
    noRecords: "没有符合条件的内容。", active: "有效", archived: "已归档",
    noDescription: "尚未录入详细说明。", floor: (value) => `${value}楼`, version: (value) => `版本 ${value}`,
    area: (value) => `区域 ${value}`, attachments: (value) => `附件 ${value}`, edit: "编辑", archive: "归档", restore: "恢复",
    editTitle: (title) => `编辑：${title}`, newEntry: "新增空间内容", newFloorEntry: (floor) => `新增 ${floor}楼空间内容`,
    archivedToast: "内容已归档，Guide 将不再主动读取。", restoredToast: "内容已恢复发布。",
    noEntry: "不可进入",
    drawFirst: "请先在地图上圈出范围。", saving: "正在保存…", processing: (current, total) => `正在处理附件 ${current}/${total}…`,
    publishedVlm: "内容已发布，图片预处理结果已写入数据库。", published: "内容已发布。", saveFailed: (error) => `保存失败：${error}`,
    noVisits: "暂无代表团任务。", available: "当前可用", noPurpose: "未填写来访目的。", endVisit: "结束并归档",
    visitArchived: "来访任务已归档。下一次导览不会读取它。", visitCreated: "来访任务已创建。Guide 可以读取该任务。",
    createFailed: (error) => `创建失败：${error}`, backendDown: "后端不可用",
    kinds: { permanent: "长期信息", event: "活动/临时展览", exhibit: "常设展品", facility: "设施" },
  },
  en: {
    backendOk: (status) => `Backend ${status}`, mapNodes: (count) => `SQLite ${count} map nodes`, regionCount: (count) => `${count} regions`,
    cancelDraw: "Cancel drawing", startDraw: "Draw new region", newRegion: "New region",
    noRecords: "No matching records.", active: "Active", archived: "Archived",
    noDescription: "No description has been entered.", floor: (value) => `Floor ${value}`, version: (value) => `Version ${value}`,
    area: (value) => `Area ${value}`, attachments: (value) => `${value} attachments`, edit: "Edit", archive: "Archive", restore: "Restore",
    editTitle: (title) => `Edit: ${title}`, newEntry: "Add spatial content", newFloorEntry: (floor) => `Add content on Floor ${floor}`,
    archivedToast: "Content archived. Guide will no longer read it by default.", restoredToast: "Content restored and published.",
    noEntry: "NO ENTRY",
    drawFirst: "Draw a region on a floor plan first.", saving: "Saving…", processing: (current, total) => `Processing attachment ${current}/${total}…`,
    publishedVlm: "Published. Image preprocessing results were stored in the database.", published: "Content published.", saveFailed: (error) => `Save failed: ${error}`,
    noVisits: "No delegation missions yet.", available: "Available", noPurpose: "No visit purpose provided.", endVisit: "End and archive",
    visitArchived: "Visit mission archived. Guide will not read it on the next tour.", visitCreated: "Visit mission created. Guide can now read it.",
    createFailed: (error) => `Creation failed: ${error}`, backendDown: "Backend unavailable",
    kinds: { permanent: "Permanent information", event: "Event / temporary exhibition", exhibit: "Permanent exhibit", facility: "Facility" },
  },
};
const copy = messages[locale];

const $ = (selector) => document.querySelector(selector);
const els = {
  mapGrid: $("#mapGrid"), drawButton: $("#drawButton"), drawHint: $("#drawHint"),
  entryForm: $("#entryForm"), formTitle: $("#formTitle"), formStatus: $("#formStatus"),
  floor: $("#floor"), groupCode: $("#groupCode"), nodeId: $("#nodeId"), geometry: $("#geometry"),
  kind: $("#kind"), titleZh: $("#titleZh"), titleEn: $("#titleEn"),
  contentZh: $("#contentZh"), contentEn: $("#contentEn"), tags: $("#tags"),
  source: $("#source"), files: $("#files"), recordList: $("#recordList"),
  searchInput: $("#searchInput"), statusFilter: $("#statusFilter"),
  healthBadge: $("#healthBadge"), toast: $("#toast"),
  activeCount: $("#activeCount"), eventCount: $("#eventCount"),
  archivedCount: $("#archivedCount"), visitCount: $("#visitCount"),
  visitForm: $("#visitForm"), visitList: $("#visitList"),
};

const palette = {
  permanent: [23, 92, 211], event: [224, 79, 22],
  exhibit: [122, 90, 248], facility: [7, 148, 85],
};

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => els.toast.classList.add("hidden"), 3200);
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  let body = {};
  try { body = await response.json(); } catch { body = { detail: response.statusText }; }
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
  return body;
}

async function load() {
  const [health, data] = await Promise.all([request("/health"), request("/api/admin/bootstrap")]);
  const mapNodeCount = (data.map_summary?.floors || []).reduce((sum, floor) => sum + floor.nodes, 0);
  els.healthBadge.textContent = mapNodeCount ? `${copy.backendOk(health.status)} · ${copy.mapNodes(mapNodeCount)}` : copy.backendOk(health.status);
  els.healthBadge.className = "badge ok";
  Object.assign(state, data);
  renderMaps(); renderRecords(); renderVisits(); renderMetrics();
}

function renderMetrics() {
  els.activeCount.textContent = state.entries.filter((item) => item.status === "active").length;
  els.eventCount.textContent = state.entries.filter((item) => item.kind === "event" && item.status === "active").length;
  els.archivedCount.textContent = state.entries.filter((item) => item.status === "archived").length;
  els.visitCount.textContent = state.visits.filter((item) => item.status === "active").length;
}

function renderMaps() {
  els.mapGrid.querySelectorAll(".map-card").forEach((card) => {
    const floor = Number(card.dataset.floor);
    const img = card.querySelector("img"), canvas = card.querySelector("canvas");
    card.querySelector("header span").textContent = copy.regionCount(state.entries.filter((e) => e.floor === floor).length);
    const prepare = () => {
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      drawCanvas(canvas);
    };
    if (img.complete && img.naturalWidth) prepare();
    else if (!img.dataset.bound) img.addEventListener("load", prepare);
    if (!canvas.dataset.bound) {
      bindDrawing(canvas); canvas.dataset.bound = "true";
    }
    img.dataset.bound = "true";
  });
}

function drawCanvas(canvas) {
  const ctx = canvas.getContext("2d"); ctx.clearRect(0, 0, canvas.width, canvas.height);
  const floor = Number(canvas.dataset.floor);
  drawUserMarkedRoutes(ctx, floor);
  state.entries.filter((e) => e.floor === floor).forEach((entry) => drawPolygon(ctx, entry.geometry, entry));
  drawRestrictedZones(ctx, floor);
  if (state.drawing?.floor === floor && state.drawing.points.length > 1) {
    drawPolygon(ctx, state.drawing.points, { kind: "event", node_id: copy.newRegion, status: "active" }, false);
  }
}

function drawRestrictedZones(ctx, floor) {
  const zones = state.map_nodes.filter((node) =>
    node.floor === floor && node.kind === "restricted" && node.status === "active" && node.geometry?.length,
  );
  zones.forEach((zone) => {
    const points = zone.geometry;
    ctx.save();
    ctx.beginPath();
    points.forEach((point, index) => {
      const x = point[0] * ctx.canvas.width, y = point[1] * ctx.canvas.height;
      index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(92, 18, 24, .94)";
    ctx.strokeStyle = "rgba(255, 78, 86, 1)";
    ctx.lineWidth = Math.max(3, ctx.canvas.width / 450);
    ctx.fill(); ctx.stroke();

    const center = points.reduce(
      (acc, point) => [acc[0] + point[0], acc[1] + point[1]], [0, 0],
    ).map((value) => value / points.length);
    const x = center[0] * ctx.canvas.width, y = center[1] * ctx.canvas.height;
    ctx.strokeStyle = "rgba(255,255,255,.9)";
    ctx.lineWidth = Math.max(2, ctx.canvas.width / 700);
    const radius = Math.max(8, ctx.canvas.width / 125);
    ctx.beginPath(); ctx.moveTo(x - radius, y - radius); ctx.lineTo(x + radius, y + radius); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + radius, y - radius); ctx.lineTo(x - radius, y + radius); ctx.stroke();
    ctx.font = `800 ${Math.max(13, ctx.canvas.width / 105)}px sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "bottom";
    ctx.fillStyle = "white";
    ctx.fillText(copy.noEntry, x, y - radius - 3);
    ctx.restore();
  });
}

function drawUserMarkedRoutes(ctx, floor) {
  const nodes = new Map(
    state.map_nodes
      .filter((node) => node.floor === floor && node.x_norm != null && node.y_norm != null)
      .map((node) => [node.node_id, node]),
  );
  const edges = state.map_edges.filter((edge) => edge.calibration_status === "user_marked" && edge.status === "active");
  ctx.save();
  ctx.strokeStyle = "rgba(18, 164, 82, .78)";
  ctx.fillStyle = "rgba(18, 164, 82, .9)";
  ctx.lineWidth = Math.max(3, ctx.canvas.width / 420);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  edges.forEach((edge) => {
    const start = nodes.get(edge.from_node_id), end = nodes.get(edge.to_node_id);
    if (!start || !end) return;
    ctx.beginPath();
    ctx.moveTo(start.x_norm * ctx.canvas.width, start.y_norm * ctx.canvas.height);
    ctx.lineTo(end.x_norm * ctx.canvas.width, end.y_norm * ctx.canvas.height);
    ctx.stroke();
    [start, end].forEach((node) => {
      ctx.beginPath();
      ctx.arc(node.x_norm * ctx.canvas.width, node.y_norm * ctx.canvas.height, Math.max(4, ctx.canvas.width / 300), 0, Math.PI * 2);
      ctx.fill();
    });
  });
  ctx.restore();
}

function drawPolygon(ctx, points, entry, close = true) {
  if (!points?.length) return;
  const [r, g, b] = palette[entry.kind] || palette.permanent;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = point[0] * ctx.canvas.width, y = point[1] * ctx.canvas.height;
    index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  if (close) ctx.closePath();
  ctx.fillStyle = `rgba(${r},${g},${b},${entry.status === "archived" ? .07 : .16})`;
  ctx.strokeStyle = `rgba(${r},${g},${b},${entry.status === "archived" ? .35 : .92})`;
  ctx.lineWidth = Math.max(3, ctx.canvas.width / 500); ctx.setLineDash(close ? [] : [12, 8]);
  if (close) ctx.fill(); ctx.stroke(); ctx.setLineDash([]);
  if (close) {
    const center = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]).map((v) => v / points.length);
    ctx.font = `700 ${Math.max(15, ctx.canvas.width / 90)}px sans-serif`;
    ctx.fillStyle = `rgb(${r},${g},${b})`; ctx.textAlign = "center";
    ctx.fillText(entry.group_code || entry.node_id, center[0] * ctx.canvas.width, center[1] * ctx.canvas.height);
  }
}

function bindDrawing(canvas) {
  canvas.addEventListener("pointerdown", (event) => {
    if (!state.drawMode) return;
    canvas.setPointerCapture(event.pointerId);
    const point = normalizedPoint(canvas, event);
    state.drawing = { floor: Number(canvas.dataset.floor), points: [point] };
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!state.drawMode || !state.drawing || state.drawing.floor !== Number(canvas.dataset.floor)) return;
    const point = normalizedPoint(canvas, event);
    const previous = state.drawing.points.at(-1);
    if (Math.hypot(point[0] - previous[0], point[1] - previous[1]) > .008) state.drawing.points.push(point);
    drawCanvas(canvas);
  });
  canvas.addEventListener("pointerup", () => {
    if (!state.drawing || state.drawing.points.length < 3) return;
    const floor = state.drawing.floor;
    els.floor.value = String(floor); els.geometry.value = JSON.stringify(state.drawing.points);
    els.nodeId.value = `LB-${floor}F-REGION-${String(Date.now()).slice(-6)}`;
    els.formTitle.textContent = copy.newFloorEntry(floor);
    setDrawMode(false); els.entryForm.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function normalizedPoint(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  return [Number(((event.clientX - rect.left) / rect.width).toFixed(4)), Number(((event.clientY - rect.top) / rect.height).toFixed(4))];
}

function setDrawMode(enabled) {
  state.drawMode = enabled;
  document.body.classList.toggle("drawing", enabled);
  els.drawHint.classList.toggle("hidden", !enabled);
  els.drawButton.textContent = enabled ? copy.cancelDraw : copy.startDraw;
  if (!enabled && !els.geometry.value) state.drawing = null;
  document.querySelectorAll("canvas").forEach(drawCanvas);
}

function renderRecords() {
  const query = els.searchInput.value.trim().toLowerCase(), status = els.statusFilter.value;
  const entries = state.entries.filter((item) => {
    const matchesStatus = status === "all" || item.status === status;
    const haystack = `${item.title_zh} ${item.title_en} ${item.node_id} ${item.content_zh}`.toLowerCase();
    return matchesStatus && (!query || haystack.includes(query));
  });
  els.recordList.textContent = "";
  if (!entries.length) { const empty = document.createElement("div"); empty.className = "empty"; empty.textContent = copy.noRecords; els.recordList.appendChild(empty); return; }
  entries.forEach((entry) => {
    const card = document.createElement("article"); card.className = `record-card ${entry.kind} ${entry.status}`;
    const top = document.createElement("div"); top.className = "record-top";
    const identity = document.createElement("div");
    const title = document.createElement("h3"); title.textContent = locale === "en" ? (entry.title_en || entry.title_zh) : entry.title_zh;
    const node = document.createElement("code"); node.textContent = entry.node_id;
    identity.append(title, node);
    const badge = document.createElement("span"); badge.className = `badge ${entry.status === "active" ? "ok" : "archived"}`; badge.textContent = entry.status === "active" ? copy.active : copy.archived;
    top.append(identity, badge);
    const description = document.createElement("p"); description.textContent = (locale === "en" ? (entry.content_en || entry.content_zh) : entry.content_zh) || copy.noDescription;
    const meta = document.createElement("div"); meta.className = "record-meta";
    const media = entry.media || [], completedMedia = media.filter((item) => item.vlm_status === "completed").length;
    [copy.floor(entry.floor), copy.kinds[entry.kind], copy.version(entry.version), entry.group_code ? copy.area(entry.group_code) : "", media.length ? copy.attachments(media.length) : "", media.length ? `VLM ${completedMedia}/${media.length}` : ""].filter(Boolean).forEach((text) => { const span = document.createElement("span"); span.textContent = text; meta.appendChild(span); });
    const actions = document.createElement("div"); actions.className = "record-actions";
    actions.append(actionButton(copy.edit, () => editEntry(entry)), actionButton(entry.status === "active" ? copy.archive : copy.restore, () => toggleArchive(entry), entry.status === "active"));
    card.append(top, description, meta, actions); els.recordList.appendChild(card);
  });
}

function actionButton(text, handler, danger = false) {
  const button = document.createElement("button"); button.type = "button"; button.className = `button small${danger ? " danger" : ""}`; button.textContent = text; button.addEventListener("click", handler); return button;
}

function editEntry(entry) {
  state.editingId = entry.id; els.formTitle.textContent = copy.editTitle(locale === "en" ? (entry.title_en || entry.title_zh) : entry.title_zh);
  els.floor.value = entry.floor; els.groupCode.value = entry.group_code || ""; els.nodeId.value = entry.node_id;
  els.geometry.value = JSON.stringify(entry.geometry); els.kind.value = entry.kind; els.titleZh.value = entry.title_zh;
  els.titleEn.value = entry.title_en; els.contentZh.value = entry.content_zh; els.contentEn.value = entry.content_en;
  els.tags.value = entry.tags.join(","); els.source.value = entry.source;
  els.entryForm.scrollIntoView({ behavior: "smooth" });
}

function resetEntryForm() {
  state.editingId = null; state.drawing = null; els.entryForm.reset(); els.geometry.value = ""; els.formTitle.textContent = copy.newEntry; document.querySelectorAll("canvas").forEach(drawCanvas);
}

async function toggleArchive(entry) {
  const action = entry.status === "active" ? "archive" : "restore";
  await request(`/api/admin/entries/${entry.id}/${action}`, { method: "POST" });
  toast(action === "archive" ? copy.archivedToast : copy.restoredToast); await load();
}

els.entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const geometry = JSON.parse(els.geometry.value || "null");
  if (!geometry || geometry.length < 3) { toast(copy.drawFirst); return; }
  const payload = {
    node_id: els.nodeId.value.trim().toUpperCase(), group_code: els.groupCode.value.trim().toUpperCase(),
    floor: Number(els.floor.value), geometry, kind: els.kind.value,
    title_zh: els.titleZh.value.trim(), title_en: els.titleEn.value.trim(),
    content_zh: els.contentZh.value.trim(), content_en: els.contentEn.value.trim(),
    tags: els.tags.value.split(/[,，]/).map((v) => v.trim()).filter(Boolean), source: els.source.value.trim(),
  };
  els.formStatus.textContent = copy.saving;
  try {
    const entry = state.editingId
      ? await request(`/api/admin/entries/${state.editingId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      : await request("/api/admin/entries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const files = Array.from(els.files.files);
    for (let index = 0; index < files.length; index += 1) {
      els.formStatus.textContent = copy.processing(index + 1, files.length);
      const data = new FormData(); data.append("file", files[index]);
      await request(`/api/admin/entries/${entry.id}/media?run_vlm=true`, { method: "POST", body: data });
    }
    toast(files.length ? copy.publishedVlm : copy.published);
    resetEntryForm(); await load();
  } catch (error) { toast(copy.saveFailed(error.message)); }
  finally { els.formStatus.textContent = ""; }
});

function renderVisits() {
  els.visitList.textContent = "";
  if (!state.visits.length) { const empty = document.createElement("div"); empty.className = "empty"; empty.textContent = copy.noVisits; els.visitList.appendChild(empty); return; }
  state.visits.forEach((visit) => {
    const card = document.createElement("article"); card.className = `visit-card ${visit.status}`;
    const title = document.createElement("h3"); title.textContent = visit.delegation_name;
    const meta = document.createElement("div"); meta.className = "record-meta";
    [visit.country, visit.institution, visit.preferred_language, visit.status === "active" ? copy.available : copy.archived].filter(Boolean).forEach((text) => { const span = document.createElement("span"); span.textContent = text; meta.appendChild(span); });
    const purpose = document.createElement("p"); purpose.textContent = visit.purpose || copy.noPurpose;
    card.append(title, meta, purpose);
    if (visit.status === "active") card.append(actionButton(copy.endVisit, async () => { await request(`/api/admin/visits/${visit.id}/archive`, { method: "POST" }); toast(copy.visitArchived); await load(); }, true));
    els.visitList.appendChild(card);
  });
}

els.visitForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const lines = $("#itinerary").value.split("\n").map((v) => v.trim()).filter(Boolean);
  const payload = {
    delegation_name: $("#delegationName").value.trim(), institution: $("#institution").value.trim(),
    country: $("#country").value.trim(), preferred_language: $("#preferredLanguage").value,
    purpose: $("#purpose").value.trim(), itinerary: lines.map((text, index) => ({ order: index + 1, text })),
    script_zh: $("#scriptZh").value.trim(), script_en: $("#scriptEn").value.trim(),
  };
  try { await request("/api/admin/visits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); els.visitForm.reset(); toast(copy.visitCreated); await load(); }
  catch (error) { toast(copy.createFailed(error.message)); }
});

els.drawButton.addEventListener("click", () => setDrawMode(!state.drawMode));
$("#reloadButton").addEventListener("click", load);
$("#resetForm").addEventListener("click", resetEntryForm);
els.searchInput.addEventListener("input", renderRecords);
els.statusFilter.addEventListener("change", renderRecords);

load().catch((error) => { els.healthBadge.textContent = copy.backendDown; els.healthBadge.className = "badge archived"; toast(error.message); });
