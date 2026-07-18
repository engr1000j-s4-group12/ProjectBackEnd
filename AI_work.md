# Task1:

将以下连接里的双语音频转化为文字稿，以他们的标题为文字稿的标题存入数据库中

https://gc.sjtu.edu.cn/audio-guide-2/
https://gc.sjtu.edu.cn/audio-guide-7/
https://gc.sjtu.edu.cn/audio-guide-6/
https://gc.sjtu.edu.cn/audio-guide-14/
https://gc.sjtu.edu.cn/audio-guide-12/
https://gc.sjtu.edu.cn/audio-guide-9/

目的：这些是学院公开的线下讲解资料，用于AI上下文的补充，以及讲解播报
请存入AI上下文读取的数据库中

# Task2

目前，导航系统虽然有，但是效果很一般，现在将调用后端导航服务更改为，直接将地图上传给Qwen VLM来进行寻路，也就是把寻路的功能更改为交给VLM

然后请你进行一些测试，输入出发点和终点查看是否能够正常工作，task2 包括测试


---

# Codex 执行记录（2026-07-18）

## Task1 音频讲解转写与入库

### 文稿存储位置

文稿已经写入本项目的 SQLite 数据库：

- 数据库文件：`data/guide.sqlite3`
- 主表：`knowledge_records`
- 空间节点表：`regions`
- 中文文稿字段：`knowledge_records.content_zh`
- 英文文稿字段：`knowledge_records.content_en`
- 标题字段：`knowledge_records.title_zh` / `knowledge_records.title_en`
- 来源与备注：`knowledge_records.source`
- 结构化来源信息：`knowledge_records.extracted_json`

可以用下面的查询查看所有已导入音频讲解记录：

```bash
/home/Hylia/workspace/Project-2/.venv/bin/python - <<'PY'
import sqlite3
conn = sqlite3.connect("data/guide.sqlite3")
conn.row_factory = sqlite3.Row
rows = conn.execute("""
SELECT kr.id, r.node_id, r.floor, kr.title_zh, kr.title_en,
       length(kr.content_zh) AS zh_len,
       length(kr.content_en) AS en_len,
       kr.status
FROM knowledge_records kr
JOIN regions r ON r.id = kr.region_id
WHERE r.node_id LIKE 'LB-%F-AUDIO-%'
ORDER BY kr.id
""").fetchall()
for row in rows:
    print(dict(row))
PY
```

### 已入库记录

| record_id | node_id | 楼层 | 中文标题 | 中文字数 | 英文字数 | 状态 |
|---:|---|---:|---|---:|---:|---|
| 9 | `LB-1F-AUDIO-LONGBIN-COMPLETION` | 1 | 龙宾楼落成志（一楼） | 343 | 1148 | active |
| 10 | `LB-1F-AUDIO-GRATITUDE-WALL` | 1 | 感恩墙（一楼） | 206 | 536 | active |
| 11 | `LB-1F-AUDIO-ALUMNI-NORTH` | 1 | 新时代的追光者系列：学术校友展（北侧）（一楼） | 189 | 585 | active |
| 12 | `LB-4F-AUDIO-JI-HISTORY` | 4 | 交大密西根学院院史（四楼） | 827 | 1599 | active |
| 13 | `LB-3F-AUDIO-SJTU-UM-HISTORY` | 3 | 交大密大合作史：百年携手，世纪跨越（三楼） | 1260 | 863 | active |
| 14 | `LB-3F-AUDIO-WATERCOLOR` | 3 | 芳华水彩组画（三楼） | 127 | 449 | active |

### 来源页面与音频

- `audio-guide-2`：https://gc.sjtu.edu.cn/audio-guide-2/
- `audio-guide-7`：https://gc.sjtu.edu.cn/audio-guide-7/
- `audio-guide-6`：https://gc.sjtu.edu.cn/audio-guide-6/
- `audio-guide-14`：https://gc.sjtu.edu.cn/audio-guide-14/
- `audio-guide-12`：https://gc.sjtu.edu.cn/audio-guide-12/
- `audio-guide-9`：https://gc.sjtu.edu.cn/audio-guide-9/

### 可重复执行脚本

- 导入脚本：`scripts/import_audio_guides.py`
- 脚本作用：重新调用 Qwen ASR，把公开音频转写并更新同一批数据库记录。
- 注意：文稿为 ASR 生成，已经在 `source` 和 `extracted_json` 中标记为 `unreviewed`，后续如需正式讲解稿，应人工校对后再改为已审核内容。

## Task2 Qwen VLM 地图寻路

### 后端实现位置

- 新增 VLM 地图寻路模块：`server/app/vlm_navigation.py`
- Qwen 地图寻路请求封装：`server/app/vlm.py`
- 普通导航接口接入位置：`server/app/main.py`
- 设备端导航接口接入位置：`server/app/device_api.py`
- 路线响应新增字段：`server/app/schemas.py`
  - `planner`
  - `confidence`
  - `assumptions`
- `/flow` 页面显示 planner：`server/app/static/flow_lab/app.js`
- `/flow` 通信图连线重绘：`server/app/static/flow_lab/index.html` 和 `server/app/static/flow_lab/styles.css`

### 当前寻路逻辑

- 默认优先使用 Qwen VLM 读取楼层地图生成路线。
- 如果 VLM 未配置或调用失败，非严格模式会回退到 SQLite 图算法。
- 设置 `VLM_ROUTE_STRICT=1` 后，VLM 失败会直接返回 502/503，便于测试真实失败原因。
- 同楼层路线：上传当前楼层地图给 Qwen VLM。
- 跨楼层路线：拆成两段 VLM 地图读取：
  - 起点楼层：起点到访客电梯。
  - 换层：后端固定生成访客电梯换层步骤。
  - 目标楼层：访客电梯到终点。
- 地图寻路超时使用 `VLM_ROUTE_TIMEOUT_SECONDS`，默认至少 180 秒。

### 可重复测试脚本

- 路线测试脚本：`scripts/check_vlm_route.py`

示例：

```bash
zsh -lic 'VLM_ROUTE_ENABLED=1 VLM_ROUTE_STRICT=1 VLM_ROUTE_TIMEOUT_SECONDS=180 /home/Hylia/workspace/Project-2/.venv/bin/python scripts/check_vlm_route.py 400A 429B'
```

```bash
zsh -lic 'VLM_ROUTE_ENABLED=1 VLM_ROUTE_STRICT=1 VLM_ROUTE_TIMEOUT_SECONDS=180 /home/Hylia/workspace/Project-2/.venv/bin/python scripts/check_vlm_route.py LB-1F-OPEN-08 429B'
```

### 真实 Qwen VLM 测试结果

#### 同楼层：`400A -> 429B`

- HTTP 状态：200
- planner：`qwen_vlm_map`
- from_id：`LB-4F-ROOM-400A`
- to_id：`LB-4F-ROOM-429B`
- total_distance_m：125.0
- confidence：0.9
- steps_count：6
- announcement：

```text
从400A房间出发，沿右侧走廊向北直行，随后向西穿过北走廊即可到达429B房间。
```

模型返回的主要备注：

- 起点和终点的坐标数据似乎与地图实际位置相反，路线按地图实际房间位置规划。
- 走廊连通性基于平面图视觉判断，实际通行可能受门禁或临时封闭影响。

#### 跨楼层：`LB-1F-OPEN-08 -> 429B`

- HTTP 状态：200
- planner：`qwen_vlm_map`
- from_id：`LB-1F-OPEN-08`
- to_id：`LB-4F-ROOM-429B`
- total_distance_m：117.0
- confidence：0.8
- steps_count：5
- announcement：

```text
请先前往访客电梯，乘坐电梯到四楼，出电梯后按地图路线前往429B房间。
```

模型返回的主要备注：

- 跨楼层路线已拆分为起点楼层和目标楼层两次 VLM 地图读取。
- 根据坐标判断 `LB-1F-ELEVATOR-GUEST` 位于地图右下角电梯区域。
- 路线沿南侧开放区域直行，无墙体阻隔。
- 访客电梯出口朝北。
- 429B 位于四楼西北侧，出电梯后需要向北再向西。

### 自动化验证

执行命令：

```bash
/home/Hylia/workspace/Project-2/.venv/bin/python -m pytest -q
```

结果：

```text
49 passed in 1.41s
```

新增测试文件：

- `tests/test_vlm_navigation.py`

覆盖内容：

- 同楼层 VLM 地图寻路会上传对应楼层图。
- `400A -> 429B` 能解析为 `LB-4F-ROOM-400A -> LB-4F-ROOM-429B`。
- 跨楼层路线会拆成 1F 地图读取、访客电梯换层、4F 地图读取。

### 本地服务验证

本地服务启动命令：

```bash
zsh -lic 'VLM_ROUTE_ENABLED=1 VLM_ROUTE_TIMEOUT_SECONDS=180 /home/Hylia/workspace/Project-2/.venv/bin/uvicorn server.app.main:app --host 127.0.0.1 --port 8000'
```

健康检查结果：

```text
http://127.0.0.1:8000/health 200 application/json
http://127.0.0.1:8000/flow 200 text/html; charset=utf-8
```

测试页面：

- http://127.0.0.1:8000/flow
