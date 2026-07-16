from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .floor_map_seed import (
    seed_elevator_navigation,
    seed_floor_map_database,
    seed_user_marked_routes,
)


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "guide.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL UNIQUE,
    group_code TEXT,
    floor INTEGER NOT NULL CHECK (floor BETWEEN 1 AND 4),
    geometry_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL,
    kind TEXT NOT NULL CHECK (kind IN ('permanent', 'event', 'exhibit', 'facility')),
    title_zh TEXT NOT NULL,
    title_en TEXT NOT NULL DEFAULT '',
    content_zh TEXT NOT NULL DEFAULT '',
    content_en TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    extracted_json TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL REFERENCES knowledge_records(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    vlm_status TEXT NOT NULL DEFAULT 'pending',
    vlm_result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(record_id, sha256)
);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delegation_name TEXT NOT NULL,
    institution TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    preferred_language TEXT NOT NULL DEFAULT 'en',
    purpose TEXT NOT NULL DEFAULT '',
    itinerary_json TEXT NOT NULL DEFAULT '[]',
    script_zh TEXT NOT NULL DEFAULT '',
    script_en TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS change_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    action TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS floor_maps (
    floor INTEGER PRIMARY KEY CHECK (floor BETWEEN 1 AND 4),
    image_url TEXT NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    source TEXT NOT NULL,
    calibration_status TEXT NOT NULL DEFAULT 'diagram_only',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS map_nodes (
    node_id TEXT PRIMARY KEY,
    floor INTEGER NOT NULL CHECK (floor BETWEEN 1 AND 4),
    kind TEXT NOT NULL,
    name_zh TEXT NOT NULL,
    name_en TEXT NOT NULL DEFAULT '',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    visual_landmarks_json TEXT NOT NULL DEFAULT '[]',
    x_norm REAL,
    y_norm REAL,
    geometry_json TEXT NOT NULL DEFAULT '[]',
    navigation_notes_json TEXT NOT NULL DEFAULT '{}',
    map_source TEXT NOT NULL DEFAULT '',
    calibration_status TEXT NOT NULL DEFAULT 'diagram_only',
    routable INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS map_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node_id TEXT NOT NULL REFERENCES map_nodes(node_id) ON UPDATE CASCADE,
    to_node_id TEXT NOT NULL REFERENCES map_nodes(node_id) ON UPDATE CASCADE,
    distance_m REAL,
    bidirectional INTEGER NOT NULL DEFAULT 1,
    accessible INTEGER NOT NULL DEFAULT 1,
    instructions_json TEXT NOT NULL DEFAULT '{}',
    calibration_status TEXT NOT NULL DEFAULT 'diagram_only',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(from_node_id, to_node_id)
);

CREATE TABLE IF NOT EXISTS device_sessions (
    device_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL DEFAULT '',
    firmware_version TEXT NOT NULL DEFAULT '',
    visit_id INTEGER REFERENCES visits(id) ON DELETE SET NULL,
    current_node TEXT,
    destination_node TEXT,
    state TEXT NOT NULL DEFAULT 'idle' CHECK (
      state IN ('idle', 'locating', 'ready', 'navigating', 'relocalizing',
                'needs_confirmation', 'arrived', 'service_unavailable', 'cancelled')
    ),
    confidence REAL,
    preferred_language TEXT NOT NULL DEFAULT 'zh',
    last_announcement TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_records_status_kind ON knowledge_records(status, kind);
CREATE INDEX IF NOT EXISTS idx_regions_floor_status ON regions(floor, status);
CREATE INDEX IF NOT EXISTS idx_media_record ON media(record_id);
CREATE INDEX IF NOT EXISTS idx_visits_status ON visits(status);
CREATE INDEX IF NOT EXISTS idx_map_nodes_floor_kind ON map_nodes(floor, kind, status);
CREATE INDEX IF NOT EXISTS idx_map_edges_from ON map_edges(from_node_id, status);
CREATE INDEX IF NOT EXISTS idx_map_edges_to ON map_edges(to_node_id, status);
CREATE INDEX IF NOT EXISTS idx_device_sessions_state ON device_sessions(state, updated_at);
"""


INITIAL_ENTRIES = [
    {
        "node_id": "LB-1F-REGION-A",
        "group_code": "A",
        "floor": 1,
        "geometry": [[0.675, 0.805], [0.73, 0.805], [0.73, 0.89], [0.675, 0.89]],
        "kind": "permanent",
        "title_zh": "浦江国际学院介绍区 A",
        "title_en": "Global College Introduction Area A",
        "content_zh": "学院介绍展示区域，具体内容由管理端后续录入。",
    },
    {
        "node_id": "LB-1F-REGION-B",
        "group_code": "B",
        "floor": 1,
        "geometry": [[0.445, 0.805], [0.50, 0.805], [0.50, 0.89], [0.445, 0.89]],
        "kind": "permanent",
        "title_zh": "浦江国际学院介绍区 B",
        "title_en": "Global College Introduction Area B",
        "content_zh": "学院介绍展示区域，具体内容由管理端后续录入。",
    },
    {
        "node_id": "LB-1F-REGION-C",
        "group_code": "C",
        "floor": 1,
        "geometry": [[0.47, 0.665], [0.69, 0.665], [0.69, 0.79], [0.47, 0.79]],
        "kind": "event",
        "title_zh": "浦江国际学院建校展览",
        "title_en": "Global College Founding Exhibition",
        "content_zh": "当前展示学院建校相关内容，具体展览资料由管理端录入。",
    },
    {
        "node_id": "LB-1F-REGION-D-WEST",
        "group_code": "D",
        "floor": 1,
        "geometry": [[0.405, 0.47], [0.455, 0.47], [0.455, 0.65], [0.405, 0.65]],
        "kind": "exhibit",
        "title_zh": "教师与优秀学生展览 D（西侧）",
        "title_en": "Faculty and Outstanding Students Display D West",
        "content_zh": "教师与优秀学生展示区域，具体内容由管理端录入。",
    },
    {
        "node_id": "LB-1F-REGION-D-EAST",
        "group_code": "D",
        "floor": 1,
        "geometry": [[0.715, 0.47], [0.765, 0.47], [0.765, 0.65], [0.715, 0.65]],
        "kind": "exhibit",
        "title_zh": "教师与优秀学生展览 D（东侧）",
        "title_en": "Faculty and Outstanding Students Display D East",
        "content_zh": "教师与优秀学生展示区域，具体内容由管理端录入。",
    },
    {
        "node_id": "LB-2F-REGION-E",
        "group_code": "E",
        "floor": 2,
        "geometry": [[0.43, 0.33], [0.49, 0.33], [0.49, 0.43], [0.43, 0.43]],
        "kind": "facility",
        "title_zh": "钢琴",
        "title_en": "Piano",
        "content_zh": "区域 E 当前放置一台钢琴。",
    },
    {
        "node_id": "LB-3F-EVENT-LEE-ART",
        "group_code": "LEE-ART",
        "floor": 3,
        "geometry": [[0.37, 0.15], [0.66, 0.15], [0.66, 0.28], [0.37, 0.28]],
        "kind": "event",
        "title_zh": "李政道科学与艺术大奖赛历年主题画展",
        "title_en": "Tsung-Dao Lee Science and Art Exhibition",
        "content_zh": "位于三楼北侧开放区域，展品资料由现场图片预处理后补充。",
    },
    {
        "node_id": "LB-4F-REGION-F",
        "group_code": "F",
        "floor": 4,
        "geometry": [[0.80, 0.36], [0.84, 0.36], [0.84, 0.75], [0.80, 0.75]],
        "kind": "permanent",
        "title_zh": "浦江国际学院介绍墙 F",
        "title_en": "Global College Introduction Wall F",
        "content_zh": "学院介绍墙，具体内容由管理端后续录入。",
    },
]


class KnowledgeStore:
    def __init__(self, path: str | Path | None = None, seed: bool = True) -> None:
        self.path = Path(path or os.getenv("GUIDE_DB_PATH") or DEFAULT_DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize(seed)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self, seed: bool) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(map_nodes)").fetchall()
            }
            if "navigation_notes_json" not in columns:
                connection.execute(
                    "ALTER TABLE map_nodes ADD COLUMN navigation_notes_json TEXT NOT NULL DEFAULT '{}'"
                )
            seed_floor_map_database(
                connection,
                Path(__file__).resolve().parents[2],
                _now(),
            )
            if seed and connection.execute("SELECT COUNT(*) FROM regions").fetchone()[0] == 0:
                for item in INITIAL_ENTRIES:
                    self._create_entry(connection, item, action="seed")
            if seed:
                record_ids = connection.execute(
                    "SELECT id FROM knowledge_records ORDER BY id"
                ).fetchall()
                for row in record_ids:
                    self._sync_record_map_node(connection, self._snapshot(connection, row[0]))
                seed_user_marked_routes(
                    connection,
                    Path(__file__).resolve().parents[2],
                    _now(),
                )
                seed_elevator_navigation(
                    connection,
                    Path(__file__).resolve().parents[2],
                    _now(),
                )

    def _snapshot(self, connection: sqlite3.Connection, record_id: int) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT kr.*, r.node_id, r.group_code, r.floor, r.geometry_json,
                   r.status AS region_status
            FROM knowledge_records kr
            LEFT JOIN regions r ON r.id = kr.region_id
            WHERE kr.id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return self._decode_entry(dict(row))

    def _history(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: int,
        version: int,
        action: str,
        snapshot: dict[str, Any],
    ) -> None:
        connection.execute(
            """INSERT INTO change_history
               (entity_type, entity_id, version, action, snapshot_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (entity_type, entity_id, version, action, _json(snapshot), _now()),
        )

    def _create_entry(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
        action: str = "create",
    ) -> dict[str, Any]:
        now = _now()
        region = connection.execute(
            """INSERT INTO regions
               (node_id, group_code, floor, geometry_json, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'active', ?, ?)""",
            (
                payload["node_id"],
                payload.get("group_code") or None,
                int(payload["floor"]),
                _json(payload["geometry"]),
                now,
                now,
            ),
        )
        record = connection.execute(
            """INSERT INTO knowledge_records
               (region_id, kind, title_zh, title_en, content_zh, content_en,
                tags_json, source, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (
                region.lastrowid,
                payload["kind"],
                payload["title_zh"].strip(),
                payload.get("title_en", "").strip(),
                payload.get("content_zh", "").strip(),
                payload.get("content_en", "").strip(),
                _json(payload.get("tags", [])),
                payload.get("source", "用户批注 2026-07-16").strip(),
                now,
                now,
            ),
        )
        result = self._snapshot(connection, int(record.lastrowid))
        self._sync_record_map_node(connection, result)
        self._history(connection, "record", result["id"], 1, action, result)
        return result

    def _sync_record_map_node(
        self,
        connection: sqlite3.Connection,
        record: dict[str, Any],
    ) -> None:
        geometry = record.get("geometry") or []
        x_norm = None
        y_norm = None
        if geometry:
            x_norm = sum(float(point[0]) for point in geometry) / len(geometry)
            y_norm = sum(float(point[1]) for point in geometry) / len(geometry)
        aliases = [
            record["node_id"],
            record["title_zh"],
            record.get("title_en", ""),
            *record.get("tags", []),
        ]
        extracted = record.get("extracted") or {}
        for media in extracted.get("media", []) if isinstance(extracted, dict) else []:
            aliases.extend(media.get("recognized_texts", []))
            aliases.extend(media.get("visual_tags", []))
            if media.get("visual_description"):
                aliases.append(media["visual_description"])
        aliases = list(dict.fromkeys(str(item).strip() for item in aliases if str(item).strip()))
        landmarks = [{"aliases": aliases, "weight": 5.0}] if aliases else []
        now = _now()
        connection.execute(
            """
            INSERT INTO map_nodes
              (node_id, floor, kind, name_zh, name_en, aliases_json,
               visual_landmarks_json, x_norm, y_norm, geometry_json, map_source,
               calibration_status, routable, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'diagram_only', 0, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
              floor = excluded.floor, kind = excluded.kind,
              name_zh = excluded.name_zh, name_en = excluded.name_en,
              aliases_json = excluded.aliases_json,
              visual_landmarks_json = excluded.visual_landmarks_json,
              x_norm = excluded.x_norm, y_norm = excluded.y_norm,
              geometry_json = excluded.geometry_json,
              map_source = excluded.map_source, status = excluded.status,
              updated_at = excluded.updated_at
            """,
            (
                record["node_id"], record["floor"], record["kind"],
                record["title_zh"], record.get("title_en", ""), _json(aliases),
                _json(landmarks), x_norm, y_norm, _json(geometry),
                f"console:record:{record['id']}", record["status"], now, now,
            ),
        )

    def create_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            return self._create_entry(connection, payload)

    def list_entries(
        self,
        *,
        floor: int | None = None,
        kind: str | None = None,
        include_archived: bool = False,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if floor is not None:
            clauses.append("r.floor = ?")
            params.append(floor)
        if kind:
            clauses.append("kr.kind = ?")
            params.append(kind)
        if not include_archived:
            clauses.append("kr.status = 'active'")
        if query:
            clauses.append(
                "(kr.title_zh LIKE ? OR kr.title_en LIKE ? OR kr.content_zh LIKE ? "
                "OR kr.content_en LIKE ? OR kr.tags_json LIKE ? OR kr.extracted_json LIKE ? "
                "OR r.node_id LIKE ?)"
            )
            pattern = f"%{query.strip()}%"
            params.extend([pattern] * 7)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT kr.*, r.node_id, r.group_code, r.floor, r.geometry_json,
                       r.status AS region_status
                FROM knowledge_records kr
                LEFT JOIN regions r ON r.id = kr.region_id
                {where}
                ORDER BY r.floor, r.node_id, kr.id
                """,
                params,
            ).fetchall()
        return [self._decode_entry(dict(row)) for row in rows]

    def get_entry(self, record_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            return self._snapshot(connection, record_id)

    def update_entry(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed_record = {
            "kind",
            "title_zh",
            "title_en",
            "content_zh",
            "content_en",
            "source",
        }
        allowed_region = {"node_id", "group_code", "floor"}
        with self._connect() as connection:
            current = self._snapshot(connection, record_id)
            record_updates = {k: v for k, v in payload.items() if k in allowed_record}
            if "tags" in payload:
                record_updates["tags_json"] = _json(payload["tags"])
            if "extracted" in payload:
                record_updates["extracted_json"] = _json(payload["extracted"])
            region_updates = {k: v for k, v in payload.items() if k in allowed_region}
            if "geometry" in payload:
                region_updates["geometry_json"] = _json(payload["geometry"])

            version = int(current["version"]) + 1
            record_updates.update(updated_at=_now(), version=version)
            if record_updates:
                assignment = ", ".join(f"{key} = ?" for key in record_updates)
                connection.execute(
                    f"UPDATE knowledge_records SET {assignment} WHERE id = ?",
                    [*record_updates.values(), record_id],
                )
            if region_updates:
                region_updates["updated_at"] = _now()
                assignment = ", ".join(f"{key} = ?" for key in region_updates)
                connection.execute(
                    f"UPDATE regions SET {assignment} WHERE id = ?",
                    [*region_updates.values(), current["region_id"]],
                )
            result = self._snapshot(connection, record_id)
            if current["node_id"] != result["node_id"]:
                connection.execute(
                    "UPDATE map_nodes SET status = 'archived', updated_at = ? WHERE node_id = ?",
                    (_now(), current["node_id"]),
                )
            self._sync_record_map_node(connection, result)
            self._history(connection, "record", record_id, version, "update", result)
            return result

    def set_archived(self, record_id: int, archived: bool) -> dict[str, Any]:
        status = "archived" if archived else "active"
        archived_at = _now() if archived else None
        with self._connect() as connection:
            current = self._snapshot(connection, record_id)
            version = int(current["version"]) + 1
            now = _now()
            connection.execute(
                """UPDATE knowledge_records
                   SET status = ?, archived_at = ?, updated_at = ?, version = ?
                   WHERE id = ?""",
                (status, archived_at, now, version, record_id),
            )
            connection.execute(
                "UPDATE regions SET status = ?, archived_at = ?, updated_at = ? WHERE id = ?",
                (status, archived_at, now, current["region_id"]),
            )
            result = self._snapshot(connection, record_id)
            self._sync_record_map_node(connection, result)
            self._history(
                connection,
                "record",
                record_id,
                version,
                "archive" if archived else "restore",
                result,
            )
            return result

    def list_floor_maps(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM floor_maps ORDER BY floor"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_floor_map(self, floor: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM floor_maps WHERE floor = ?", (floor,)
            ).fetchone()
        if row is None:
            raise KeyError(floor)
        return dict(row)

    def list_map_nodes(
        self,
        *,
        floor: int | None = None,
        kind: str | None = None,
        query: str | None = None,
        routable: bool | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if floor is not None:
            clauses.append("floor = ?")
            params.append(floor)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if query:
            pattern = f"%{query.strip()}%"
            clauses.append(
                "(node_id LIKE ? OR name_zh LIKE ? OR name_en LIKE ? OR aliases_json LIKE ?)"
            )
            params.extend([pattern] * 4)
        if routable is not None:
            clauses.append("routable = ?")
            params.append(int(routable))
        if not include_archived:
            clauses.append("status = 'active'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM map_nodes {where} ORDER BY floor, node_id",
                params,
            ).fetchall()
        return [self._decode_map_node(dict(row)) for row in rows]

    def get_map_node(self, node_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM map_nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
        if row is None:
            raise KeyError(node_id)
        return self._decode_map_node(dict(row))

    def list_map_edges(
        self,
        *,
        floor: int | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if floor is not None:
            clauses.append("source.floor = ?")
            params.append(floor)
        if not include_archived:
            clauses.append("edge.status = 'active'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT edge.* FROM map_edges edge
                JOIN map_nodes source ON source.node_id = edge.from_node_id
                {where}
                ORDER BY edge.id
                """,
                params,
            ).fetchall()
        return [self._decode_map_edge(dict(row)) for row in rows]

    def map_summary(self) -> dict[str, Any]:
        floors = []
        with self._connect() as connection:
            for floor in range(1, 5):
                row = connection.execute(
                    """
                    SELECT COUNT(*) AS nodes,
                           SUM(CASE WHEN routable = 1 THEN 1 ELSE 0 END) AS routable_nodes
                    FROM map_nodes WHERE floor = ? AND status = 'active'
                    """,
                    (floor,),
                ).fetchone()
                edge_count = connection.execute(
                    """
                    SELECT COUNT(*) FROM map_edges edge
                    JOIN map_nodes node ON node.node_id = edge.from_node_id
                    WHERE node.floor = ? AND edge.status = 'active'
                    """,
                    (floor,),
                ).fetchone()[0]
                floors.append(
                    {
                        "floor": floor,
                        "nodes": row["nodes"],
                        "routable_nodes": row["routable_nodes"] or 0,
                        "edges": edge_count,
                    }
                )
        return {"database": str(self.path), "floors": floors}

    def add_media(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM knowledge_records WHERE id = ?", (record_id,)
            ).fetchone() is None:
                raise KeyError(record_id)
            cursor = connection.execute(
                """INSERT INTO media
                   (record_id, original_name, stored_name, content_type, sha256,
                    size_bytes, vlm_status, vlm_result_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    payload["original_name"],
                    payload["stored_name"],
                    payload["content_type"],
                    payload["sha256"],
                    payload["size_bytes"],
                    payload.get("vlm_status", "pending"),
                    _json(payload.get("vlm_result", {})),
                    _now(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM media WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._decode_media(dict(row))

    def update_media_vlm(
        self, media_id: int, status: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "UPDATE media SET vlm_status = ?, vlm_result_json = ? WHERE id = ?",
                (status, _json(result), media_id),
            )
            row = connection.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        if row is None:
            raise KeyError(media_id)
        return self._decode_media(dict(row))

    def get_media(self, media_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        if row is None:
            raise KeyError(media_id)
        return self._decode_media(dict(row))

    def list_media(self, record_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM media WHERE record_id = ? ORDER BY id", (record_id,)
            ).fetchall()
        return [self._decode_media(dict(row)) for row in rows]

    def create_visit(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO visits
                   (delegation_name, institution, country, preferred_language,
                    purpose, itinerary_json, script_zh, script_en, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (
                    payload["delegation_name"].strip(),
                    payload.get("institution", "").strip(),
                    payload.get("country", "").strip(),
                    payload.get("preferred_language", "en"),
                    payload.get("purpose", "").strip(),
                    _json(payload.get("itinerary", [])),
                    payload.get("script_zh", "").strip(),
                    payload.get("script_en", "").strip(),
                    now,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM visits WHERE id = ?", (cursor.lastrowid,)).fetchone()
            result = self._decode_visit(dict(row))
            self._history(connection, "visit", result["id"], 1, "create", result)
            return result

    def list_visits(self, include_archived: bool = False) -> list[dict[str, Any]]:
        where = "" if include_archived else "WHERE status = 'active'"
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM visits {where} ORDER BY id DESC"
            ).fetchall()
        return [self._decode_visit(dict(row)) for row in rows]

    def set_visit_archived(self, visit_id: int, archived: bool) -> dict[str, Any]:
        status = "archived" if archived else "active"
        archived_at = _now() if archived else None
        with self._connect() as connection:
            connection.execute(
                "UPDATE visits SET status = ?, archived_at = ?, updated_at = ? WHERE id = ?",
                (status, archived_at, _now(), visit_id),
            )
            row = connection.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
            if row is None:
                raise KeyError(visit_id)
            result = self._decode_visit(dict(row))
            self._history(
                connection,
                "visit",
                visit_id,
                1,
                "archive" if archived else "restore",
                result,
            )
            return result

    def history(self, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            clauses.append("entity_id = ?")
            params.append(entity_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM change_history {where} ORDER BY id DESC LIMIT 200", params
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["snapshot"] = json.loads(item.pop("snapshot_json"))
            result.append(item)
        return result

    def update_device_session(
        self,
        device_id: str,
        *,
        client_id: str | None = None,
        firmware_version: str | None = None,
        visit_id: int | None = None,
        current_node: str | None = None,
        destination_node: str | None = None,
        state: str | None = None,
        confidence: float | None = None,
        preferred_language: str | None = None,
        last_announcement: str | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO device_sessions (device_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (device_id, now, now),
            )
            updates = {
                "client_id": client_id,
                "firmware_version": firmware_version,
                "visit_id": visit_id,
                "current_node": current_node,
                "destination_node": destination_node,
                "state": state,
                "confidence": confidence,
                "preferred_language": preferred_language,
                "last_announcement": last_announcement,
                "last_error": last_error,
            }
            supplied = {key: value for key, value in updates.items() if value is not None}
            if supplied:
                supplied["updated_at"] = now
                assignment = ", ".join(f"{key} = ?" for key in supplied)
                connection.execute(
                    f"UPDATE device_sessions SET {assignment} WHERE device_id = ?",
                    [*supplied.values(), device_id],
                )
            row = connection.execute(
                "SELECT * FROM device_sessions WHERE device_id = ?", (device_id,)
            ).fetchone()
        return dict(row)

    def get_device_session(self, device_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM device_sessions WHERE device_id = ?", (device_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def _decode_entry(self, item: dict[str, Any]) -> dict[str, Any]:
        item["geometry"] = json.loads(item.pop("geometry_json"))
        item["tags"] = json.loads(item.pop("tags_json"))
        item["extracted"] = json.loads(item.pop("extracted_json"))
        return item

    def _decode_media(self, item: dict[str, Any]) -> dict[str, Any]:
        item["vlm_result"] = json.loads(item.pop("vlm_result_json"))
        item["url"] = f"/admin/uploads/{item['stored_name']}"
        return item

    def _decode_visit(self, item: dict[str, Any]) -> dict[str, Any]:
        item["itinerary"] = json.loads(item.pop("itinerary_json"))
        return item

    def _decode_map_node(self, item: dict[str, Any]) -> dict[str, Any]:
        item["aliases"] = json.loads(item.pop("aliases_json"))
        item["visual_landmarks"] = json.loads(item.pop("visual_landmarks_json"))
        item["geometry"] = json.loads(item.pop("geometry_json"))
        item["navigation_notes"] = json.loads(item.pop("navigation_notes_json"))
        item["routable"] = bool(item["routable"])
        return item

    def _decode_map_edge(self, item: dict[str, Any]) -> dict[str, Any]:
        item["instructions"] = json.loads(item.pop("instructions_json"))
        item["bidirectional"] = bool(item["bidirectional"])
        item["accessible"] = bool(item["accessible"])
        return item
