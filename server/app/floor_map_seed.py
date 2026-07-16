from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any


FLOOR_IMAGES = {
    floor: f"/admin/static/maps/longbin-{floor}f-node-worksheet.png"
    for floor in range(1, 5)
}


ROOM_LABELS = {
    2: [
        "217", "218", "219A", "219B", "219C", "220", "221", "223", "225", "227", "228", "229",
        "212-11B", "212-12B", "212-11A", "212-12A", "212-9B", "212-10B", "212-9A", "212-10A",
        "212-7B", "212-8", "212-7A", "212-5B", "212-5A", "212-3B", "212-4B", "212-3A", "212-4A",
        "212-1B", "212-2B", "212-1A", "212-2A", "210", "211", "212", "213", "214", "215",
        "216", "222", "224", "226", "230", "231", "232", "233", "234", "235", "236",
        "233-2B", "233-1B", "233-2A", "233-1A", "233-4B", "233-3B", "233-4A", "233-3A",
        "233-6", "233-5B", "233-8B", "233-7B", "233-8A", "233-7A",
        "209", "208", "207", "206", "205", "204", "203", "202A", "201", "200",
    ],
    3: [
        "312", "313A", "313B", "313C", "313D", "314", "315", "316", "317", "318", "319", "320", "321",
        "310G", "310H", "311", "310E", "310F", "309", "310D", "308", "310B", "307", "310C", "306", "310A",
        "322A", "322", "323", "324", "325", "327", "326F", "326J", "326E", "326I", "326D", "326H",
        "326C", "326G", "326B", "326A", "326", "300B", "300A", "300", "305", "304", "303",
        "302C", "302D", "302B", "302A", "301",
    ],
}


OPEN_NODES = {
    1: [
        ("LB-1F-OPEN-01", 0.49, 0.20), ("LB-1F-OPEN-02", 0.27, 0.29),
        ("LB-1F-OPEN-03", 0.73, 0.29), ("LB-1F-OPEN-04", 0.49, 0.37),
        ("LB-1F-OPEN-05", 0.28, 0.51), ("LB-1F-OPEN-06", 0.72, 0.51),
        ("LB-1F-OPEN-07", 0.27, 0.69), ("LB-1F-OPEN-08", 0.49, 0.82),
    ],
    2: [
        ("LB-2F-OPEN-01", 0.28, 0.18), ("LB-2F-OPEN-02", 0.50, 0.18),
        ("LB-2F-OPEN-03", 0.72, 0.18), ("LB-2F-OPEN-04", 0.39, 0.45),
        ("LB-2F-OPEN-06", 0.34, 0.66), ("LB-2F-OPEN-06-SOUTH", 0.27, 0.78),
        ("LB-2F-OPEN-07", 0.49, 0.43), ("LB-2F-OPEN-08", 0.49, 0.76),
        ("LB-2F-OPEN-09", 0.59, 0.45), ("LB-2F-OPEN-10", 0.73, 0.78),
    ],
    3: [
        ("LB-3F-OPEN-01", 0.19, 0.17), ("LB-3F-OPEN-02", 0.48, 0.17),
        ("LB-3F-OPEN-03", 0.77, 0.17), ("LB-3F-OPEN-310H-OPPOSITE", 0.22, 0.25),
        ("LB-3F-OPEN-04", 0.34, 0.35), ("LB-3F-OPEN-05", 0.49, 0.45),
        ("LB-3F-OPEN-06", 0.20, 0.70), ("LB-3F-OPEN-07", 0.49, 0.72),
        ("LB-3F-OPEN-08", 0.24, 0.78), ("LB-3F-OPEN-09", 0.78, 0.39),
        ("LB-3F-OPEN-10", 0.78, 0.78),
    ],
    4: [
        ("LB-4F-OPEN-01", 0.30, 0.17), ("LB-4F-OPEN-02", 0.52, 0.17),
        ("LB-4F-OPEN-03", 0.77, 0.17), ("LB-4F-OPEN-04", 0.14, 0.30),
        ("LB-4F-OPEN-05", 0.27, 0.50), ("LB-4F-OPEN-06", 0.25, 0.69),
        ("LB-4F-OPEN-07", 0.48, 0.84), ("LB-4F-OPEN-08", 0.84, 0.47),
        ("LB-4F-OPEN-09", 0.52, 0.69), ("LB-4F-OPEN-10", 0.76, 0.69),
        ("LB-4F-OPEN-11", 0.84, 0.70), ("LB-4F-OPEN-12", 0.70, 0.83),
    ],
}


FACILITIES = [
    ("LB-1F-RESTROOM-NORTHWEST", 1, "restroom", "西北侧洗手间", "Northwest restroom", 0.29, 0.12),
    ("LB-1F-RESTROOM-NORTHEAST", 1, "restroom", "东北侧洗手间", "Northeast restroom", 0.71, 0.12),
    ("LB-1F-RESTROOM-SOUTHWEST", 1, "restroom", "西南侧洗手间", "Southwest restroom", 0.28, 0.86),
    ("LB-1F-RESTROOM-SOUTHEAST", 1, "restroom", "东南侧洗手间", "Southeast restroom", 0.72, 0.86),
    ("LB-1F-STAIRS-NORTHWEST", 1, "stairs", "西北侧楼梯", "Northwest stairs", 0.32, 0.12),
    ("LB-1F-STAIRS-NORTHEAST", 1, "stairs", "东北侧楼梯", "Northeast stairs", 0.67, 0.12),
    ("LB-1F-STAIRS-SOUTHWEST", 1, "stairs", "西南侧楼梯", "Southwest stairs", 0.31, 0.86),
    ("LB-1F-STAIRS-SOUTHEAST", 1, "stairs", "东南侧楼梯", "Southeast stairs", 0.67, 0.86),
    ("LB-1F-ELEVATOR-SOUTHWEST", 1, "elevator", "西南侧电梯", "Southwest elevator", 0.35, 0.88),
    ("LB-1F-ELEVATOR-SOUTHEAST", 1, "elevator", "东南侧电梯", "Southeast elevator", 0.64, 0.88),
    ("LB-2F-RESTROOM-NORTH", 2, "restroom", "北侧洗手间", "North restroom", 0.71, 0.12),
    ("LB-2F-RESTROOM-SOUTHWEST", 2, "restroom", "西南侧洗手间", "Southwest restroom", 0.28, 0.84),
    ("LB-2F-ELEVATOR-SOUTH", 2, "elevator", "南侧电梯", "South elevator", 0.65, 0.84),
    ("LB-2F-PANTRY-NORTH", 2, "pantry", "北侧茶水间", "North pantry", 0.77, 0.12),
    ("LB-3F-RESTROOM-NORTH", 3, "restroom", "北侧洗手间", "North restroom", 0.75, 0.11),
    ("LB-3F-RESTROOM-SOUTHWEST", 3, "restroom", "西南侧洗手间", "Southwest restroom", 0.25, 0.84),
    ("LB-3F-PANTRY-SOUTH", 3, "pantry", "南侧茶水间", "South pantry", 0.68, 0.84),
]


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _insert_node(connection: sqlite3.Connection, node: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO map_nodes
          (node_id, floor, kind, name_zh, name_en, aliases_json,
           visual_landmarks_json, x_norm, y_norm, geometry_json, map_source,
           calibration_status, routable, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(node_id) DO NOTHING
        """,
        (
            node["node_id"], node["floor"], node["kind"], node["name_zh"],
            node.get("name_en", ""), _dump(node.get("aliases", [])),
            _dump(node.get("visual_landmarks", [])), node.get("x_norm"),
            node.get("y_norm"), _dump(node.get("geometry", [])),
            node.get("map_source", "floor worksheet"),
            node.get("calibration_status", "diagram_only"),
            int(bool(node.get("routable", False))), node["now"], node["now"],
        ),
    )


def seed_floor_map_database(
    connection: sqlite3.Connection,
    root: Path,
    now: str,
) -> None:
    for floor, image_url in FLOOR_IMAGES.items():
        connection.execute(
            """
            INSERT INTO floor_maps
              (floor, image_url, image_width, image_height, source,
               calibration_status, created_at, updated_at)
            VALUES (?, ?, 1536, 1024, ?, 'diagram_only', ?, ?)
            ON CONFLICT(floor) DO UPDATE SET image_url = excluded.image_url,
              image_width = excluded.image_width, image_height = excluded.image_height,
              updated_at = excluded.updated_at
            """,
            (floor, image_url, f"龙宾楼{floor}F节点补充图", now, now),
        )

    map_path = root / "data" / "building_map.json"
    if map_path.is_file():
        map_data = json.loads(map_path.read_text(encoding="utf-8"))
        edge_nodes = {value for edge in map_data["edges"] for value in (edge["from"], edge["to"])}
        for source in map_data["nodes"]:
            position = source.get("position") or {}
            _insert_node(connection, {
                "node_id": source["id"], "floor": source["floor"], "kind": source["kind"],
                "name_zh": source["name_zh"], "name_en": source["name_en"],
                "aliases": source.get("aliases", []),
                "visual_landmarks": source.get("visual_landmarks", []),
                "x_norm": position.get("x_ratio"), "y_norm": position.get("y_ratio"),
                "map_source": source.get("source", "data/building_map.json"),
                "calibration_status": "estimated" if position.get("estimated") else "diagram_only",
                "routable": source["id"] in edge_nodes, "now": now,
            })
        for edge in map_data["edges"]:
            connection.execute(
                """
                INSERT INTO map_edges
                  (from_node_id, to_node_id, distance_m, bidirectional, accessible,
                   instructions_json, calibration_status, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'estimated', 'active', ?, ?)
                ON CONFLICT(from_node_id, to_node_id) DO NOTHING
                """,
                (edge["from"], edge["to"], edge["distance_m"],
                 int(edge.get("bidirectional", True)), int(edge.get("accessible", True)),
                 _dump(edge.get("instructions", {})), now, now),
            )

    for floor, labels in ROOM_LABELS.items():
        for label in labels:
            aliases = [label, f"{label}房间", f"Room {label}"]
            _insert_node(connection, {
                "node_id": f"LB-{floor}F-ROOM-{label}", "floor": floor, "kind": "room",
                "name_zh": f"{label}房间", "name_en": f"Room {label}", "aliases": aliases,
                "visual_landmarks": [{"aliases": aliases, "weight": 5.0}],
                "map_source": f"龙宾楼{floor}F节点补充图", "now": now,
            })

    # The 2F worksheet contains two labels reading 203. Keep the second one
    # queryable without pretending that its final room number is confirmed.
    _insert_node(connection, {
        "node_id": "LB-2F-ROOM-203-EAST-UNVERIFIED", "floor": 2, "kind": "room",
        "name_zh": "东侧203（待核对）", "name_en": "East 203 (unverified)",
        "aliases": ["203", "东侧203"], "map_source": "龙宾楼2F节点补充图",
        "calibration_status": "needs_review", "now": now,
    })

    for floor, items in OPEN_NODES.items():
        for node_id, x_norm, y_norm in items:
            source_label = "LB-2F-OPEN-06" if node_id.endswith("OPEN-06-SOUTH") else node_id
            _insert_node(connection, {
                "node_id": node_id, "floor": floor, "kind": "open_area",
                "name_zh": f"{floor}楼开放空间 {source_label.rsplit('-', 1)[-1]}",
                "name_en": f"Floor {floor} open area {source_label.rsplit('-', 1)[-1]}",
                "aliases": [source_label, node_id], "x_norm": x_norm, "y_norm": y_norm,
                "map_source": f"龙宾楼{floor}F节点补充图",
                "calibration_status": "needs_review" if node_id.endswith("OPEN-06-SOUTH") else "diagram_only",
                "now": now,
            })

    for node_id, floor, kind, name_zh, name_en, x_norm, y_norm in FACILITIES:
        aliases = [name_zh, name_en]
        _insert_node(connection, {
            "node_id": node_id, "floor": floor, "kind": kind,
            "name_zh": name_zh, "name_en": name_en, "aliases": aliases,
            "visual_landmarks": [{"aliases": aliases, "weight": 3.0}],
            "x_norm": x_norm, "y_norm": y_norm,
            "map_source": f"龙宾楼{floor}F节点补充图", "now": now,
        })


def seed_user_marked_routes(
    connection: sqlite3.Connection,
    root: Path,
    now: str,
) -> None:
    path = root / "data" / "user_marked_routes_2026-07-16.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for node_id, floor, x_norm, y_norm in data.get("path_nodes", []):
        _insert_node(connection, {
            "node_id": node_id,
            "floor": int(floor),
            "kind": "path",
            "name_zh": f"{floor}楼绿色路线转折点",
            "name_en": f"Floor {floor} green-route waypoint",
            "aliases": [node_id],
            "x_norm": float(x_norm),
            "y_norm": float(y_norm),
            "map_source": data.get("source", "user route annotation"),
            "calibration_status": "user_marked",
            "now": now,
        })
    for node_id, position in data.get("node_positions", {}).items():
        connection.execute(
            "UPDATE map_nodes SET x_norm = ?, y_norm = ?, updated_at = ? WHERE node_id = ?",
            (float(position[0]), float(position[1]), now, node_id),
        )

    connection.execute(
        "UPDATE map_edges SET status = 'archived', updated_at = ? WHERE calibration_status = 'user_marked'",
        (now,),
    )
    connection.execute(
        "UPDATE map_nodes SET routable = 0, updated_at = ? WHERE floor IN (1, 2, 3)",
        (now,),
    )
    for from_node, to_node in data.get("edges", []):
        rows = connection.execute(
            "SELECT node_id, x_norm, y_norm FROM map_nodes WHERE node_id IN (?, ?)",
            (from_node, to_node),
        ).fetchall()
        indexed = {row["node_id"]: row for row in rows}
        if from_node not in indexed or to_node not in indexed:
            raise ValueError(f"用户标注路线引用未知节点：{from_node} -> {to_node}")
        start, end = indexed[from_node], indexed[to_node]
        if None not in (start["x_norm"], start["y_norm"], end["x_norm"], end["y_norm"]):
            dx = (float(end["x_norm"]) - float(start["x_norm"])) * 70
            dy = (float(end["y_norm"]) - float(start["y_norm"])) * 80
            distance = max(2.0, round(math.hypot(dx, dy), 1))
        else:
            distance = 5.0
        connection.execute(
            """
            INSERT INTO map_edges
              (from_node_id, to_node_id, distance_m, bidirectional, accessible,
               instructions_json, calibration_status, status, created_at, updated_at)
            VALUES (?, ?, ?, 1, 1, '{}', 'user_marked', 'active', ?, ?)
            ON CONFLICT(from_node_id, to_node_id) DO UPDATE SET
              distance_m = excluded.distance_m,
              calibration_status = excluded.calibration_status,
              status = 'active', updated_at = excluded.updated_at
            """,
            (from_node, to_node, distance, now, now),
        )
        connection.execute(
            "UPDATE map_nodes SET routable = 1, updated_at = ? WHERE node_id IN (?, ?)",
            (now, from_node, to_node),
        )

    marked_floors = sorted(
        {int(edge[0].split("-")[1][0]) for edge in data.get("edges", [])}
    )
    connection.executemany(
        "UPDATE floor_maps SET calibration_status = 'user_marked', updated_at = ? WHERE floor = ?",
        [(now, floor) for floor in marked_floors],
    )


def seed_elevator_navigation(
    connection: sqlite3.Connection,
    root: Path,
    now: str,
) -> None:
    path = root / "data" / "elevator_navigation_2026-07-16.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    archive_nodes = data.get("archive_nodes", [])
    for node_id in archive_nodes:
        connection.execute(
            "UPDATE map_nodes SET status = 'archived', routable = 0, updated_at = ? WHERE node_id = ?",
            (now, node_id),
        )
        connection.execute(
            "UPDATE map_edges SET status = 'archived', updated_at = ? WHERE from_node_id = ? OR to_node_id = ?",
            (now, node_id, node_id),
        )

    for item in data.get("restricted_nodes", []):
        _insert_node(connection, {
            "node_id": item["node_id"], "floor": item["floor"], "kind": "restricted",
            "name_zh": item["name_zh"], "name_en": item["name_en"],
            "aliases": [item["name_zh"], item["name_en"], "不可进入", "No entry"],
            "x_norm": item["x_norm"], "y_norm": item["y_norm"],
            "geometry": item["geometry"], "map_source": data["source"],
            "calibration_status": "user_confirmed", "now": now,
        })
        connection.execute(
            """
            UPDATE map_nodes SET kind = 'restricted', geometry_json = ?,
              navigation_notes_json = ?, calibration_status = 'user_confirmed',
              routable = 0, status = 'active', updated_at = ? WHERE node_id = ?
            """,
            (_dump(item["geometry"]), _dump(item["navigation_notes"]), now, item["node_id"]),
        )

    guest_ids: list[str] = []
    for node_id, floor, x_norm, y_norm in data.get("guest_elevators", []):
        guest_ids.append(node_id)
        aliases = ["访客电梯", "来宾电梯", "Guest elevator", node_id]
        _insert_node(connection, {
            "node_id": node_id, "floor": floor, "kind": "elevator",
            "name_zh": f"{floor}楼访客电梯", "name_en": f"Floor {floor} guest elevator",
            "aliases": aliases,
            "visual_landmarks": [{"aliases": aliases, "weight": 5.0}],
            "x_norm": x_norm, "y_norm": y_norm, "map_source": data["source"],
            "calibration_status": "user_confirmed", "routable": True, "now": now,
        })
        connection.execute(
            """
            UPDATE map_nodes SET navigation_notes_json = ?, status = 'active',
              routable = 1, calibration_status = 'user_confirmed', updated_at = ?
            WHERE node_id = ?
            """,
            (_dump({"exit_facing": "north", "guest_access": True}), now, node_id),
        )

    def insert_edge(
        start: str,
        end: str,
        distance: float,
        forward_zh: str,
        reverse_zh: str,
    ) -> None:
        instructions = {
            "forward": {"zh": forward_zh, "en": "Follow the guest-elevator route."},
            "reverse": {"zh": reverse_zh, "en": "Follow the guest-elevator route."},
        }
        connection.execute(
            """
            INSERT INTO map_edges
              (from_node_id, to_node_id, distance_m, bidirectional, accessible,
               instructions_json, calibration_status, status, created_at, updated_at)
            VALUES (?, ?, ?, 1, 1, ?, 'user_confirmed', 'active', ?, ?)
            ON CONFLICT(from_node_id, to_node_id) DO UPDATE SET
              distance_m = excluded.distance_m,
              instructions_json = excluded.instructions_json,
              calibration_status = 'user_confirmed', status = 'active',
              updated_at = excluded.updated_at
            """,
            (start, end, distance, _dump(instructions), now, now),
        )
        connection.execute(
            "UPDATE map_nodes SET routable = 1, updated_at = ? WHERE node_id IN (?, ?)",
            (now, start, end),
        )

    for start, end, forward_zh, reverse_zh in data.get("floor_edges", []):
        insert_edge(start, end, 5.0, forward_zh, reverse_zh)

    for index, start in enumerate(guest_ids):
        start_floor = int(start.split("-")[1][0])
        for end in guest_ids[index + 1:]:
            end_floor = int(end.split("-")[1][0])
            insert_edge(
                start,
                end,
                float((end_floor - start_floor) * 3),
                f"乘坐访客电梯到{end_floor}楼。",
                f"乘坐访客电梯到{start_floor}楼。",
            )
