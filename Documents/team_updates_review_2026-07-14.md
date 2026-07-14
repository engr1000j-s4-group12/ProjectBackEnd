# 队友新增内容联合检查报告

检查时间：2026-07-14
当前仓库：`/home/Hylia/workspace/ProjectBackEnd`
关联仓库：`/home/Hylia/workspace/Project-2`

## 结论摘要

这次重新检查后，需要修正上一版报告中的一个判断：

仅看 `ProjectBackEnd` 时，远端新内容只看到 `origin/yepincheng` 上的一个提交：

- `d8de65c`，作者 `AetherWish <aiden2007@126.com>`，主题 `feat: optimization of localize and routing API`

但结合 `Project-2` 的 `origin/backend-api` 分支后，确实能看到多个人分别做了后端、导航、展品介绍和固件 MCP 相关工作。`backend-api` 分支相对 `origin/main` 有 `7` 个提交，涉及 `17` 个文件，约 `1732` 行新增、`86` 行删除。

按提交记录看，最接近你说的“两个人分别做 navigator 和 exhibit 介绍”的对应关系是：

- Navigator / route 相关：`AetherWish` 在 `8b617c0` 做过 `museum.plan_route` MCP 工具，但随后在 `b80c59c` 被同一作者 revert；当前最终分支中可用的 `museum.plan_route` 更主要来自 `churuijun` 后续的固件 MCP/客户端集成提交。
- Exhibit 介绍 / exhibit MCP 相关：`Yingyan Wang <wynnwang@sjtu.edu.cn>` 在 `21f1cef`、`23dbfc9`、`75cade9` 中集中完成了展品数据、展品解析接口、展品 context、文档等工作。
- 后端 API 与固件客户端集成：`churuijun <churuijun@gmail.com>` 在 `e2ec0aa`、`2fe7613` 中补了 MCP server、museum client 和相机/图片定位相关代码。

因此，修正后的判断是：**如果只看 ProjectBackEnd，不是两个人分别 commit；如果联合 Project-2/backend-api，看得到多人分工，其中 exhibit 明确由 Yingyan Wang 提交，navigator/route 相关历史上有 AetherWish 的提交，但最终可用实现还包含 churuijun 的集成工作。**

## 一、ProjectBackEnd 检查结果

### 1. 分支和提交

`ProjectBackEnd` 当前 `origin/main` 没有新提交；远端另有：

| 分支 | 提交 | 作者 | 内容 |
|---|---|---|---|
| `origin/yepincheng` | `d8de65c` | `AetherWish <aiden2007@126.com>` | `feat: optimization of localize and routing API` |

### 2. 主要内容

`origin/yepincheng` 相对当前 `main`：

- 修改 `data/building_map.json`
- 修改 `data/exhibits.json`
- 新增 `localize_route_guide.md`
- 新增多份 `scripts/*.py`
- 修改测试

数据层变化：

| 指标 | 数量 |
|---|---:|
| 总节点 | 124 |
| 房间节点 | 89 |
| 走廊节点 | 12 |
| 路径边 | 129 |
| 可无障碍边 | 125 |
| 不可无障碍边 | 4 |

这个分支把你之前生成的 4F 房间节点补成了可导航图：新增走廊节点和边，从 `LB-4F-ROOM-400A` 到 `LB-4F-ROOM-429B` 可规划出约 `127.3m`、`7` 步的路线。

### 3. ProjectBackEnd 风险

最大风险仍然是 Excel 数据源没有同步：

- `data/building_map_nodes.xlsx` 没有包含走廊节点和边。
- `scripts/import_building_map_excel.py` 导入时会把 `edges` 写成空数组。

如果后续继续用 Excel 作为地图数据主源，需要把走廊节点和边也放入 Excel，或至少增加第二张 `edges` 表。

另外，部分新增脚本仍含旧 1F/2F 演示数据：

- `scripts/fix_edges.py`
- `scripts/fix_landmarks.py`
- `scripts/merge_demo_data.py`

这些脚本可能把旧的 `LB-1F-*`、`LB-2F-*`、`EXHIBIT-ROBOT` 写回数据，建议合并前隔离或删除。

## 二、Project-2/backend-api 检查结果

### 1. 分支提交列表

`Project-2` 的 `origin/backend-api` 分支相对 `origin/main` 有以下提交：

| 提交 | 作者 | 日期 | 主题 |
|---|---|---|---|
| `8b617c0` | `AetherWish <aiden2007@126.com>` | 2026-07-07 | `feat: add MCP tool museum.plan_route` |
| `b80c59c` | `AetherWish <aiden2007@126.com>` | 2026-07-07 | `Revert "feat: add MCP tool museum.plan_route"` |
| `21f1cef` | `Yingyan Wang <wynnwang@sjtu.edu.cn>` | 2026-07-10 | `feat: add exhibits mcp` |
| `23dbfc9` | `Yingyan Wang <wynnwang@sjtu.edu.cn>` | 2026-07-10 | `upd exhibit mcp` |
| `75cade9` | `Yingyan Wang <wynnwang@sjtu.edu.cn>` | 2026-07-11 | `update guide` |
| `e2ec0aa` | `churuijun <churuijun@gmail.com>` | 2026-07-12 | `Backend almost completed, without image-localization` |
| `2fe7613` | `churuijun <churuijun@gmail.com>` | 2026-07-13 | `well done` |

这说明 `Project-2/backend-api` 不是单人提交，而是至少三个人参与了该分支。

### 2. 文件变化

相对 `origin/main`：

| 类型 | 文件 |
|---|---|
| 后端数据 | `data/building_map.json`, `data/exhibits.json` |
| 后端接口 | `server/app/main.py`, `server/app/repository.py`, `server/app/schemas.py`, `server/app/visual_localization.py` |
| 文档 | `guide.md` |
| 测试 | `tests/test_api.py`, `tests/test_repository.py` |
| 固件/MCP | `xiaozhi-esp32/main/mcp_server.cc`, `museum_client.cpp`, `museum_client.h`, `mcp_controller.cc`, 相机相关文件 |

总体变化为 `17` 个文件、约 `1732` 行新增、`86` 行删除。

### 3. 展品介绍内容

`Project-2/backend-api` 的 `data/exhibits.json` 已经不是 `ROBOT-001` 单个模拟展品，而是 4 个展品：

| exhibit id | 中文名 | location_id |
|---|---|---|
| `BLUE-TIGER-STATUE` | 蓝虎雕像 | `LB-1F-ENTRANCE` |
| `ALUMNI-HOME` | 校友之家 | `LB-1F-LOBBY` |
| `TSUNG-DAO-LEE-EXHIBIT` | 李政道展 | `LB-3F-LOBBY` |
| `PIANO-LOBBY` | 大厅钢琴 | `LB-2F-LOBBY` |

这些内容比 `ProjectBackEnd/origin/yepincheng` 的 `ROBOT-001` 占位介绍更接近“展品介绍”任务。每个展品都有：

- `name_zh` / `name_en`
- `summary_zh` / `summary_en`
- `facts_zh` / `facts_en`
- 绑定位置 `location_id`

因此，上一版报告中“exhibit 只是占位修复”的判断只适用于 `ProjectBackEnd`；如果把 `Project-2/backend-api` 纳入分析，展品介绍部分已经有较完整的数据和接口工作。

### 4. 导航 / Navigator 内容

`Project-2/backend-api` 的 `data/building_map.json` 仍是较小的演示地图：

| 指标 | 数量 |
|---|---:|
| 节点 | 10 |
| 边 | 8 |
| 楼层 | 1、2、3 |
| 主要类型 | entrance、checkpoint、stairs、elevator、exhibit |

它不包含 `ProjectBackEnd` 中的 4F 真实房间图，也没有 124 个节点/129 条边的 4F 导航网络。

但 `backend-api` 在接口和固件侧补了 route/MCP 调用能力：

- FastAPI 后端保留路线规划接口。
- 固件侧新增或扩展 `museum_client.cpp/h`。
- `mcp_server.cc` 中可见 `museum.plan_route`、`museum.visual_localize`、`museum.list_places`、`museum.resolve_place`、`museum.resolve_exhibit` 等工具注册。

因此它更像是“后端 API + 固件 MCP 调用链路”的实现，不是 4F 实地图数据实现。

### 5. 后端测试验证

我把 `Project-2/origin/backend-api` 导出到 `/tmp`，使用 `Project-2` 自带 `.venv` 跑了后端测试：

```text
28 个测试：19 passed，9 failed
```

失败集中在两类：

1. 测试仍然期待旧的 `ROBOT-001` / `EXHIBIT-ROBOT`。
2. 视觉定位 lobby 置信度从测试要求的 `>0.8` 降到了 `0.65`。

这说明 `backend-api` 分支的数据和测试没有完全同步。展品数据已经换成 `BLUE-TIGER-STATUE`、`ALUMNI-HOME` 等，但部分测试仍在验证旧模拟展品。

## 三、两个仓库如何互补

两个仓库的信息不是同一套数据，不能直接互相覆盖：

| 项目 | 优势 | 问题 |
|---|---|---|
| `ProjectBackEnd/origin/yepincheng` | 4F 地图数据最完整，有 124 节点和 129 条边，可做真实 4F 导航演示。 | 展品内容仍偏占位；Excel 模板和导入脚本未同步；部分脚本残留旧 demo 逻辑。 |
| `Project-2/origin/backend-api` | 展品介绍更完整；后端 exhibit resolve/context 接口和固件 MCP 调用链路更完整。 | 地图仍是小型 1/2/3 楼演示数据；测试与新展品数据不一致，当前 pytest 有 9 个失败。 |

建议的融合方式：

1. 以 `ProjectBackEnd/origin/yepincheng` 的 4F `building_map.json` 作为当前地图主数据。
2. 借用 `Project-2/origin/backend-api` 的展品数据结构和 exhibit resolve/context 接口设计。
3. 将 `Project-2` 的 4 个展品迁移到当前地图前，必须先确认这些 `location_id` 在当前地图中存在，或者建立新的 4F 对应点。
4. 借用 `Project-2` 的 `museum_client.cpp/h` 和 MCP 工具设计时，需要适配当前后端接口路径和数据 ID。
5. 修复测试：不要继续混用 `ROBOT-001 / EXHIBIT-ROBOT` 与新展品数据。
6. 同步更新 Excel 模板和导入脚本，防止 4F 导航边丢失。

## 四、修正后的人员判断

如果问题是“是否有两个人分别做 navigator 和 exhibit 介绍”，基于两个仓库的联合检查，答案是：

**有多人参与，但不是简单的两个人各自一个 commit。**

更准确地说：

- `AetherWish`：在 `ProjectBackEnd/origin/yepincheng` 中提交了 4F 本地化和路由优化；在 `Project-2/backend-api` 中也有一次 `museum.plan_route` 尝试，但随后自己 revert。
- `Yingyan Wang`：在 `Project-2/backend-api` 中明显负责 exhibit 相关工作，包括 `exhibits.json`、展品解析、展品 context 和文档更新。
- `churuijun`：在 `Project-2/backend-api` 中完成较多后端/固件集成工作，包括 `museum_client`、`mcp_server`、相机和图片定位相关代码。

因此，如果要在报告或答辩中描述分工，建议写成：

“导航和定位数据主要来自 `ProjectBackEnd` 分支的 4F 地图与路由优化；展品介绍和展品问答接口主要参考 `Project-2/backend-api` 中 Yingyan Wang 的 exhibit MCP 相关提交；固件端 MCP 调用链路由 churuijun 的提交进一步集成。”

## 五、建议的下一步

1. 不要直接把两个分支机械合并。
2. 先选择当前项目的数据主线：建议以 4F 地图为主线。
3. 把 `Project-2` 的 exhibit 结构迁移到当前项目，但重新绑定到当前地图节点。
4. 清理旧的 `ROBOT-001 / EXHIBIT-ROBOT` 测试和脚本。
5. 修复 Excel 导入流程，使它能保留或导入 `edges`。
6. 合并前跑完整后端测试，并确保 `pytest` 全绿。
