from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import DataValidationError, LocationNotFoundError


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
            raise DataValidationError(f"缺少数据文件：{path}") from exc
        except json.JSONDecodeError as exc:
            raise DataValidationError(f"JSON 格式错误：{path}: {exc}") from exc

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
            raise DataValidationError(f"地点 {node_id} 的 visual_landmarks 必须是数组")
        for landmark in visual_landmarks:
            aliases = landmark.get("aliases") if isinstance(landmark, dict) else None
            weight = landmark.get("weight", 1) if isinstance(landmark, dict) else None
            if (
                not isinstance(aliases, list)
                or not aliases
                or not all(isinstance(alias, str) and alias.strip() for alias in aliases)
            ):
                raise DataValidationError(
                    f"地点 {node_id} 的每个视觉地标必须包含非空 aliases 数组"
                )
            if not isinstance(weight, (int, float)) or weight <= 0:
                raise DataValidationError(f"地点 {node_id} 的视觉地标权重必须大于 0")

    def _validate_node(self, node: Any, node_index: dict[str, dict[str, Any]]) -> None:
        if not isinstance(node, dict):
            raise DataValidationError("每个地点必须是对象")
        node_id = self._require_string(node.get("id"), "每个地点必须包含非空字符串 id")
        if node_id in node_index:
            raise DataValidationError(f"地点 ID 重复：{node_id}")
        for field in ("name_zh", "name_en", "kind"):
            self._require_string(node.get(field), f"地点 {node_id} 必须包含非空 {field}")
        floor = node.get("floor")
        if not isinstance(floor, int):
            raise DataValidationError(f"地点 {node_id} 的 floor 必须是整数")
        self._validate_aliases(node.get("aliases"), f"地点 {node_id} 的 aliases 必须是字符串数组")
        position = node.get("position")
        if position is not None:
            if not isinstance(position, dict):
                raise DataValidationError(f"地点 {node_id} 的 position 必须是对象")
            for field in ("x_m", "y_m"):
                if field in position and not isinstance(position[field], (int, float)):
                    raise DataValidationError(f"地点 {node_id} 的 position.{field} 必须是数字")
        self._validate_visual_landmarks(node_id, node)
        node_index[node_id] = node

    def _validate_instructions(self, start: str, end: str, instructions: Any) -> None:
        if instructions is None:
            return
        if not isinstance(instructions, dict):
            raise DataValidationError(f"连线指令必须是对象：{start} -> {end}")
        for direction in ("forward", "reverse"):
            localized = instructions.get(direction)
            if localized is None:
                continue
            if not isinstance(localized, dict):
                raise DataValidationError(
                    f"连线 {start} -> {end} 的 {direction} 指令必须是对象"
                )
            for language, text in localized.items():
                if language not in {"zh", "en"}:
                    raise DataValidationError(
                        f"连线 {start} -> {end} 包含未知语言指令：{language}"
                    )
                if not isinstance(text, str) or not text.strip():
                    raise DataValidationError(
                        f"连线 {start} -> {end} 的 {direction}.{language} 必须是非空字符串"
                    )

    def _validate_edge(self, edge: Any, node_index: dict[str, dict[str, Any]]) -> None:
        if not isinstance(edge, dict):
            raise DataValidationError("每条连线必须是对象")
        start, end = edge.get("from"), edge.get("to")
        if start not in node_index or end not in node_index:
            raise DataValidationError(f"连线引用未知地点：{start} -> {end}")
        distance = edge.get("distance_m")
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise DataValidationError(f"连线距离必须大于 0：{start} -> {end}")
        for field in ("bidirectional", "accessible"):
            if field in edge and not isinstance(edge[field], bool):
                raise DataValidationError(f"连线 {start} -> {end} 的 {field} 必须是布尔值")
        self._validate_instructions(start, end, edge.get("instructions"))

    def _validate_exhibit(
        self,
        exhibit: Any,
        exhibit_index: dict[str, dict[str, Any]],
        node_index: dict[str, dict[str, Any]],
    ) -> None:
        if not isinstance(exhibit, dict):
            raise DataValidationError("每个展品必须是对象")
        exhibit_id = self._require_string(exhibit.get("id"), "每个展品必须包含非空字符串 id")
        location_id = exhibit.get("location_id")
        if exhibit_id in exhibit_index:
            raise DataValidationError(f"展品 ID 重复：{exhibit_id}")
        if location_id not in node_index:
            raise DataValidationError(f"展品 {exhibit_id} 引用了未知地点 {location_id}")
        for field in ("name_zh", "name_en", "summary_zh", "summary_en"):
            self._require_string(exhibit.get(field), f"展品 {exhibit_id} 必须包含非空 {field}")
        for field in ("facts_zh", "facts_en"):
            facts = exhibit.get(field)
            if not isinstance(facts, list) or not all(
                isinstance(item, str) and item.strip() for item in facts
            ):
                raise DataValidationError(f"展品 {exhibit_id} 的 {field} 必须是非空字符串数组")
        exhibit_index[exhibit_id] = exhibit

    def _load(self) -> GuideData:
        map_data = self._read_json("building_map.json")
        exhibit_data = self._read_json("exhibits.json")

        nodes = map_data.get("nodes")
        edges = map_data.get("edges")
        exhibits = exhibit_data.get("exhibits")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise DataValidationError("building_map.json 必须包含 nodes 和 edges 数组")
        if not isinstance(exhibits, list):
            raise DataValidationError("exhibits.json 必须包含 exhibits 数组")

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
            raise LocationNotFoundError(f"未知地点：{value}")
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
            raise LocationNotFoundError(f"未知展品：{exhibit_id}")
        return exhibit

    def list_exhibits(self) -> list[dict[str, Any]]:
        return sorted(self.data.exhibits.values(), key=lambda exhibit: exhibit["id"])
