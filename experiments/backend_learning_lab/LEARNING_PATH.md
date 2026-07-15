# 学习路线：把后端架构拆开理解

你不需要一次看懂整个后端。建议每次只理解一个问题。

## 0. 先建立一个心智模型

当前后端不是“AI 魔法”，主链路其实是：

```text
用户输入
  -> 解析当前位置和目的地
  -> 在 building_map.json 里找到节点
  -> 在 edges 图里搜索路线
  -> 返回导航步骤
```

VLM 目前只是辅助：

```text
图片
  -> VLM/OCR 提取文字和物体
  -> 后端拿这些证据匹配 visual_landmarks
  -> 得到候选节点
```

## 1. 看懂数据，不看 API

运行：

```bash
python3 experiments/backend_learning_lab/01_inspect_data.py
```

你需要能回答：

- `nodes` 是什么？
- `edges` 是什么？
- 为什么地图可以被看成一张图？
- 房间、走廊、楼梯、电梯在数据里有什么区别？

建议你改：

- 把脚本里的 `nodes[:5]` 改成 `nodes[:20]`；
- 观察不同 `kind` 的节点字段有什么不同。

## 2. 看懂“用户说的话”如何变成 node_id

运行：

```bash
python3 experiments/backend_learning_lab/02_alias_resolver.py 413A
python3 experiments/backend_learning_lab/02_alias_resolver.py 413A房间
python3 experiments/backend_learning_lab/02_alias_resolver.py LB-4F-ROOM-413A
```

你需要能回答：

- 为什么同一个地点有多个别名？
- 为什么 API 不应该要求用户只说完整 `node_id`？
- 如果用户说“机器人展品”，现在能不能直接解析到地点？

建议你改：

- 去 `data/building_map.json` 找一个房间；
- 临时给它加一个别名；
- 再运行脚本看解析是否成功。

## 3. 看懂路线规划

运行：

```bash
python3 experiments/backend_learning_lab/03_route_planner.py LB-4F-ROOM-400A LB-4F-ROOM-429B
```

再运行：

```bash
python3 experiments/backend_learning_lab/03_route_planner.py LB-4F-STAIRS-NORTHWEST LB-4F-STAIRS-SOUTHEAST --accessible
```

你需要能回答：

- Dijkstra 算法的输入是什么？
- 路线总距离从哪里来？
- `accessible_only` 为什么会让某些路线不可达？

建议你改：

- 找一条 edge，把 `distance_m` 临时改大；
- 再运行脚本，看最短路是否变化。

## 4. 看懂视觉定位为什么不可靠

运行：

```bash
python3 experiments/backend_learning_lab/04_visual_matcher.py --text 413A
python3 experiments/backend_learning_lab/04_visual_matcher.py --text 西北侧楼梯
python3 experiments/backend_learning_lab/04_visual_matcher.py --text 消防栓
```

你需要能回答：

- 为什么只看“消防栓”很容易匹配到很多地点？
- 为什么“房间号 OCR”比“场景理解”更可靠？
- 为什么 ambiguity 时应该让用户确认？

建议你改：

- 给某个节点添加更独特的 `visual_landmarks`；
- 再运行脚本，看候选排序是否更明确。

## 5. 看懂 API JSON

运行：

```bash
python3 experiments/backend_learning_lab/05_api_payloads.py
```

你需要能回答：

- `/api/v1/localize` 和 `/api/v1/localize/visual` 的区别是什么？
- `/api/v1/route` 需要哪些字段？
- 展品 `/context` 返回的是最终答案，还是给 LLM/RAG 的上下文？

## 一个原则

以后遇到后端问题，先不要直接问 Codex “帮我修”。先按这个顺序定位：

```text
数据是否存在？
别名能否解析？
边是否连通？
路线是否可达？
视觉证据是否足够唯一？
API JSON 是否符合 schema？
```

你能回答这六个问题时，就不是只依赖 Codex 了。
