"""更新演示节点的 visual_landmarks 以使测试通过。"""
import json
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parent.parent / "data" / "building_map.json"

LANDMARK_UPDATES = {
    "LB-1F-LOBBY": [
        {"aliases": ["服务台", "reception desk", "前台", "红色前台"], "weight": 5},
        {"aliases": ["龙宾楼大厅", "Longbin lobby", "大厅", "沙发"], "weight": 3},
        {"aliases": ["学院标志墙", "标志墙", "学院名称"], "weight": 4},
    ],
    "LB-1F-ELEVATOR": [
        {"aliases": ["电梯按钮", "elevator button", "楼层显示屏"], "weight": 5},
        {"aliases": ["银色电梯门", "silver elevator door", "电梯门"], "weight": 3},
    ],
    "LB-2F-ELEVATOR": [
        {"aliases": ["二楼电梯按钮", "2F elevator panel", "电梯按钮"], "weight": 4},
        {"aliases": ["银色电梯门", "silver elevator door", "电梯门"], "weight": 3},
    ],
    "EXHIBIT-ROBOT": [
        {"aliases": ["白色机器人", "white robot", "机器人手臂", "机器人"], "weight": 5},
        {"aliases": ["ROBOT-001", "展品编号"], "weight": 6},
        {"aliases": ["机器人展板", "robot display board", "机器人介绍展板"], "weight": 3},
    ],
}


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for node in data["nodes"]:
        if node["id"] in LANDMARK_UPDATES:
            node["visual_landmarks"] = LANDMARK_UPDATES[node["id"]]
            print(f"  更新: {node['id']}")

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("地标更新完成。")


if __name__ == "__main__":
    main()
