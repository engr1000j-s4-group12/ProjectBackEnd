from pathlib import Path
from typing import Any

import pytest

from server.app.knowledge import KnowledgeStore
from server.app.repository import SqliteGuideRepository
from server.app.vlm_navigation import VlmMapNavigator


class FakeVlmClient:
    configured = True

    def __init__(self) -> None:
        self.context: dict[str, Any] | None = None
        self.floors: list[int] = []
        self.calls: list[tuple[list[int], dict[str, Any]]] = []

    async def plan_route_from_maps(
        self,
        map_images: list[dict],
        context: dict,
    ) -> dict:
        self.context = context
        self.floors = [image["floor"] for image in map_images]
        self.calls.append((self.floors, context))
        return {
            "from_id": context["start"]["id"],
            "to_id": context["destination"]["id"],
            "total_distance_m": 58,
            "announcement": "请沿四楼走廊前往 429B。",
            "steps": [
                {
                    "from_id": context["start"]["id"],
                    "to_id": "四楼中部走廊",
                    "distance_m": 30,
                    "instruction": "从 400A 出门后沿走廊向东走。",
                },
                {
                    "from_id": "四楼中部走廊",
                    "to_id": context["destination"]["id"],
                    "distance_m": 28,
                    "instruction": "继续沿南侧通道前往 429B。",
                },
            ],
            "confidence": 0.72,
            "assumptions": ["距离按地图比例估算。"],
        }


@pytest.mark.anyio
async def test_vlm_map_navigator_returns_qwen_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VLM_ROUTE_ENABLED", "1")
    store = KnowledgeStore(tmp_path / "guide.sqlite3")
    repository = SqliteGuideRepository(store)
    fake_vlm = FakeVlmClient()
    navigator = VlmMapNavigator(
        repository,
        fake_vlm,
        Path("server/app/static/admin/maps"),
    )

    result = await navigator.plan("400A", "429B", "zh")

    assert result.planner == "qwen_vlm_map"
    assert result.from_id == "LB-4F-ROOM-400A"
    assert result.to_id == "LB-4F-ROOM-429B"
    assert result.total_distance_m == 58
    assert result.confidence == 0.72
    assert result.assumptions == ["距离按地图比例估算。"]
    assert result.steps[0].from_id == "LB-4F-ROOM-400A"
    assert result.steps[-1].to_id == "LB-4F-ROOM-429B"
    assert fake_vlm.floors == [4]
    assert fake_vlm.context is not None
    assert fake_vlm.context["floor_scale"]["outer_outline_m"]["long_side"] == 80


@pytest.mark.anyio
async def test_vlm_map_navigator_splits_cross_floor_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VLM_ROUTE_ENABLED", "1")
    store = KnowledgeStore(tmp_path / "guide.sqlite3")
    repository = SqliteGuideRepository(store)
    fake_vlm = FakeVlmClient()
    navigator = VlmMapNavigator(
        repository,
        fake_vlm,
        Path("server/app/static/admin/maps"),
    )

    result = await navigator.plan("LB-1F-OPEN-08", "429B", "zh")

    assert result.planner == "qwen_vlm_map"
    assert result.from_id == "LB-1F-OPEN-08"
    assert result.to_id == "LB-4F-ROOM-429B"
    assert result.steps[0].from_id == "LB-1F-OPEN-08"
    transfer = next(
        step
        for step in result.steps
        if step.from_id == "LB-1F-ELEVATOR-GUEST"
    )
    assert transfer.to_id == "LB-4F-ELEVATOR-GUEST"
    assert result.steps[-1].to_id == "LB-4F-ROOM-429B"
    assert fake_vlm.calls[0][0] == [1]
    assert fake_vlm.calls[1][0] == [4]
    assert "跨楼层路线已拆分" in result.assumptions[0]
