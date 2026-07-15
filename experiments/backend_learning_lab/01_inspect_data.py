from __future__ import annotations

from collections import Counter

from common import load_exhibits, load_map


def main() -> None:
    map_data = load_map()
    exhibit_data = load_exhibits()
    nodes = map_data["nodes"]
    edges = map_data["edges"]
    exhibits = exhibit_data["exhibits"]

    print("=== building_map.json ===")
    print("building:", map_data["building"])
    print("floor_plan:", map_data.get("floor_plan", {}).get("source"))
    print("nodes:", len(nodes))
    print("edges:", len(edges))
    print("node kinds:", dict(Counter(node["kind"] for node in nodes)))
    print("floors:", dict(Counter(node["floor"] for node in nodes)))
    print("accessible edges:", dict(Counter(edge.get("accessible", True) for edge in edges)))

    print("\n=== first 5 nodes ===")
    for node in nodes[:5]:
        print(
            node["id"],
            "|",
            node["name_zh"],
            "| kind=",
            node["kind"],
            "| aliases=",
            node.get("aliases", [])[:3],
        )

    print("\n=== first 5 edges ===")
    for edge in edges[:5]:
        print(
            edge["from"],
            "->",
            edge["to"],
            "| distance_m=",
            edge["distance_m"],
            "| accessible=",
            edge.get("accessible", True),
        )

    print("\n=== exhibits ===")
    for exhibit in exhibits:
        print(exhibit["id"], "at", exhibit["location_id"], "|", exhibit["name_zh"])


if __name__ == "__main__":
    main()
