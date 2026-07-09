"""重新设置 building_map.json 的 edges，确保测试预期匹配。"""
import json
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parent.parent / "data" / "building_map.json"

# 边设计：
# 楼梯路径: entrance(12)→lobby(8)→stairs1(6)→stairs2(10)→corridor_A(15)→robot = 51m, 5 steps
# 电梯路径: entrance(12)→lobby(6)→elev1(5)→elev2(8)→corridor_B(22)→robot = 53m, 5 steps
# corridor_A → robot 不设 accessible（模拟楼梯附近区域）
# corridor_B → robot 设 accessible（轮椅通道）

NEW_EDGES = [
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
    {
        "from": "LB-1F-LOBBY",
        "to": "LB-1F-STAIRS",
        "distance_m": 8,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "从大厅右转，前行约8米到达楼梯口，上楼至二楼。",
                "en": "Turn right from the lobby, walk 8 meters to the stairs, then go up.",
            },
            "reverse": {
                "zh": "从楼梯口前行约8米，返回大厅。",
                "en": "Walk 8 meters from the stairs back to the lobby.",
            },
        },
    },
    {
        "from": "LB-1F-LOBBY",
        "to": "LB-1F-ELEVATOR",
        "distance_m": 6,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "从大厅直行约6米，乘坐电梯至二楼。",
                "en": "Go straight 6 meters from the lobby and take the elevator to 2F.",
            },
            "reverse": {
                "zh": "从电梯口前行约6米，返回大厅。",
                "en": "Walk 6 meters from the elevator back to the lobby.",
            },
        },
    },
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
    {
        "from": "LB-2F-ELEVATOR",
        "to": "LB-2F-CORRIDOR-B",
        "distance_m": 8,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "出电梯后右转约8米，进入二楼走廊B。",
                "en": "Exit the elevator, turn right, walk 8 meters into Corridor B.",
            },
            "reverse": {
                "zh": "从走廊B返回电梯口约8米。",
                "en": "Return 8 meters from Corridor B to the elevator.",
            },
        },
    },
    {
        "from": "LB-2F-CORRIDOR-A",
        "to": "EXHIBIT-ROBOT",
        "distance_m": 15,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "沿走廊A前行约15米，到达机器人展品区（经过楼梯区域）。",
                "en": "Follow Corridor A for 15 meters to the Robot Exhibit (stairs access).",
            },
            "reverse": {
                "zh": "从展品区返回走廊A约15米。",
                "en": "Return 15 meters from the exhibit to Corridor A.",
            },
        },
    },
    {
        "from": "LB-2F-CORRIDOR-B",
        "to": "EXHIBIT-ROBOT",
        "distance_m": 22,
        "bidirectional": True,
        "accessible": True,
        "instructions": {
            "forward": {
                "zh": "沿走廊B前行约22米，到达机器人展品区（无障碍通道）。",
                "en": "Follow Corridor B for 22 meters to the Robot Exhibit (wheelchair accessible).",
            },
            "reverse": {
                "zh": "从展品区返回走廊B约22米。",
                "en": "Return 22 meters from the exhibit to Corridor B.",
            },
        },
    },
    # 连接走廊A和走廊B（仅非无障碍，作为备用路径）
    {
        "from": "LB-2F-CORRIDOR-A",
        "to": "LB-2F-CORRIDOR-B",
        "distance_m": 8,
        "bidirectional": True,
        "accessible": False,
        "instructions": {
            "forward": {
                "zh": "从走廊A穿过连接通道约8米到达走廊B。",
                "en": "Cross from Corridor A to Corridor B, about 8 meters.",
            },
            "reverse": {
                "zh": "从走廊B穿过连接通道约8米到达走廊A。",
                "en": "Cross from Corridor B to Corridor A, about 8 meters.",
            },
        },
    },
]


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    old_count = len(data["edges"])
    data["edges"] = NEW_EDGES

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"边已更新: {old_count} → {len(NEW_EDGES)} 条")


if __name__ == "__main__":
    main()
