from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any

from .errors import RouteNotFoundError
from .repository import GuideRepository


@dataclass(frozen=True)
class RouteStep:
    from_id: str
    to_id: str
    distance_m: float
    instruction: str


@dataclass(frozen=True)
class RouteResult:
    from_id: str
    to_id: str
    total_distance_m: float
    steps: list[RouteStep]


class Navigator:
    def __init__(self, repository: GuideRepository) -> None:
        self.repository = repository

    def _instruction(
        self,
        edge: dict[str, Any],
        start: str,
        end: str,
        language: str,
    ) -> str:
        direction = "forward" if edge["from"] == start else "reverse"
        instructions = edge.get("instructions", {})
        localized = instructions.get(direction, {})
        instruction = localized.get(language) or localized.get("zh")
        if isinstance(instruction, str) and instruction:
            return instruction

        end_node = self.repository.data.nodes[end]
        name_key = "name_en" if language == "en" else "name_zh"
        destination_name = end_node.get(name_key) or end_node["id"]
        distance = edge["distance_m"]
        if language == "en":
            return f"Continue for {distance:g} meters to {destination_name}."
        return f"前进 {distance:g} 米到达{destination_name}。"

    def plan(
        self,
        start_value: str,
        destination_value: str,
        language: str = "zh",
        accessible_only: bool = False,
    ) -> RouteResult:
        start = self.repository.resolve_location(start_value)
        destination = self.repository.resolve_location(destination_value)
        if start == destination:
            return RouteResult(start, destination, 0, [])

        adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {
            node_id: [] for node_id in self.repository.data.nodes
        }
        for edge in self.repository.data.edges:
            if accessible_only and not edge.get("accessible", True):
                continue
            adjacency[edge["from"]].append((edge["to"], edge))
            if edge.get("bidirectional", True):
                adjacency[edge["to"]].append((edge["from"], edge))

        distances = {node_id: float("inf") for node_id in adjacency}
        distances[start] = 0.0
        previous: dict[str, tuple[str, dict[str, Any]]] = {}
        queue: list[tuple[float, str]] = [(0.0, start)]

        while queue:
            current_distance, current = heapq.heappop(queue)
            if current_distance != distances[current]:
                continue
            if current == destination:
                break
            for neighbor, edge in adjacency[current]:
                candidate = current_distance + float(edge["distance_m"])
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = (current, edge)
                    heapq.heappush(queue, (candidate, neighbor))

        if destination not in previous:
            raise RouteNotFoundError(
                f"从 {start} 到 {destination} 不存在满足条件的路线"
            )

        reversed_segments: list[tuple[str, str, dict[str, Any]]] = []
        cursor = destination
        while cursor != start:
            parent, edge = previous[cursor]
            reversed_segments.append((parent, cursor, edge))
            cursor = parent
        reversed_segments.reverse()

        steps = [
            RouteStep(
                from_id=segment_start,
                to_id=segment_end,
                distance_m=float(edge["distance_m"]),
                instruction=self._instruction(
                    edge, segment_start, segment_end, language
                ),
            )
            for segment_start, segment_end, edge in reversed_segments
        ]
        return RouteResult(start, destination, distances[destination], steps)
