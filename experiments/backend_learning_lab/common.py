from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def load_json(filename: str) -> Any:
    with (DATA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def load_map() -> dict[str, Any]:
    return load_json("building_map.json")


def load_exhibits() -> dict[str, Any]:
    return load_json("exhibits.json")


def node_index(map_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in map_data["nodes"]}


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized).strip()


def build_alias_index(map_data: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in map_data["nodes"]:
        values = [node["id"], node.get("name_zh"), node.get("name_en")]
        values.extend(node.get("aliases", []))
        for value in values:
            if isinstance(value, str) and value.strip():
                aliases[normalize(value)] = node["id"]
    return aliases


def resolve_location(value: str, aliases: dict[str, str]) -> str | None:
    return aliases.get(normalize(value))


def edge_neighbors(
    edges: list[dict[str, Any]], *, accessible_only: bool = False
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for edge in edges:
        if accessible_only and not edge.get("accessible", True):
            continue
        start = edge["from"]
        end = edge["to"]
        graph.setdefault(start, []).append((end, edge))
        if edge.get("bidirectional", True):
            graph.setdefault(end, []).append((start, edge))
    return graph


def matches(alias: str, observation: str) -> bool:
    alias_n = normalize(alias)
    observation_n = normalize(observation)
    if not alias_n or not observation_n:
        return False
    if alias_n == observation_n:
        return True
    contains_cjk = bool(re.search(r"[\u4e00-\u9fff]", alias_n + observation_n))
    minimum = 2 if contains_cjk else 3
    shorter = min(len(alias_n), len(observation_n))
    return shorter >= minimum and (
        alias_n in observation_n or observation_n in alias_n
    )
