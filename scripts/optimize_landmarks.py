"""
优化 visual_landmarks：将共享特征（如"楼梯"）与独有特征分离，
分别赋予不同权重，提高视觉定位的区分度。
"""
import json
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parent.parent / "data" / "building_map.json"

# 共享的低区分度特征（所有同类节点共享）
SHARED_STAIRS = ["楼梯", "stairs"]
SHARED_ELEVATOR = ["电梯", "elevator", "电梯门"]
SHARED_RESTROOM = ["卫生间", "restroom", "洗手间", "厕所"]
SHARED_PANTRY = ["茶水间", "pantry"]
SHARED_HYDRANT = ["消防栓", "fire hydrant"]
SHARED_CORRIDOR = ["走廊", "corridor"]


def split_landmarks(node):
    """将一个节点的 landmarks 拆分为独有（高权重）和共享（低权重）两组。"""
    landmarks = node.get("visual_landmarks", [])
    if not landmarks:
        return landmarks

    kind = node.get("kind", "")
    node_id = node["id"]

    # 收集所有现有别名
    all_aliases = []
    for lm in landmarks:
        all_aliases.extend(lm.get("aliases", []))

    # 确定哪些是共享特征
    shared_set = set()
    if kind == "stairs":
        shared_set = set(SHARED_STAIRS)
    elif kind in ("elevator", "cargo_elevator"):
        shared_set = set(SHARED_ELEVATOR)
    elif kind == "restroom":
        shared_set = set(SHARED_RESTROOM)
    elif kind == "pantry":
        shared_set = set(SHARED_PANTRY)
    elif kind == "fire_hydrant":
        shared_set = set(SHARED_HYDRANT)
    elif kind == "corridor":
        shared_set = set(SHARED_CORRIDOR)

    unique_aliases = [a for a in all_aliases if a not in shared_set]
    shared_aliases = [a for a in all_aliases if a in shared_set]

    new_landmarks = []
    if unique_aliases:
        new_landmarks.append({"aliases": unique_aliases, "weight": 5.0})
    if shared_aliases:
        new_landmarks.append({"aliases": shared_aliases, "weight": 1.0})

    return new_landmarks if new_landmarks else landmarks


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for node in data["nodes"]:
        old = node.get("visual_landmarks", [])
        new = split_landmarks(node)
        if old != new:
            node["visual_landmarks"] = new
            updated += 1

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已优化 {updated} 个节点的 visual_landmarks")
    print("共享特征权重=1.0, 独有特征权重=5.0")


if __name__ == "__main__":
    main()
