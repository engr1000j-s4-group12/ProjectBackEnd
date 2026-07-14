# 后端整合与完善工作计划

日期：2026-07-14
目标分支：`main`
待整合来源：`origin/yepincheng`
来源提交：`d8de65c feat: optimization of localize and routing API`

## 目标

把队友在 `origin/yepincheng` 上完成的后端内容整合到 `main`，并在整合时补齐维护性、数据一致性和测试验证问题。整合完成后，后端应至少支持：

- 4 楼节点、走廊、设施和房间数据加载；
- 任意连通节点之间的路线规划；
- 普通路线和无障碍路线；
- 展品 `ROBOT-001` 正确关联到 4 楼 400 房间；
- 视觉定位接口继续可用；
- 导航 API 文档可供小智端或测试脚本调用；
- Excel 数据维护流程不会覆盖掉走廊节点和路线边。

本计划只覆盖后端和数据层，不承担小智终端固件开发。

## 当前状态

当前 `main` 已有：

- FastAPI 后端；
- `Navigator` 最短路算法；
- `/api/v1/route` 路线接口；
- `/api/v1/localize`、`/api/v1/localize/visual`、`/api/v1/localize/image` 定位接口；
- `/api/v1/exhibits` 和展品上下文接口；
- 4 楼基础节点数据；
- Excel 节点模板和 Excel 导入脚本。

当前 `main` 的主要缺口：

- `data/building_map.json` 只有节点，没有 `edges`，因此不能实际生成两点路线；
- `data/exhibits.json` 仍引用旧节点时会导致数据加载失败；
- Excel 导入脚本目前只导入 nodes，并会把 `edges` 写成空数组；
- 测试仍有部分旧 1F/2F 演示数据假设。

队友分支新增：

| 类型 | 内容 |
|---|---|
| 地图数据 | 124 个节点，129 条边，12 个走廊节点，4 条不可无障碍边 |
| 展品数据 | `ROBOT-001` 关联到 `LB-4F-ROOM-400` |
| 文档 | `localize_route_guide.md`，面向定位和路线 API 调用 |
| 脚本 | 数据分析、地标优化、真实数据重建、API 验证脚本 |
| 测试 | API、导航、仓储、视觉定位测试改为 4F 场景 |

## 整合原则

1. **保留确定性导航算法**
   路线规划继续由 `Navigator` 基于图结构和 Dijkstra 完成，不交给 RAG 或 LLM 决策。

2. **接受 4F 路网数据，但标注估算性质**
   队友新增的走廊节点和边能让系统跑通导航，应合入；但距离仍是估算值，报告和数据备注中要保留“需实地校准”。

3. **保留 Excel 作为人工维护入口**
   但 Excel 不能只维护节点。整合后需要扩展为至少两张表：`nodes` 和 `edges`。导入脚本也要同步支持 `edges`，否则会破坏导航图。

4. **脚本要分类，不让旧演示数据误回流**
   队友新增脚本里有一部分仍含 `LB-1F-*`、`LB-2F-*`、`EXHIBIT-ROBOT` 等旧演示数据。整合时不能让这些脚本以“推荐工具”的身份留在主脚本目录。

5. **Project-2 作为参考资料，不直接覆盖当前仓库**
   后续工作会参考 `/home/Hylia/workspace/Project-2` 里的小智固件资料、后端说明和联调方案；当前代码整合仍以 `ProjectBackEnd` 为主。

## 计划步骤

### 1. 建立整合分支并保护工作区

先从 `main` 新建整合分支，例如：

```bash
git switch -c integration/yepincheng-backend
```

当前工作区中已有未跟踪文件：

- `Documents/team_updates_review_2026-07-14.md`
- `Documents/team_updates_review_2026-07-14.pdf`
- `Documents/backend_integration_plan_2026-07-14.md`
- `Documents/backend_integration_plan_2026-07-14.pdf`
- `data/使用指南.md`

整合时只处理明确属于本次工作的文件，不自动提交无关未跟踪文件。

### 2. 合入队友后端内容

从 `origin/yepincheng` 引入以下内容：

- `data/building_map.json`
- `data/exhibits.json`
- `localize_route_guide.md`
- `tests/test_api.py`
- `tests/test_navigation.py`
- `tests/test_repository.py`
- `tests/test_visual_localization.py`
- 有用脚本：`analyze_data.py`、`analyze_rooms.py`、`rebuild_real_data.py`、`optimize_landmarks.py`、`fix_landmarks_v2.py`、`verify_api.py`

对以下脚本不直接作为主流程工具合入：

- `fix_edges.py`
- `fix_landmarks.py`
- `merge_demo_data.py`

原因：这些脚本包含旧 1F/2F 演示节点和 `EXHIBIT-ROBOT`，误运行会污染当前 4F 数据。处理方式是移动到 `scripts/legacy/` 或改写为安全的历史参考脚本。

### 3. 完善地图数据维护流程

当前 Excel 文件 `data/building_map_nodes.xlsx` 只能描述节点。整合后要升级为：

- `nodes` 工作表：节点 ID、名称、楼层、类型、别名、备注、坐标、地标；
- `edges` 工作表：`from`、`to`、`distance_m`、`bidirectional`、`accessible`、中文/英文正反向指令；
- 可选 `metadata` 工作表：楼层、外轮廓尺寸、坐标系说明。

同时升级 `scripts/import_building_map_excel.py`：

- 读取 `nodes`；
- 读取 `edges`；
- 校验边引用的节点必须存在；
- 校验距离必须大于 0；
- 保留 `floor_plan`；
- 不再无条件清空 `edges`。

如时间允许，再新增一个反向导出脚本：

```text
scripts/export_building_map_excel.py
```

用于从 JSON 生成 Excel，避免 JSON 和 Excel 长期漂移。

### 4. 加强数据校验

在 `GuideRepository` 或独立脚本中补充校验：

- 所有 node ID 唯一；
- 所有 edge 引用存在；
- `distance_m > 0`；
- `accessible` 必须为 bool；
- `bidirectional` 必须为 bool；
- 每个节点必须有 `name_zh`、`name_en`、`floor`、`kind`；
- 每个房间节点必须有 `room_number` 或明确理由；
- 每个视觉地标必须有非空 `aliases`；
- 展品 `location_id` 必须引用存在节点；
- 全图至少有一个连通分量覆盖主要房间；
- 无障碍图中楼梯边不可通过。

这些校验应进入测试或 `scripts/analyze_data.py`，不是只靠人工观察。

### 5. 完善导航后端行为

现有 `Navigator` 已能生成路线。整合后建议补强：

- 对路线总距离做稳定的浮点格式处理；
- 对缺失手写 instruction 的边使用 fallback 指令；
- 在返回 steps 时保留 `from_id`、`to_id`、`distance_m`、`instruction`；
- 对不可达路线返回 422；
- 对未知地点返回 404；
- 保留中英文 instruction；
- 增加典型路线样例测试，例如 `400A -> 429B`、`400A -> 400`、楼梯无障碍失败。

### 6. 保留 VLM 和视觉定位的两条链路

后端继续支持两种方式：

```text
方案 A：测试图片 -> 后端 /api/v1/localize/image -> 后端调用 VLM
方案 B：外部/小智 VLM -> 结构化结果 -> /api/v1/localize/visual
```

你的测试工作可以完全脱离 terminal，只用 VLM API key、图片和用户发言模拟流程。

本次后端整合不需要实现小智固件工具，但要保证接口适合未来小智调用。

### 7. 整理文档

整合后更新：

- `README.md`：说明当前后端能力、如何运行、如何配置 VLM；
- `使用指南.md` 或 `localize_route_guide.md`：统一接口说明，避免重复或冲突；
- `Documents/后端.md`：如需保留课程报告，补充 4F 路网状态；
- 明确 `Project-2` 是参考资料，不是运行时依赖。

### 8. 测试与验收

整合后执行：

```bash
python3 -m pytest -q
python3 scripts/verify_api.py
python3 scripts/import_building_map_excel.py --input data/building_map_nodes.xlsx --output /tmp/building_map_check.json --dry-run
```

如果当前环境缺少依赖，则先使用项目虚拟环境或安装 `server/requirements-dev.txt`。

验收标准：

- 后端能启动；
- `/health` 返回正常；
- `/api/v1/places` 能列出 4F 节点；
- `/api/v1/route` 能生成 `400A -> 429B` 路线；
- `accessible_only=true` 能避开楼梯边；
- `/api/v1/exhibits/ROBOT-001/context` 能返回 4F 400 房间相关 facts；
- `/api/v1/localize/visual` 能通过房间号定位；
- JSON 和 Excel 导入流程不会丢失 edges；
- 测试通过，或者剩余失败项有明确原因。

## 预期交付物

整合完成后应产生：

- 更新后的 `data/building_map.json`；
- 更新后的 `data/exhibits.json`；
- 更新后的 `data/building_map_nodes.xlsx`，包含 nodes 和 edges；
- 升级后的 `scripts/import_building_map_excel.py`；
- 整理后的脚本目录；
- 更新后的导航、定位、展品测试；
- 后端调用文档；
- 一份最终整合说明。

## 风险与处理

| 风险 | 影响 | 处理 |
|---|---|---|
| Excel 导入覆盖 edges | 导航失效 | 升级 Excel 和导入脚本，加入 edges 表 |
| 旧演示脚本误运行 | 1F/2F 旧数据回流 | 移到 `scripts/legacy/` 或删除 |
| 距离为估算值 | 真实导航不准 | 在备注中标注，后续实测校准 |
| 视觉定位歧义 | 楼梯/卫生间等公共设施误识别 | 增加唯一地标、降低共享特征权重 |
| 测试依赖缺失 | 无法验证 | 使用 `.venv` 或安装 dev requirements |
| 文档重复 | 使用方混淆 | 合并 README、使用指南和 route guide 中冲突描述 |

## 工作概览

我会按“先整合可用能力，再修掉维护风险”的顺序推进：

1. 先把队友分支里能让导航跑起来的 4F 路网和测试接入当前 `main`。
2. 再修 Excel 导入链路，让地图不再出现“JSON 有边、Excel 没边”的漂移。
3. 然后清理脚本，把旧演示数据脚本隔离，避免误用。
4. 最后跑完整测试和 API 验证，给出整合结果和剩余问题。

完成后，后端应该具备一个可测试的完整闭环：

```text
图片或 VLM 特征
  -> 定位当前节点
  -> 用户目标解析
  -> 导航后端生成路线
  -> 展品/RAG 上下文补充
  -> 返回适合语音播报的结果
```
