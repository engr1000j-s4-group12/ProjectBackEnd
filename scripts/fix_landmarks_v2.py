"""
直接修复关键节点的 visual_landmarks，将共享特征与唯一特征分离。
"""
import json
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parent.parent / "data" / "building_map.json"

# 为每种节点类型定义优化后的 landmarks
FIXES = {
    "LB-4F-STAIRS-NORTHWEST": [
        {"aliases": ["西北侧楼梯", "Northwest Stairs", "西北楼梯"], "weight": 5.0},
        {"aliases": ["楼梯", "stairs"], "weight": 1.0},
    ],
    "LB-4F-STAIRS-NORTHEAST": [
        {"aliases": ["东北侧楼梯", "Northeast Stairs", "东北楼梯"], "weight": 5.0},
        {"aliases": ["楼梯", "stairs"], "weight": 1.0},
    ],
    "LB-4F-STAIRS-SOUTHWEST": [
        {"aliases": ["西南侧楼梯", "Southwest Stairs", "西南楼梯"], "weight": 5.0},
        {"aliases": ["楼梯", "stairs"], "weight": 1.0},
    ],
    "LB-4F-STAIRS-SOUTHEAST": [
        {"aliases": ["东南侧楼梯", "Southeast Stairs", "东南楼梯"], "weight": 5.0},
        {"aliases": ["楼梯", "stairs"], "weight": 1.0},
    ],
    "LB-4F-ELEVATOR-NORTHWEST": [
        {"aliases": ["西北电梯", "Northwest Elevator", "西北侧电梯"], "weight": 5.0},
        {"aliases": ["电梯", "elevator", "电梯门", "elevator door"], "weight": 1.0},
    ],
    "LB-4F-CARGO-ELEVATOR-SOUTHEAST": [
        {"aliases": ["东南货梯", "Southeast Cargo Elevator", "货梯", "cargo elevator"], "weight": 5.0},
        {"aliases": ["电梯", "elevator"], "weight": 1.0},
    ],
    "LB-4F-RESTROOM-NORTHEAST": [
        {"aliases": ["东北卫生间", "Northeast Restroom", "东北侧卫生间"], "weight": 5.0},
        {"aliases": ["卫生间", "restroom", "洗手间"], "weight": 1.0},
    ],
    "LB-4F-RESTROOM-SOUTHWEST": [
        {"aliases": ["西南卫生间", "Southwest Restroom", "西南侧卫生间"], "weight": 5.0},
        {"aliases": ["卫生间", "restroom", "洗手间"], "weight": 1.0},
    ],
}


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed = 0
    for node in data["nodes"]:
        if node["id"] in FIXES:
            node["visual_landmarks"] = FIXES[node["id"]]
            fixed += 1
            print(f"  ✓ {node['id']}")

    # 检查之前添加的走廊节点是否已有 landmarks
    for node in data["nodes"]:
        if node["kind"] == "corridor" and not node.get("visual_landmarks"):
            node["visual_landmarks"] = [
                {"aliases": node.get("aliases", [node["name_zh"], node["name_en"]]), "weight": 2.0}
            ]
            fixed += 1

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n共修复 {fixed} 个节点")


if __name__ == "__main__":
    main()
