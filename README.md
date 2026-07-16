# 龙宾楼 VLM 智能导览后端

这是可直接部署到云端的龙宾楼智能导览服务。当前版本将管理 Console、四层楼地图、学院资料、活动/展览、代表团任务、VLM 定位、SQLite 导航和小智设备接口放在同一套 FastAPI 服务中。

## 当前能力

- 中文管理端常态展示 1–4 楼四幅平面图；
- 可直接在平面图上圈出展览范围，绑定节点 ID、标题、说明、标签和附件；
- 图片上传时只调用一次 VLM，将识别出的中英文说明、文字、对象和标签固化到 SQLite；
- 内容支持编辑、版本历史、归档与恢复；
- 区分长期信息、活动、展品、设施和代表团来访任务；
- Guide 查询数据库时默认只读取有效内容，已归档活动仍可通过显式历史查询获得；
- 提供 MCP JSON-RPC 入口和等价 HTTP 查询接口；
- 四层楼地图节点已经进入 SQLite，导航模块和管理端共享同一个数据库；
- 保留原有视觉定位、4F 确定性路线规划和中英文导航接口。
- 提供 `/api/device/v1` 小智终端接口、设备会话、紧凑路线播报和可选 Token 鉴权；
- 提供 Docker Compose 持久化部署和可选 Caddy HTTPS 入口。

已经初始化的区域包括：

- 1F A、B：浦江国际学院介绍；
- 1F C：学院建校展览；
- 1F D：教师及优秀学生展览（东西两侧）；
- 2F E：钢琴；
- 3F：李政道科学与艺术展览；
- 4F F：学院介绍墙。

`DevData` 中筛选出的 8 张李政道展览图片已经完成 VLM 预处理和去重入库。C 区以及后续展品的正式资料可直接由管理端补充。

## 快速启动

### 云端或正式演示（推荐）

```bash
cp .env.example .env
# 修改管理员密码、设备/MCP Token、VLM 配置和域名
docker compose up -d --build
```

使用域名和自动 HTTPS：

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build
```

SQLite 和上传附件保存在 Docker 命名卷 `guide_runtime`。首次启动会复制仓库内的当前数据库和已导入附件，重建容器不会丢失运行数据。

### 本地 Python 开发

需要 Python 3.11 或更高版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements-dev.txt
uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --reload
```

常用入口：

- 管理端：`http://127.0.0.1:8000/admin`
- English admin console: `http://127.0.0.1:8000/admin/en`
- API 文档：`http://127.0.0.1:8000/docs`
- 后端流程协作台：`http://127.0.0.1:8000/flow`
- MCP JSON-RPC：`POST http://127.0.0.1:8000/mcp`
- 小智设备能力：`GET http://127.0.0.1:8000/api/device/v1/capabilities`

配置 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 后，管理端使用 HTTP Basic Auth。配置 `DEVICE_API_TOKEN` 后，小智设备接口要求 Bearer Token；配置 `MCP_API_TOKEN` 后，`/mcp` 要求 Bearer Token。云端部署时这些值均应配置。

## VLM 配置

图片预处理读取以下环境变量：

```bash
export VLM_API_KEY="API 密钥"
export VLM_BASE_URL="VLM 接口地址"
export VLM_MODEL="模型名称"
```

程序支持 OpenAI Chat Completions 兼容地址，并会自动把阿里云 Model Studio 的 `/api/v1` 地址转换到 compatible-mode 地址。密钥只能保存在本机环境变量中，不会写入数据库、上传目录或错误响应。

VLM 只在管理者上传/重试图片时运行。Guide 日常问答直接检索已经固化的文字和标签，不会在每次查询时重新比对图片。

## 数据与文件

```text
data/guide.sqlite3                         管理端知识、区域、附件索引、来访任务和历史
data/building_map.json                     旧4F路网导入来源（运行时导航读取 SQLite）
data/exhibits.json                         原有展品演示数据
server/app/static/admin/maps/              四幅楼层底图
server/app/static/admin/uploads/           哈希命名的上传附件
server/app/knowledge.py                    SQLite 数据访问层
server/app/floor_map_seed.py               四层楼节点与旧路网迁移
server/app/admin_api.py                    管理和只读查询接口
server/app/mcp_api.py                      MCP JSON-RPC 入口
server/app/guide_persona.py                Guide Persona 与工具契约
scripts/import_devdata.py                  DevData 受控导入脚本
```

附件按 SHA-256 去重；数据库记录保存来源、VLM 状态、结构化识别结果和每次修改快照。管理端“保存”即发布，归档后 Guide 默认不再读取。

## MCP 工具

`POST /mcp` 支持 `initialize`、`tools/list` 和 `tools/call`。当前提供：

- `museum.search_knowledge`
- `museum.get_place_info`
- `museum.search_events`
- `museum.get_event`
- `museum.get_nearby_events`
- `museum.get_visitor_context`
- `museum.get_guide_context`
- `museum.search_map_nodes`
- `museum.get_map_node`
- `museum.plan_route`

示例：

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"museum.get_place_info","arguments":{"node_id":"LB-1F-REGION-A"}}}'
```

同一数据也可以通过 `/api/v1/knowledge/search`、`/api/v1/events` 和 `/api/v1/guide/context` 等 HTTP 接口读取。

## 小智设备接口

设备请求必须携带 `Device-Id`，建议同时携带 `Client-Id`、`Firmware-Version` 和 `Authorization: Bearer <DEVICE_API_TOKEN>`。主要接口：

- `GET /api/device/v1/capabilities`
- `POST /api/device/v1/session/start`
- `GET /api/device/v1/guide/context`
- `POST /api/device/v1/resolve-place`
- `POST /api/device/v1/localize/image`
- `POST /api/device/v1/localize/visual`
- `POST /api/device/v1/route`
- `GET /api/device/v1/knowledge/search`

设备路线默认不返回内部 `steps`，只返回可直接交给 TTS 的 `announcement`。无开发板时可运行：

```bash
python3 scripts/simulate_xiaozhi.py \
  --base-url http://127.0.0.1:8000 \
  --token "$DEVICE_API_TOKEN" \
  --floor 3
```

## Guide 行为边界

Guide 的默认风格是正式、专业和克制。语言由当前代表团任务决定；无任务时不读取或猜测个人资料。后台保留完整路线，但终端只播报简短 `announcement`，并通过周期性现场照片重新定位。Guide 对管理数据库只有读取权限。

## 验证

```bash
python3 -m pytest -q
python3 scripts/verify_api.py
python3 scripts/import_building_map_excel.py \
  --input data/building_map_nodes.xlsx --dry-run
```

当前基线为 46 项自动化测试、27 项端到端 API 检查。SQLite 地图表中各楼层有效节点数依次为 27、94、73、136；绿色路线和访客电梯连接均已写入 SQLite。导航接口返回内部 `steps` 与面向来宾的一句式 `announcement`，小智终端只播报后者。一楼西北侧误标为洗手间的位置已归档，并以不可进入的禁用电梯区域覆盖；访客电梯出口方向记录为朝北。

## 仍需现场完成

目前 1–3 楼的房间、开放空间和设施节点已经可从 SQLite/HTTP/MCP 查询，绿色标注覆盖的路线可以导航，但大部分房间门口和跨楼层连接仍未接入。4F 导航已经从 SQLite 读取，现有距离、转向和视觉地标仍包含基于图纸的估算。正式部署前需要：

- 实测 1–4 楼入口、走廊、楼梯、电梯和房间之间的距离与通行关系；
- 核对楼层底图中的房间编号与墙体边界；
- 采集关键节点多角度现场照片；
- 录入并审核 C 区及后续展览的权威中英文资料；
- 完成 ESP32-S3 与本机 `/mcp` 或对应 HTTP 接口的局域网联调。

地图 JSON/Excel 的维护方法和旧接口示例见 [使用指南.md](使用指南.md)。
