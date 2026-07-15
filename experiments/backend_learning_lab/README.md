# Backend Learning Lab

这个目录是实验性质的学习区，不参与正式后端服务启动，也不修改 `data/` 里的主数据。

目标是把现在后端的核心结构拆成几个能单独运行的小实验：

```text
JSON 地图数据
  -> 节点和边
  -> 别名解析
  -> 图搜索路线
  -> 视觉证据匹配
  -> API 请求 JSON
```

## 为什么要有这个目录

正式后端代码已经有 `server/app/repository.py`、`navigation.py`、`visual_localization.py` 等模块，但这些模块是“工程实现”。如果直接看它们，容易只知道调用函数，不知道背后的数据结构。

这个目录用更小、更直接的脚本复现同样的思想：

- `common.py`：公共读取和索引函数；
- `01_inspect_data.py`：看清楚 `building_map.json` 里到底有什么；
- `02_alias_resolver.py`：理解房间号、中文名、英文名如何解析成 `node_id`；
- `03_route_planner.py`：用 Dijkstra 从两点生成路线；
- `04_visual_matcher.py`：模拟视觉定位，不依赖真实 VLM；
- `05_api_payloads.py`：生成前端/终端会发给后端的 JSON。

## 运行方式

在仓库根目录运行：

```bash
python3 experiments/backend_learning_lab/01_inspect_data.py
python3 experiments/backend_learning_lab/02_alias_resolver.py 400A房间
python3 experiments/backend_learning_lab/03_route_planner.py LB-4F-ROOM-400A LB-4F-ROOM-429B
python3 experiments/backend_learning_lab/04_visual_matcher.py --text 413A --text 西北侧楼梯
python3 experiments/backend_learning_lab/05_api_payloads.py
```

## 学习顺序

1. 先跑 `01_inspect_data.py`，确认地图是“节点 + 边”的图结构。
2. 再跑 `02_alias_resolver.py`，理解用户不会总是说完整节点 ID，所以需要别名索引。
3. 然后跑 `03_route_planner.py`，看最短路径如何从边的距离累加出来。
4. 再跑 `04_visual_matcher.py`，理解目前视觉定位只是“证据匹配”，不是可靠定位。
5. 最后跑 `05_api_payloads.py`，看终端、网页和后端之间传递的 JSON 长什么样。

## 注意

这里的代码故意写得直白，不追求复用和工程抽象。你可以随便改这些脚本做实验，但不要把实验脚本当作生产逻辑。
