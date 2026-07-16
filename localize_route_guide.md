# 定位与导航 API 调用文档

本文档面向小智 ESP32-S3 终端（固件岗位），覆盖 4 个核心接口的完整调用规范。

---

## 接口概览

| 方法 | 路径 | 用途 | 内容类型 |
|------|------|------|----------|
| `POST` | `/api/v1/localize` | 标记定位（二维码兜底） | `application/json` |
| `POST` | `/api/v1/localize/visual` | 结构化特征定位（推荐） | `application/json` |
| `POST` | `/api/v1/localize/image` | 图片上传定位 | `multipart/form-data` |
| `POST` | `/api/v1/route` | 路线规划 | `application/json` |

---

## 1. `POST /api/v1/localize` — 标记定位（二维码）

### 1.1 请求

```http
POST /api/v1/localize
Content-Type: application/json
```

```json
{
  "marker_id": "LB-4F-ROOM-400A"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `marker_id` | string | ✅ | 地点 ID、中文名、英文名或别名均可 |

### 1.2 响应

**成功 (200)：**

```json
{
  "node_id": "LB-4F-ROOM-400A",
  "name_zh": "400A房间",
  "name_en": "Room 400A",
  "floor": 4,
  "kind": "room",
  "confidence": 1.0
}
```

**失败：**

| 状态码 | 说明 |
|--------|------|
| `404` | 地点 ID 不存在 |

### 1.3 curl 示例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/localize \
  -H "Content-Type: application/json" \
  -d '{"marker_id":"LB-4F-ROOM-400A"}'
```

---

## 2. `POST /api/v1/localize/visual` — 结构化特征定位（推荐）

> ⚠️ **推荐方案**：如果小智端已有 VLM 能力，优先用此接口而非 `/api/v1/localize/image`，可减少一次图片上传和 VLM 调用。

### 2.1 请求

```http
POST /api/v1/localize/visual
Content-Type: application/json
```

```json
{
  "objects": [
    { "label": "西北侧楼梯", "confidence": 0.95 }
  ],
  "recognized_texts": ["西北侧楼梯", "4F"],
  "scene_description": "4楼西北角楼梯间，可见窗户外景",
  "floor_hint": 4
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `objects` | array | 否 | VLM 识别到的物体列表 |
| `objects[].label` | string | ✅ | 物体名称（中英文均可） |
| `objects[].confidence` | number | 否 | 识别置信度 0–1，默认 1 |
| `recognized_texts` | array\<string\> | 否 | VLM 识别到的文字（门牌号、标牌等） |
| `scene_description` | string | 否 | 场景的自然语言描述 |
| `floor_hint` | integer | 否 | 楼层号，能显著降低楼梯/电梯/相似房间的歧义 |

### 2.2 响应（matched — 精确定位成功）

```json
{
  "status": "matched",
  "node_id": "LB-4F-STAIRS-NORTHWEST",
  "confidence": 1.0,
  "needs_confirmation": false,
  "candidates": [
    {
      "node_id": "LB-4F-STAIRS-NORTHWEST",
      "name_zh": "西北侧楼梯",
      "name_en": "Northwest Stairs",
      "floor": 4,
      "score": 1.0,
      "matched_features": ["西北侧楼梯"]
    }
  ],
  "evidence": { "objects": [...], "recognized_texts": [...], ... }
}
```

### 2.3 响应（ambiguous — 位置不明确）

```json
{
  "status": "ambiguous",
  "node_id": null,
  "confidence": 0.167,
  "needs_confirmation": true,
  "candidates": [
    { "node_id": "LB-4F-STAIRS-NORTHWEST", "name_zh": "西北侧楼梯", "score": 0.167 },
    { "node_id": "LB-4F-STAIRS-NORTHEAST", "name_zh": "东北侧楼梯", "score": 0.167 },
    { "node_id": "LB-4F-STAIRS-SOUTHEAST", "name_zh": "东南侧楼梯", "score": 0.167 }
  ],
  "evidence": { ... }
}
```

### 2.4 响应（not_found — 无法定位）

```json
{
  "status": "not_found",
  "node_id": null,
  "confidence": 0.0,
  "needs_confirmation": true,
  "candidates": [],
  "evidence": { ... }
}
```

### 2.5 三种状态的处理约定

| `status` | 含义 | 设备端应如何响应 |
|----------|------|------------------|
| `matched` | 找到明显优于其他地点的候选 | 若 `needs_confirmation=false`，直接使用 `node_id` 规划路线；若 `needs_confirmation=true`，播报位置并确认 |
| `ambiguous` | 多个地点得分接近 | 播报 `candidates` 中前几个位置，让用户确认或要求重新拍照 |
| `not_found` | 没有足够视觉证据 | 提示用户重新拍照，或建议扫描二维码兜底 |

### 2.6 curl 示例

```bash
# 精确定位 — 识别到唯一房间号
curl -X POST http://127.0.0.1:8000/api/v1/localize/visual \
  -H "Content-Type: application/json" \
  -d '{"objects":[{"label":"413A","confidence":0.98}],"floor_hint":4}'

# 歧义场景 — 仅识别到"楼梯"
curl -X POST http://127.0.0.1:8000/api/v1/localize/visual \
  -H "Content-Type: application/json" \
  -d '{"objects":[{"label":"楼梯","confidence":0.95}]}'

# 楼层提示缩小范围
curl -X POST http://127.0.0.1:8000/api/v1/localize/visual \
  -H "Content-Type: application/json" \
  -d '{"objects":[{"label":"楼梯","confidence":0.95}],"floor_hint":4}'
```

---

## 3. `POST /api/v1/localize/image` — 图片上传定位

### 3.1 请求

```http
POST /api/v1/localize/image
Content-Type: multipart/form-data
```

| 表单字段 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| `image` | file | ✅ | JPEG、PNG 或 WebP 图片，最大 5 MiB |
| `floor_hint` | integer | 否 | 楼层号 |

### 3.2 响应

与 `/api/v1/localize/visual` 完全相同（返回 `VisualLocalizationResponse`）。

### 3.3 错误码（仅本接口独有）

| 状态码 | 说明 |
|--------|------|
| `400` | 图片内容为空 |
| `413` | 图片超过 5 MiB |
| `415` | 图片格式不支持（仅允许 JPEG/PNG/WebP） |
| `502` | VLM 响应异常 |
| `503` | VLM 服务未配置或不可用 |

### 3.4 curl 示例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/localize/image \
  -F "image=@现场照片.jpg" \
  -F "floor_hint=4"
```

---

## 4. `POST /api/v1/route` — 路线规划

### 4.1 请求

```http
POST /api/v1/route
Content-Type: application/json
```

```json
{
  "from_location": "LB-4F-ROOM-400A",
  "to_location": "LB-4F-ROOM-429B",
  "language": "zh",
  "accessible_only": false
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `from_location` | string | ✅ | — | 起点，支持 ID / 中文名 / 英文名 / 别名 |
| `to_location` | string | ✅ | — | 终点，同上 |
| `language` | string | 否 | `"zh"` | `"zh"` 返回中文指令，`"en"` 返回英文指令 |
| `accessible_only` | boolean | 否 | `false` | `true` = 仅走无障碍通道；`false` = 走最短路径 |

### 4.2 响应（成功）

```json
{
  "from_id": "LB-4F-ROOM-400A",
  "to_id": "LB-4F-ROOM-429B",
  "total_distance_m": 127.3,
  "announcement": "429B房间就在您所在的四楼。",
  "steps": [
    {
      "from_id": "LB-4F-ROOM-400A",
      "to_id": "LB-4F-CORRIDOR-N1",
      "distance_m": 7.1,
      "instruction": "前进 7.1 米到达北走廊西段。"
    },
    {
      "from_id": "LB-4F-CORRIDOR-N1",
      "to_id": "LB-4F-CORRIDOR-M1",
      "distance_m": 16.0,
      "instruction": "前进 16 米到达中北走廊西段。"
    },
    {
      "from_id": "LB-4F-CORRIDOR-SOUTH3",
      "to_id": "LB-4F-ROOM-429B",
      "distance_m": 10.0,
      "instruction": "前进 10 米到达429B房间。"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `from_id` | 解析后的起点 ID |
| `to_id` | 解析后的终点 ID |
| `total_distance_m` | 总距离（米） |
| `announcement` | 面向来宾的最终播报，设备交给 TTS |
| `steps` | 后台重新定位和调试使用的完整分段，不逐段播报 |
| `steps[].from_id` | 本段起点 |
| `steps[].to_id` | 本段终点 |
| `steps[].distance_m` | 本段距离（米） |
| `steps[].instruction` | 后台分段说明 |

**起点 = 终点** 时：`total_distance_m = 0`，`steps = []`。

### 4.3 响应（失败）

| 状态码 | 含义 | 响应体示例 |
|--------|------|-----------|
| `404` | 起点或终点不存在 | `{"detail":"未知地点：xxx"}` |
| `422` | 两点间无满足条件的路线 | `{"detail":"从 xxx 到 xxx 不存在满足条件的路线"}` |

### 4.4 设备端处理建议

| 情况 | 处理方式 |
|------|----------|
| `total_distance_m == 0` | 提示用户"您已在目的地" |
| `announcement` 非空 | 只播报 `announcement`；移动后重新定位并重新规划 |
| `404` | 提示"该地点暂未录入系统" |
| `422` | 提示"无法到达，请尝试关闭无障碍模式或选择其他目的地" |

### 4.5 curl 示例

```bash
# 中文普通路线
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "from_location": "LB-4F-ROOM-400A",
    "to_location": "LB-4F-ROOM-429B",
    "language": "zh",
    "accessible_only": false
  }'

# 英文无障碍路线
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "from_location": "LB-4F-ROOM-400A",
    "to_location": "LB-4F-ROOM-429B",
    "language": "en",
    "accessible_only": true
  }'

# 使用别名
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{"from_location":"400A","to_location":"429B","language":"zh"}'

# 起点=终点（边界情况）
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{"from_location":"LB-4F-ROOM-400","to_location":"LB-4F-ROOM-400"}'

# 地点不存在
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{"from_location":"火星","to_location":"LB-4F-ROOM-400"}'

# 无障碍模式下楼梯之间不可达
curl -X POST http://127.0.0.1:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "from_location": "LB-4F-STAIRS-NORTHWEST",
    "to_location": "LB-4F-STAIRS-SOUTHEAST",
    "language": "zh",
    "accessible_only": true
  }'
```

---

## 5. 推荐的前端调用流程

```text
1. 用户触发导航
      ↓
2. ESP32 拍摄照片
      ↓
3. 方案 A: POST /api/v1/localize/image  （后端自行调用 VLM）
   方案 B: 小智 VLM 提取特征 → POST /api/v1/localize/visual  （推荐）
      ↓
4. 收到定位结果：
   - matched + needs_confirmation=false → 跳至第5步
   - matched + needs_confirmation=true → 播报位置，让用户确认
   - ambiguous → 播报候选位置，让用户选择或重拍
   - not_found → 提示重拍，或引导扫描二维码（方案 C）
      ↓
5. 确认目的地 → POST /api/v1/route
      ↓
6. 收到 announcement → 直接交给 TTS；移动后重新拍照定位
```

**方案 C（兜底）**：若视觉定位失败，提示用户到最近的二维码标记处，调用：
`POST /api/v1/localize` `{"marker_id":"LB-4F-STAIRS-NORTHWEST"}`

---

## 6. 可用地点速查

前端可用 `GET /api/v1/resolve?q=名称` 验证地点是否已录入系统：

```bash
curl http://127.0.0.1:8000/api/v1/resolve?q=400A房间
# → {"node_id":"LB-4F-ROOM-400A"}
```

全部地点列表：`GET /api/v1/places`

---

## 7. 超时与重试建议

| 接口 | 建议超时 | 说明 |
|------|----------|------|
| `/api/v1/localize` | 3 s | 纯本地查表 |
| `/api/v1/localize/visual` | 3 s | 纯本地计算 |
| `/api/v1/localize/image` | 60 s | 含 VLM 远程调用 |
| `/api/v1/route` | 5 s | Dijkstra 本地计算，通常 < 10 ms |

VLM 相关错误（502/503）建议间隔 3 秒重试，最多 2 次。
