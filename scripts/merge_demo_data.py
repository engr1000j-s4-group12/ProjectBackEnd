"""
将演示导航数据（节点+边）合并到当前 building_map.json 中。
保留所有 4F 真实数据，同时补回使 route API 工作的演示路径。
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAP_FILE = DATA_DIR / "building_map.json"

# ============================================================
# 演示导航节点（保留原始 demo 数据以便 route API 工作）
# ============================================================
DEMO_NODES = [
    {
        "id": "LB-1F-ENTRANCE",
        "name_zh": "一楼主入口",
        "name_en": "First-floor Main Entrance",
        "floor": 1,
        "kind": "entrance",
        "aliases": ["入口", "main entrance", "主入口"],
        "visual_landmarks": [
            {"aliases": ["龙宾楼门牌", "Longbin Building sign", "龙宾楼"], "weight": 4},
            {"aliases": ["玻璃双开门", "glass double doors"], "weight": 2},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-1F-LOBBY",
        "name_zh": "一楼大厅",
        "name_en": "First-floor Lobby",
        "floor": 1,
        "kind": "lobby",
        "aliases": ["大厅", "lobby", "一楼大厅"],
        "visual_landmarks": [
            {"aliases": ["服务台", "reception desk", "前台"], "weight": 5},
            {"aliases": ["龙宾楼大厅", "Longbin lobby"], "weight": 3},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-1F-STAIRS",
        "name_zh": "一楼楼梯口",
        "name_en": "First-floor Stairs",
        "floor": 1,
        "kind": "stairs",
        "aliases": ["楼梯", "stairs", "一楼楼梯"],
        "visual_landmarks": [
            {"aliases": ["楼梯标识", "stairs sign", "安全出口"], "weight": 4},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-1F-ELEVATOR",
        "name_zh": "一楼电梯",
        "name_en": "First-floor Elevator",
        "floor": 1,
        "kind": "elevator",
        "aliases": ["电梯", "elevator", "lift", "一楼电梯"],
        "visual_landmarks": [
            {"aliases": ["电梯按钮", "elevator button", "楼层显示屏"], "weight": 5},
            {"aliases": ["银色电梯门", "silver elevator door"], "weight": 3},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-2F-STAIRS",
        "name_zh": "二楼楼梯口",
        "name_en": "Second-floor Stairs",
        "floor": 2,
        "kind": "stairs",
        "aliases": ["二楼楼梯", "2F stairs"],
        "visual_landmarks": [
            {"aliases": ["2F标识", "2F sign", "二楼楼梯间"], "weight": 4},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-2F-ELEVATOR",
        "name_zh": "二楼电梯",
        "name_en": "Second-floor Elevator",
        "floor": 2,
        "kind": "elevator",
        "aliases": ["二楼电梯", "2F elevator"],
        "visual_landmarks": [
            {"aliases": ["二楼电梯按钮", "2F elevator panel"], "weight": 4},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-2F-CORRIDOR-A",
        "name_zh": "二楼走廊A",
        "name_en": "Second-floor Corridor A",
        "floor": 2,
        "kind": "corridor",
        "aliases": ["走廊A", "corridor A", "二楼走廊"],
        "visual_landmarks": [
            {"aliases": ["走廊指示牌", "corridor sign"], "weight": 2},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "LB-2F-CORRIDOR-B",
        "name_zh": "二楼走廊B",
        "name_en": "Second-floor Corridor B",
        "floor": 2,
        "kind": "corridor",
        "aliases": ["走廊B", "corridor B"],
        "visual_landmarks": [
            {"aliases": ["展示柜", "display case"], "weight": 3},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
    {
        "id": "EXHIBIT-ROBOT",
        "name_zh": "机器人展品",
        "name_en": "Robot Exhibit",
        "floor": 2,
        "kind": "exhibit_area",
        "aliases": ["机器人", "robot", "机器人展品", "Robot Exhibit"],
        "visual_landmarks": [
            {"aliases": ["白色机器人", "white robot", "机器人手臂"], "weight": 5},
            {"aliases": ["ROBOT-001", "展品编号"], "weight": 6},
            {"aliases": ["机器人展板", "robot display board"], "weight": 3},
        ],
        "remark": "演示数据 — 实地测量后替换。",
    },
]

# ============================================================
# 演示边（连接演示节点，支持普通路线和无障碍路线）
# ============================================================
DEMO_EDGES = [
    # 一楼：入口 ↔ 大厅
    {
        "from": "LB-1F-ENTRANCE",
        "to": "LB-1F-LOBBY",
        "distance_m": 12,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "从主入口直行约12米，进入一楼大厅。",
                "en": "Go straight for about 12 meters into the lobby.",
            },
            "reverse": {
                "zh": "穿过大厅直行约12米，到达主入口。",
                "en": "Cross the lobby and continue to the main entrance.",
            },
        },
    },
    # 一楼：大厅 ↔ 楼梯
    {
        "from": "LB-1F-LOBBY",
        "to": "LB-1F-STAIRS",
        "distance_m": 8,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "从大厅右转，前行约8米到达楼梯口，上楼至二楼。",
                "en": "Turn right from the lobby and walk 8 meters to the stairs, then go up to the second floor.",
            },
            "reverse": {
                "zh": "从楼梯口前行约8米，返回大厅。",
                "en": "Walk 8 meters from the stairs back to the lobby.",
            },
        },
    },
    # 一楼：大厅 ↔ 电梯
    {
        "from": "LB-1F-LOBBY",
        "to": "LB-1F-ELEVATOR",
        "distance_m": 6,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "从大厅直行约6米，乘坐电梯至二楼。",
                "en": "Go straight 6 meters from the lobby and take the elevator to the second floor.",
            },
            "reverse": {
                "zh": "从电梯口前行约6米，返回大厅。",
                "en": "Walk 6 meters from the elevator back to the lobby.",
            },
        },
    },
    # 楼梯：一楼 → 二楼（楼梯间为不可达边，仅作为垂直通道）
    {
        "from": "LB-1F-STAIRS",
        "to": "LB-2F-STAIRS",
        "distance_m": 6,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "沿楼梯上行至二楼楼梯口。",
                "en": "Go up the stairs to the second floor.",
            },
            "reverse": {
                "zh": "沿楼梯下行至一楼楼梯口。",
                "en": "Go down the stairs to the first floor.",
            },
        },
    },
    # 电梯：一楼 → 二楼
    {
        "from": "LB-1F-ELEVATOR",
        "to": "LB-2F-ELEVATOR",
        "distance_m": 5,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "乘坐电梯至二楼。",
                "en": "Take the elevator to the second floor.",
            },
            "reverse": {
                "zh": "乘坐电梯至一楼。",
                "en": "Take the elevator to the first floor.",
            },
        },
    },
    # 二楼：楼梯口 ↔ 走廊A
    {
        "from": "LB-2F-STAIRS",
        "to": "LB-2F-CORRIDOR-A",
        "distance_m": 10,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "从楼梯口直行约10米，进入二楼走廊A。",
                "en": "Go straight 10 meters from the stairs into Corridor A.",
            },
            "reverse": {
                "zh": "从走廊A返回楼梯口约10米。",
                "en": "Return 10 meters from Corridor A to the stairs.",
            },
        },
    },
    # 二楼：电梯 ↔ 走廊A
    {
        "from": "LB-2F-ELEVATOR",
        "to": "LB-2F-CORRIDOR-A",
        "distance_m": 8,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "出电梯后直行约8米，进入二楼走廊A。",
                "en": "Exit the elevator and go straight 8 meters into Corridor A.",
            },
            "reverse": {
                "zh": "从走廊A返回电梯口约8米。",
                "en": "Return 8 meters from Corridor A to the elevator.",
            },
        },
    },
    # 二楼：走廊A ↔ 走廊B
    {
        "from": "LB-2F-CORRIDOR-A",
        "to": "LB-2F-CORRIDOR-B",
        "distance_m": 15,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "沿走廊A前行约15米，转入走廊B。",
                "en": "Follow Corridor A for 15 meters, then turn into Corridor B.",
            },
            "reverse": {
                "zh": "沿走廊B返回走廊A约15米。",
                "en": "Return 15 meters along Corridor B to Corridor A.",
            },
        },
    },
    # 二楼：走廊B ↔ 机器人展品
    {
        "from": "LB-2F-CORRIDOR-B",
        "to": "EXHIBIT-ROBOT",
        "distance_m": 5,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "沿走廊B前行约5米，到达机器人展品区。",
                "en": "Follow Corridor B for 5 meters to the Robot Exhibit.",
            },
            "reverse": {
                "zh": "从展品区返回走廊B约5米。",
                "en": "Return 5 meters from the exhibit to Corridor B.",
            },
        },
    },
]


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = {node["id"] for node in data["nodes"]}
    added_nodes = 0
    for node in DEMO_NODES:
        if node["id"] not in existing_ids:
            data["nodes"].append(node)
            added_nodes += 1
            print(f"  + 添加节点: {node['id']} ({node['name_zh']})")

    if not data["edges"]:
        data["edges"] = list(DEMO_EDGES)
        print(f"  + 添加 {len(DEMO_EDGES)} 条演示边")
    else:
        print("  边已存在，跳过。")

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n完成！节点总数: {len(data['nodes'])}，边总数: {len(data['edges'])}")


if __name__ == "__main__":
    main()
