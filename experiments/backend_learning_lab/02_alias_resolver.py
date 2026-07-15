from __future__ import annotations

import sys

from common import build_alias_index, load_map, node_index, resolve_location


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or "400A房间"
    map_data = load_map()
    aliases = build_alias_index(map_data)
    nodes = node_index(map_data)
    node_id = resolve_location(query, aliases)

    print("query:", query)
    print("alias count:", len(aliases))

    if node_id is None:
        print("result: not found")
        print("try examples: 400A房间, LB-4F-ROOM-413A, 西北侧楼梯")
        return

    node = nodes[node_id]
    print("result node_id:", node_id)
    print("name_zh:", node["name_zh"])
    print("name_en:", node["name_en"])
    print("kind:", node["kind"])
    print("position:", node.get("position"))
    print("aliases:", node.get("aliases", []))


if __name__ == "__main__":
    main()
