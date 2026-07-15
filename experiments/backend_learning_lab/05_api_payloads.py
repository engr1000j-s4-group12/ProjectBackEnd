from __future__ import annotations

import json


def show(title: str, method: str, endpoint: str, payload: dict | None = None) -> None:
    print(f"\n=== {title} ===")
    print(method, endpoint)
    if payload is not None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    show("健康检查", "GET", "/health")
    show("地点列表", "GET", "/api/v1/places")
    show(
        "二维码/锚点定位",
        "POST",
        "/api/v1/localize",
        {"marker_id": "LB-4F-ROOM-400A"},
    )
    show(
        "结构化视觉定位",
        "POST",
        "/api/v1/localize/visual",
        {
            "objects": [{"label": "消防栓", "confidence": 0.7}],
            "recognized_texts": ["413A"],
            "scene_description": "走廊右侧可见房间号和消防栓",
            "floor_hint": 4,
        },
    )
    show(
        "路线规划",
        "POST",
        "/api/v1/route",
        {
            "from_location": "LB-4F-ROOM-400A",
            "to_location": "LB-4F-ROOM-429B",
            "language": "zh",
            "accessible_only": False,
        },
    )
    show(
        "展品上下文",
        "POST",
        "/api/v1/exhibits/ROBOT-001/context",
        {"question": "这个展品在哪里？", "language": "zh"},
    )


if __name__ == "__main__":
    main()
