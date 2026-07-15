from __future__ import annotations

import heapq
import sys
from typing import Any

from common import build_alias_index, edge_neighbors, load_map, node_index, resolve_location


def shortest_path(
    edges: list[dict[str, Any]],
    start: str,
    destination: str,
    *,
    accessible_only: bool = False,
) -> tuple[float, list[tuple[str, str, dict[str, Any]]]]:
    graph = edge_neighbors(edges, accessible_only=accessible_only)
    distances = {start: 0.0}
    previous: dict[str, tuple[str, dict[str, Any]]] = {}
    queue: list[tuple[float, str]] = [(0.0, start)]

    while queue:
        distance, current = heapq.heappop(queue)
        if distance != distances[current]:
            continue
        if current == destination:
            break
        for neighbor, edge in graph.get(current, []):
            candidate = distance + float(edge["distance_m"])
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = (current, edge)
                heapq.heappush(queue, (candidate, neighbor))

    if destination not in distances:
        raise SystemExit(f"no route from {start} to {destination}")

    path: list[tuple[str, str, dict[str, Any]]] = []
    cursor = destination
    while cursor != start:
        parent, edge = previous[cursor]
        path.append((parent, cursor, edge))
        cursor = parent
    path.reverse()
    return distances[destination], path


def instruction(edge: dict[str, Any], start: str, end: str, nodes: dict[str, dict[str, Any]]) -> str:
    direction = "forward" if edge["from"] == start else "reverse"
    text = edge.get("instructions", {}).get(direction, {}).get("zh")
    if text:
        return text
    return f"前进 {edge['distance_m']} 米到达{nodes[end]['name_zh']}。"


def main() -> None:
    start_value = sys.argv[1] if len(sys.argv) > 1 else "LB-4F-ROOM-400A"
    end_value = sys.argv[2] if len(sys.argv) > 2 else "LB-4F-ROOM-429B"
    accessible_only = "--accessible" in sys.argv

    map_data = load_map()
    aliases = build_alias_index(map_data)
    nodes = node_index(map_data)
    start = resolve_location(start_value, aliases)
    end = resolve_location(end_value, aliases)
    if start is None or end is None:
        raise SystemExit(f"unknown start or end: {start_value!r}, {end_value!r}")

    total, path = shortest_path(
        map_data["edges"],
        start,
        end,
        accessible_only=accessible_only,
    )

    print("start:", start)
    print("end:", end)
    print("accessible_only:", accessible_only)
    print("total_distance_m:", round(total, 1))
    print("steps:", len(path))
    print()
    for index, (segment_start, segment_end, edge) in enumerate(path, start=1):
        print(f"{index}. {segment_start} -> {segment_end} ({edge['distance_m']}m)")
        print("   ", instruction(edge, segment_start, segment_end, nodes))


if __name__ == "__main__":
    main()
