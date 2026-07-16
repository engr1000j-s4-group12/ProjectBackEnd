from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import DataValidationError, LocationNotFoundError
from .knowledge import KnowledgeStore


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class GuideData:
    nodes: dict[str, dict[str, Any]]
    edges: list[dict[str, Any]]
    exhibits: dict[str, dict[str, Any]]


class GuideRepository:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        configured_dir = data_dir or os.getenv("MUSEUM_DATA_DIR") or DEFAULT_DATA_DIR
        self.data_dir = Path(configured_dir)
        self.data = self._load()
        self._aliases = self._build_alias_index()

    def _read_json(self, filename: str) -> Any:
        path = self.data_dir / filename
        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError as exc:
            raise DataValidationError(f"Missing data file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise DataValidationError(f"Invalid JSON format: {path}: {exc}") from exc

    def _require_string(self, value: Any, message: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise DataValidationError(message)
        return value

    def _validate_aliases(self, aliases: Any, message: str) -> None:
        if aliases is None:
            return
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias.strip() for alias in aliases
        ):
            raise DataValidationError(message)

    def _validate_visual_landmarks(self, node_id: str, node: dict[str, Any]) -> None:
        visual_landmarks = node.get("visual_landmarks", [])
        if not isinstance(visual_landmarks, list):
            raise DataValidationError(f"visual_landmarks for node {node_id} must be a list")
        for landmark in visual_landmarks:
            aliases = landmark.get("aliases") if isinstance(landmark, dict) else None
            weight = landmark.get("weight", 1) if isinstance(landmark, dict) else None
            if (
                not isinstance(aliases, list)
                or not aliases
                or not all(isinstance(alias, str) and alias.strip() for alias in aliases)
            ):
                raise DataValidationError(
                    f"Each visual landmark for node {node_id} must contain a non-empty aliases list"
                )
            if not isinstance(weight, (int, float)) or weight <= 0:
                raise DataValidationError(f"Visual landmark weight for node {node_id} must be greater than 0")

    def _validate_node(self, node: Any, node_index: dict[str, dict[str, Any]]) -> None:
        if not isinstance(node, dict):
            raise DataValidationError("Each node must be an object")
        node_id = self._require_string(node.get("id"), "Each node must contain a non-empty string id")
        if node_id in node_index:
            raise DataValidationError(f"Duplicate node ID: {node_id}")
        for field in ("name_zh", "name_en", "kind"):
            self._require_string(node.get(field), f"Node {node_id} must contain non-empty {field}")
        floor = node.get("floor")
        if not isinstance(floor, int):
            raise DataValidationError(f"floor for node {node_id} must be an integer")
        self._validate_aliases(node.get("aliases"), f"aliases for node {node_id} must be a string list")
        position = node.get("position")
        if position is not None:
            if not isinstance(position, dict):
                raise DataValidationError(f"position for node {node_id} must be an object")
            for field in ("x_m", "y_m"):
                if field in position and not isinstance(position[field], (int, float)):
                    raise DataValidationError(f"position.{field} for node {node_id} must be numeric")
        self._validate_visual_landmarks(node_id, node)
        node_index[node_id] = node

    def _validate_instructions(self, start: str, end: str, instructions: Any) -> None:
        if instructions is None:
            return
        if not isinstance(instructions, dict):
            raise DataValidationError(f"Edge instructions must be an object: {start} -> {end}")
        for direction in ("forward", "reverse"):
            localized = instructions.get(direction)
            if localized is None:
                continue
            if not isinstance(localized, dict):
                raise DataValidationError(
                    f"{direction} instructions for edge {start} -> {end} must be an object"
                )
            for language, text in localized.items():
                if language not in {"zh", "en"}:
                    raise DataValidationError(
                        f"Edge {start} -> {end} contains an unknown instruction language: {language}"
                    )
                if not isinstance(text, str) or not text.strip():
                    raise DataValidationError(
                        f"{direction}.{language} for edge {start} -> {end} must be a non-empty string"
                    )

    def _validate_edge(self, edge: Any, node_index: dict[str, dict[str, Any]]) -> None:
        if not isinstance(edge, dict):
            raise DataValidationError("Each edge must be an object")
        start, end = edge.get("from"), edge.get("to")
        if start not in node_index or end not in node_index:
            raise DataValidationError(f"Edge references unknown node: {start} -> {end}")
        distance = edge.get("distance_m")
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise DataValidationError(f"Edge distance must be greater than 0: {start} -> {end}")
        for field in ("bidirectional", "accessible"):
            if field in edge and not isinstance(edge[field], bool):
                raise DataValidationError(f"{field} for edge {start} -> {end} must be boolean")
        self._validate_instructions(start, end, edge.get("instructions"))

    def _validate_exhibit(
        self,
        exhibit: Any,
        exhibit_index: dict[str, dict[str, Any]],
        node_index: dict[str, dict[str, Any]],
    ) -> None:
        if not isinstance(exhibit, dict):
            raise DataValidationError("Each exhibit must be an object")
        exhibit_id = self._require_string(exhibit.get("id"), "Each exhibit must contain a non-empty string id")
        location_id = exhibit.get("location_id")
        if exhibit_id in exhibit_index:
            raise DataValidationError(f"Duplicate exhibit ID: {exhibit_id}")
        if location_id not in node_index:
            raise DataValidationError(f"Exhibit {exhibit_id} references unknown node {location_id}")
        for field in ("name_zh", "name_en", "summary_zh", "summary_en"):
            self._require_string(exhibit.get(field), f"Exhibit {exhibit_id} must contain non-empty {field}")
        for field in ("facts_zh", "facts_en"):
            facts = exhibit.get(field)
            if not isinstance(facts, list) or not all(
                isinstance(item, str) and item.strip() for item in facts
            ):
                raise DataValidationError(f"{field} for exhibit {exhibit_id} must be a non-empty string list")
        exhibit_index[exhibit_id] = exhibit

    def _load(self) -> GuideData:
        map_data = self._read_json("building_map.json")
        exhibit_data = self._read_json("exhibits.json")

        nodes = map_data.get("nodes")
        edges = map_data.get("edges")
        exhibits = exhibit_data.get("exhibits")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise DataValidationError("building_map.json must contain nodes and edges arrays")
        if not isinstance(exhibits, list):
            raise DataValidationError("exhibits.json must contain an exhibits array")

        node_index: dict[str, dict[str, Any]] = {}
        for node in nodes:
            self._validate_node(node, node_index)

        for edge in edges:
            self._validate_edge(edge, node_index)

        exhibit_index: dict[str, dict[str, Any]] = {}
        for exhibit in exhibits:
            self._validate_exhibit(exhibit, exhibit_index, node_index)

        return GuideData(nodes=node_index, edges=edges, exhibits=exhibit_index)

    def _build_alias_index(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for node_id, node in self.data.nodes.items():
            candidates = [node_id, node.get("name_zh"), node.get("name_en")]
            candidates.extend(node.get("aliases", []))
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.strip():
                    aliases[candidate.strip().casefold()] = node_id
        return aliases

    def resolve_location(self, value: str) -> str:
        node_id = self._aliases.get(value.strip().casefold())
        if node_id is None:
            raise LocationNotFoundError(f"Unknown location: {value}")
        return node_id

    def get_location(self, value: str) -> dict[str, Any]:
        return self.data.nodes[self.resolve_location(value)]

    def list_locations(self) -> list[dict[str, Any]]:
        return sorted(
            self.data.nodes.values(),
            key=lambda node: (node.get("floor", 0), node["id"]),
        )

    def get_exhibit(self, exhibit_id: str) -> dict[str, Any]:
        exhibit = self.data.exhibits.get(exhibit_id)
        if exhibit is None:
            raise LocationNotFoundError(f"Unknown exhibit: {exhibit_id}")
        return exhibit

    def list_exhibits(self) -> list[dict[str, Any]]:
        return sorted(self.data.exhibits.values(), key=lambda exhibit: exhibit["id"])

    def resolve_destination(self, value: str) -> tuple[str, str, dict[str, Any] | None]:
        exhibit = self.data.exhibits.get(value.strip())
        if exhibit is not None:
            return exhibit["location_id"], "exhibit", exhibit
        try:
            node_id = self.resolve_location(value)
        except LocationNotFoundError as exc:
            raise LocationNotFoundError(f"Unknown destination: {value}") from exc
        return node_id, "location", None


class SqliteGuideRepository(GuideRepository):
    """Navigation repository backed by the map tables in guide.sqlite3."""

    def __init__(
        self,
        store: KnowledgeStore,
        data_dir: str | Path | None = None,
    ) -> None:
        self.store = store
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self.data = self._load_from_sqlite()
        self._aliases = self._build_alias_index()

    def refresh(self) -> None:
        self.data = self._load_from_sqlite()
        self._aliases = self._build_alias_index()

    def resolve_location(self, value: str) -> str:
        self.refresh()
        return super().resolve_location(value)

    def list_locations(self) -> list[dict[str, Any]]:
        self.refresh()
        return super().list_locations()

    def get_exhibit(self, exhibit_id: str) -> dict[str, Any]:
        self.refresh()
        return super().get_exhibit(exhibit_id)

    def list_exhibits(self) -> list[dict[str, Any]]:
        self.refresh()
        return super().list_exhibits()

    def resolve_destination(self, value: str) -> tuple[str, str, dict[str, Any] | None]:
        self.refresh()
        return super().resolve_destination(value)

    def _load_from_sqlite(self) -> GuideData:
        node_index: dict[str, dict[str, Any]] = {}
        for item in self.store.list_map_nodes(include_archived=False):
            node = {
                "id": item["node_id"],
                "name_zh": item["name_zh"],
                "name_en": item["name_en"] or item["name_zh"],
                "floor": item["floor"],
                "kind": item["kind"],
                "aliases": item["aliases"],
                "visual_landmarks": item["visual_landmarks"],
                "position": {
                    "x_ratio": item["x_norm"],
                    "y_ratio": item["y_norm"],
                    "estimated": item["calibration_status"] != "calibrated",
                },
                "source": item["map_source"],
                "navigation_notes": item["navigation_notes"],
                "calibration_status": item["calibration_status"],
                "routable": item["routable"],
            }
            self._validate_node(node, node_index)

        edges: list[dict[str, Any]] = []
        for item in self.store.list_map_edges(include_archived=False):
            if item["distance_m"] is None:
                continue
            edge = {
                "from": item["from_node_id"],
                "to": item["to_node_id"],
                "distance_m": item["distance_m"],
                "bidirectional": item["bidirectional"],
                "accessible": item["accessible"],
                "instructions": item["instructions"],
            }
            self._validate_edge(edge, node_index)
            edges.append(edge)

        exhibit_data = self._read_json("exhibits.json")
        exhibit_index: dict[str, dict[str, Any]] = {}
        for exhibit in exhibit_data.get("exhibits", []):
            self._validate_exhibit(exhibit, exhibit_index, node_index)
        return GuideData(nodes=node_index, edges=edges, exhibits=exhibit_index)
