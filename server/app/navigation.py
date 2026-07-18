from __future__ import annotations

import heapq
import re
from dataclasses import dataclass
from dataclasses import field
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
    announcement: str
    steps: list[RouteStep]
    planner: str = "deterministic"
    confidence: float | None = None
    assumptions: list[str] = field(default_factory=list)


class Navigator:
    def __init__(self, repository: GuideRepository) -> None:
        self.repository = repository

    @staticmethod
    def _floor_name(floor: int, language: str) -> str:
        if language == "en":
            return f"Floor {floor}"
        numerals = {1: "一", 2: "二", 3: "三", 4: "四"}
        return f"{numerals.get(floor, floor)}楼"

    def _destination_name(self, node: dict[str, Any], language: str) -> str:
        if language == "en":
            return str(node.get("name_en") or node["id"])
        node_id = str(node["id"])
        if node_id == "LB-4F-REGION-F":
            return "学院介绍区域"
        room = re.search(r"-ROOM-([A-Z0-9]+)$", node_id)
        if node_id == "LB-3F-ROOM-300" and room:
            return f"{room.group(1)}会议室"
        return str(node.get("name_zh") or node_id)

    def _announcement(self, start: str, destination: str, language: str) -> str:
        start_node = self.repository.data.nodes[start]
        destination_node = self.repository.data.nodes[destination]
        start_floor = int(start_node["floor"])
        destination_floor = int(destination_node["floor"])
        destination_name = self._destination_name(destination_node, language)

        if language == "en":
            if start == destination:
                return f"You are already at {destination_name}."
            if start_floor == destination_floor:
                if destination == "LB-3F-ROOM-300":
                    return (
                        f"{destination_name} is on your current floor, "
                        "near the elevator exit."
                    )
                return f"{destination_name} is on your current floor."
            if destination == "LB-4F-REGION-F":
                return (
                    "The college introduction area is on Floor 4. Take the guest "
                    "elevator to Floor 4, turn right after exiting, then right again; "
                    "the college introduction is on your left."
                )
            return (
                f"{destination_name} is on {self._floor_name(destination_floor, language)}. "
                f"Take the guest elevator to {self._floor_name(destination_floor, language)} "
                "and follow the guidance after exiting."
            )

        floor_name = self._floor_name(destination_floor, language)
        if start == destination:
            return f"您已在{destination_name}。"
        if start_floor == destination_floor:
            if destination == "LB-3F-ROOM-300":
                return f"{destination_name}就在您所在的{floor_name}，位于电梯出口附近。"
            return f"{destination_name}就在您所在的{floor_name}。"
        if destination == "LB-4F-REGION-F":
            return (
                "学院介绍区域在四楼。请乘坐访客电梯到四楼，出电梯后右转，"
                "再右转，学院介绍在左侧。"
            )
        return (
            f"{destination_name}在{floor_name}。请乘坐访客电梯到{floor_name}，"
            "出电梯后按指引前往。"
        )

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
            return RouteResult(
                start,
                destination,
                0,
                self._announcement(start, destination, language),
                [],
            )

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
        return RouteResult(
            start,
            destination,
            distances[destination],
            self._announcement(start, destination, language),
            steps,
        )
