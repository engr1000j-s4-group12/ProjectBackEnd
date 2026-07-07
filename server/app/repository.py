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
            node_id = node.get("id") if isinstance(node, dict) else None
            if not isinstance(node_id, str) or not node_id:
                raise DataValidationError("每个地点必须包含非空字符串 id")
            if node_id in node_index:
                raise DataValidationError(f"地点 ID 重复：{node_id}")
            visual_landmarks = node.get("visual_landmarks", [])
            if not isinstance(visual_landmarks, list):
                raise DataValidationError(f"地点 {node_id} 的 visual_landmarks 必须是数组")
            for landmark in visual_landmarks:
                aliases = landmark.get("aliases") if isinstance(landmark, dict) else None
                weight = landmark.get("weight", 1) if isinstance(landmark, dict) else None
                if (
                    not isinstance(aliases, list)
                    or not aliases
                    or not all(isinstance(alias, str) and alias for alias in aliases)
                ):
                    raise DataValidationError(
                        f"地点 {node_id} 的每个视觉地标必须包含非空 aliases 数组"
                    )
                if not isinstance(weight, (int, float)) or weight <= 0:
                    raise DataValidationError(
                        f"地点 {node_id} 的视觉地标权重必须大于 0"
                    )
            node_index[node_id] = node

        for edge in edges:
            if not isinstance(edge, dict):
                raise DataValidationError("每条连线必须是对象")
            start, end = edge.get("from"), edge.get("to")
            if start not in node_index or end not in node_index:
                raise DataValidationError(f"连线引用未知地点：{start} -> {end}")
            distance = edge.get("distance_m")
            if not isinstance(distance, (int, float)) or distance <= 0:
                raise DataValidationError(f"连线距离必须大于 0：{start} -> {end}")

        exhibit_index: dict[str, dict[str, Any]] = {}
        for exhibit in exhibits:
            exhibit_id = exhibit.get("id") if isinstance(exhibit, dict) else None
            location_id = exhibit.get("location_id") if isinstance(exhibit, dict) else None
            if not isinstance(exhibit_id, str) or not exhibit_id:
                raise DataValidationError("每个展品必须包含非空字符串 id")
            if exhibit_id in exhibit_index:
                raise DataValidationError(f"展品 ID 重复：{exhibit_id}")
            if location_id not in node_index:
                raise DataValidationError(f"展品 {exhibit_id} 引用了未知地点 {location_id}")
            exhibit_index[exhibit_id] = exhibit

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
