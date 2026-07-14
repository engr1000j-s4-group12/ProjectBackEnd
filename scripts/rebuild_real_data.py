"""
重建 building_map.json:
1. 移除所有演示数据 (demo 节点 + 所有旧边)
2. 基于4F真实节点位置构建走廊网络
3. 自动生成导航指令
"""
import json, math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAP_FILE = DATA_DIR / "building_map.json"

# ============================================================
# 走廊节点定义 (基于4F真实房间位置分析)
# ============================================================
# 建筑约 70m×80m, 房间分布在: 西(x≈2-20), 中(x≈20-50), 东(x≈51-67)
# 纵向走廊: 西x≈9, 中x≈30, 东x≈55
# 横向走廊: 北y≈6, 中北y≈22, 中南y≈50, 南y≈73

CORRIDOR_NODES = [
    # 北走廊 (y≈6)
    {"id": "LB-4F-CORRIDOR-N1", "name_zh": "北走廊西段", "name_en": "North Corridor West", "floor": 4, "kind": "corridor",
     "aliases": ["北走廊西", "North Corridor West"], "position": {"x_m": 9, "y_m": 6}},
    {"id": "LB-4F-CORRIDOR-N2", "name_zh": "北走廊中段", "name_en": "North Corridor Center", "floor": 4, "kind": "corridor",
     "aliases": ["北走廊中", "North Corridor Center"], "position": {"x_m": 30, "y_m": 6}},
    {"id": "LB-4F-CORRIDOR-N3", "name_zh": "北走廊东段", "name_en": "North Corridor East", "floor": 4, "kind": "corridor",
     "aliases": ["北走廊东", "North Corridor East"], "position": {"x_m": 55, "y_m": 6}},

    # 中北走廊 (y≈22)
    {"id": "LB-4F-CORRIDOR-M1", "name_zh": "中北走廊西段", "name_en": "Mid-North Corridor West", "floor": 4, "kind": "corridor",
     "aliases": ["中北走廊西", "Mid-North Corridor West"], "position": {"x_m": 9, "y_m": 22}},
    {"id": "LB-4F-CORRIDOR-M2", "name_zh": "中北走廊中段", "name_en": "Mid-North Corridor Center", "floor": 4, "kind": "corridor",
     "aliases": ["中北走廊中", "Mid-North Corridor Center"], "position": {"x_m": 30, "y_m": 22}},
    {"id": "LB-4F-CORRIDOR-M3", "name_zh": "中北走廊东段", "name_en": "Mid-North Corridor East", "floor": 4, "kind": "corridor",
     "aliases": ["中北走廊东", "Mid-North Corridor East"], "position": {"x_m": 55, "y_m": 22}},

    # 中南走廊 (y≈50)
    {"id": "LB-4F-CORRIDOR-S1", "name_zh": "中南走廊西段", "name_en": "Mid-South Corridor West", "floor": 4, "kind": "corridor",
     "aliases": ["中南走廊西", "Mid-South Corridor West"], "position": {"x_m": 9, "y_m": 50}},
    {"id": "LB-4F-CORRIDOR-S2", "name_zh": "中南走廊中段", "name_en": "Mid-South Corridor Center", "floor": 4, "kind": "corridor",
     "aliases": ["中南走廊中", "Mid-South Corridor Center"], "position": {"x_m": 30, "y_m": 50}},
    {"id": "LB-4F-CORRIDOR-S3", "name_zh": "中南走廊东段", "name_en": "Mid-South Corridor East", "floor": 4, "kind": "corridor",
     "aliases": ["中南走廊东", "Mid-South Corridor East"], "position": {"x_m": 55, "y_m": 50}},

    # 南走廊 (y≈73)
    {"id": "LB-4F-CORRIDOR-SOUTH1", "name_zh": "南走廊西段", "name_en": "South Corridor West", "floor": 4, "kind": "corridor",
     "aliases": ["南走廊西", "South Corridor West"], "position": {"x_m": 12, "y_m": 73}},
    {"id": "LB-4F-CORRIDOR-SOUTH2", "name_zh": "南走廊中段", "name_en": "South Corridor Center", "floor": 4, "kind": "corridor",
     "aliases": ["南走廊中", "South Corridor Center"], "position": {"x_m": 30, "y_m": 73}},
    {"id": "LB-4F-CORRIDOR-SOUTH3", "name_zh": "南走廊东段", "name_en": "South Corridor East", "floor": 4, "kind": "corridor",
     "aliases": ["南走廊东", "South Corridor East"], "position": {"x_m": 55, "y_m": 73}},
]


def dist(p1, p2):
    """两点之间的欧氏距离"""
    return math.hypot(p1["x_m"] - p2["x_m"], p1["y_m"] - p2["y_m"])


def make_edge(from_id, to_id, distance, accessible=True):
    """创建一条边（不预生成指令，由 Navigator 根据目标节点自动生成）。"""
    d = round(distance, 1)
    if d <= 0:
        d = 1.0
    return {
        "from": from_id,
        "to": to_id,
        "distance_m": d,
        "bidirectional": True,
        "accessible": accessible,
        # 不预设 instructions，让 Navigator 的 fallback 根据目的地名称自动生成
        # 例如：前进 12 米到达400房间。
    }


def main():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ---- Step 1: 移除所有演示节点 ----
    old_count = len(data["nodes"])
    data["nodes"] = [n for n in data["nodes"] if not (
        isinstance(n.get("remark"), str) and n["remark"].startswith("演示数据")
    )]
    print(f"移除演示节点: {old_count} → {len(data['nodes'])}")

    # ---- Step 2: 添加走廊节点 ----
    existing_ids = {n["id"] for n in data["nodes"]}
    for cn in CORRIDOR_NODES:
        if cn["id"] not in existing_ids:
            cn["visual_landmarks"] = [{"aliases": cn["aliases"].copy(), "weight": 2.0}]
            cn["remark"] = "基于4F楼层索引图位置估算的走廊节点，实地测量后调整。"
            cn["source"] = "龙宾楼4楼楼层索引图"
            data["nodes"].append(cn)
            print(f"  + 走廊节点: {cn['id']} ({cn['name_zh']})")

    # ---- Step 3: 构建节点名称映射 ----
    node_map = {n["id"]: n for n in data["nodes"]}

    # ---- Step 4: 创建走廊内部连线 (水平+垂直网格) ----
    new_edges = []

    # 水平连线: 每条横向走廊的西→中→东
    horizontal_groups = [
        ("LB-4F-CORRIDOR-N1", "LB-4F-CORRIDOR-N2", "LB-4F-CORRIDOR-N3"),
        ("LB-4F-CORRIDOR-M1", "LB-4F-CORRIDOR-M2", "LB-4F-CORRIDOR-M3"),
        ("LB-4F-CORRIDOR-S1", "LB-4F-CORRIDOR-S2", "LB-4F-CORRIDOR-S3"),
        ("LB-4F-CORRIDOR-SOUTH1", "LB-4F-CORRIDOR-SOUTH2", "LB-4F-CORRIDOR-SOUTH3"),
    ]
    for w, c, e in horizontal_groups:
        pw, pc, pe = node_map[w]["position"], node_map[c]["position"], node_map[e]["position"]
        new_edges.append(make_edge(w, c, dist(pw, pc)))
        new_edges.append(make_edge(c, e, dist(pc, pe)))

    # 垂直连线: 每条纵向走廊的北→中北→中南→南
    vertical_groups = [
        ("LB-4F-CORRIDOR-N1", "LB-4F-CORRIDOR-M1", "LB-4F-CORRIDOR-S1", "LB-4F-CORRIDOR-SOUTH1"),
        ("LB-4F-CORRIDOR-N2", "LB-4F-CORRIDOR-M2", "LB-4F-CORRIDOR-S2", "LB-4F-CORRIDOR-SOUTH2"),
        ("LB-4F-CORRIDOR-N3", "LB-4F-CORRIDOR-M3", "LB-4F-CORRIDOR-S3", "LB-4F-CORRIDOR-SOUTH3"),
    ]
    for nodes in vertical_groups:
        for i in range(len(nodes) - 1):
            a, b = nodes[i], nodes[i + 1]
            pa, pb = node_map[a]["position"], node_map[b]["position"]
            new_edges.append(make_edge(a, b, dist(pa, pb)))

    # ---- Step 5: 连接房间到最近走廊 ----
    corridor_ids = {cn["id"] for cn in CORRIDOR_NODES}
    corridor_positions = {cid: node_map[cid]["position"] for cid in corridor_ids}

    for node in data["nodes"]:
        nid = node["id"]
        if nid in corridor_ids:
            continue
        pos = node.get("position")
        if not pos or "x_m" not in pos:
            continue

        # 找最近的走廊节点
        best_corridor = min(corridor_positions.items(), key=lambda kv: dist(pos, kv[1]))
        best_id, best_pos = best_corridor
        d = dist(pos, best_pos)
        accessible = node.get("kind") != "stairs"
        new_edges.append(make_edge(best_id, nid, d, accessible))

    # ---- Step 6: 清除旧边，写入新边 ----
    data["edges"] = new_edges
    accessible_count = sum(1 for e in new_edges if e["accessible"])
    print(f"\n走廊网格边: {len(new_edges)} (其中 {accessible_count} 条可无障碍通行)")

    # ---- Step 7: 保存 ----
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n完成! 节点: {len(data['nodes'])}, 边: {len(data['edges'])}")
    print("请实地测量后调整走廊节点位置和房间距离。")


if __name__ == "__main__":
    main()
