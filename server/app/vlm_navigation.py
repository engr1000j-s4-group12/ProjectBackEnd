from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .errors import VlmNotConfiguredError, VlmResponseError
from .navigation import RouteResult, RouteStep
from .repository import GuideRepository
from .vlm import VlmClient


FALSE_VALUES = {"0", "false", "no", "off", "disabled"}
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
NAVIGATION_KINDS = {
    "corridor",
    "elevator",
    "fire_hydrant",
    "stairs",
    "open_area",
    "pantry",
    "path",
    "restroom",
    "entrance",
    "exit",
    "facility",
}


class VlmMapNavigator:
    """Route planner that asks the configured VLM to read floor-map images."""

    def __init__(
        self,
        repository: GuideRepository,
        vlm_client: VlmClient,
        map_dir: str | Path,
    ) -> None:
        self.repository = repository
        self.vlm_client = vlm_client
        self.map_dir = Path(map_dir)
        setting = os.getenv("VLM_ROUTE_ENABLED", "auto").strip().lower()
        self.strict = os.getenv("VLM_ROUTE_STRICT", "").strip().lower() in TRUE_VALUES
        self.enabled = (
            setting not in FALSE_VALUES
            and (self.vlm_client.configured or setting in TRUE_VALUES)
        )

    def _resolve_destination(self, value: str) -> tuple[str, str, dict[str, Any] | None]:
        if hasattr(self.repository, "resolve_destination"):
            return self.repository.resolve_destination(value)
        return self.repository.resolve_location(value), "location", None

    def _floor_map_image(self, floor: int) -> dict[str, Any]:
        path = self.map_dir / f"longbin-{floor}f-node-worksheet.png"
        if not path.exists():
            raise VlmResponseError(f"缺少 {floor}F 地图图片：{path}")
        return {
            "floor": floor,
            "content_type": "image/png",
            "content": path.read_bytes(),
        }

    def _guest_elevator_for_floor(self, floor: int) -> str:
        preferred = f"LB-{floor}F-ELEVATOR-GUEST"
        if preferred in self.repository.data.nodes:
            return preferred
        for node_id, node in self.repository.data.nodes.items():
            notes = node.get("navigation_notes", {})
            aliases = [str(item).casefold() for item in node.get("aliases", [])]
            if (
                int(node.get("floor", 0)) == floor
                and node.get("kind") == "elevator"
                and (notes.get("guest_access") is True or "guest elevator" in aliases)
            ):
                return node_id
        raise VlmResponseError(f"缺少 {floor}F 访客电梯节点")

    @staticmethod
    def _node_brief(node: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": node["id"],
            "floor": node["floor"],
            "kind": node["kind"],
            "name_zh": node["name_zh"],
            "name_en": node.get("name_en", ""),
            "aliases": list(node.get("aliases", []))[:8],
            "position": node.get("position", {}),
            "routable": bool(node.get("routable", False)),
        }

    @staticmethod
    def _node_summary(node: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": node["id"],
            "floor": node["floor"],
            "kind": node["kind"],
            "name_zh": node["name_zh"],
            "aliases": list(node.get("aliases", []))[:4],
        }

    def _floor_node_summaries(self, floors: set[int], pinned_ids: set[str]) -> list[dict[str, Any]]:
        nodes = []
        for node in self.repository.list_locations():
            if int(node["floor"]) not in floors:
                continue
            if (
                node["id"] not in pinned_ids
                and not bool(node.get("routable", False))
                and str(node.get("kind", "")) not in NAVIGATION_KINDS
            ):
                continue
            if len(nodes) >= 80 and node["id"] not in pinned_ids:
                continue
            nodes.append(self._node_summary(node))
        return nodes

    @staticmethod
    def _distance(value: Any) -> float:
        try:
            distance = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, distance)

    @staticmethod
    def _confidence(value: Any) -> float | None:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return None
        if confidence < 0 or confidence > 1:
            return None
        return confidence

    def _route_step(
        self,
        raw: Any,
        index: int,
        start_id: str,
        destination_id: str,
        language: str,
    ) -> RouteStep:
        if not isinstance(raw, dict):
            raise VlmResponseError("VLM steps 中每一项必须是对象")
        from_id = str(raw.get("from_id") or "").strip() or f"VLM-WAYPOINT-{index}"
        to_id = str(raw.get("to_id") or "").strip() or f"VLM-WAYPOINT-{index + 1}"
        if index == 0:
            from_id = start_id
        instruction = str(raw.get("instruction") or "").strip()
        if not instruction:
            instruction = "继续沿地图指引前进。" if language == "zh" else "Continue along the mapped route."
        return RouteStep(
            from_id=from_id,
            to_id=to_id,
            distance_m=self._distance(raw.get("distance_m")),
            instruction=instruction,
        )

    def _parse_plan(
        self,
        plan: dict[str, Any],
        start_id: str,
        destination_id: str,
        start_node: dict[str, Any],
        destination_node: dict[str, Any],
        language: str,
    ) -> RouteResult:
        raw_steps = plan.get("steps") or []
        steps = [
            self._route_step(raw_step, index, start_id, destination_id, language)
            for index, raw_step in enumerate(raw_steps)
        ]
        if steps:
            steps[-1] = RouteStep(
                from_id=steps[-1].from_id,
                to_id=destination_id,
                distance_m=steps[-1].distance_m,
                instruction=steps[-1].instruction,
            )
        total_distance = self._distance(plan.get("total_distance_m"))
        if total_distance <= 0:
            total_distance = sum(step.distance_m for step in steps)
        announcement = str(plan.get("announcement") or "").strip()
        if not announcement:
            if language == "en":
                announcement = (
                    f"Please follow the mapped route from {start_node['name_en']} "
                    f"to {destination_node['name_en']}."
                )
            else:
                announcement = f"请根据地图路线从{start_node['name_zh']}前往{destination_node['name_zh']}。"
        if not steps and start_id != destination_id:
            steps = [
                RouteStep(
                    from_id=start_id,
                    to_id=destination_id,
                    distance_m=total_distance,
                    instruction=announcement,
                )
            ]
        assumptions = [
            str(item).strip()
            for item in plan.get("assumptions", [])
            if str(item).strip()
        ]
        return RouteResult(
            from_id=start_id,
            to_id=destination_id,
            total_distance_m=total_distance,
            announcement=announcement,
            steps=steps,
            planner="qwen_vlm_map",
            confidence=self._confidence(plan.get("confidence")),
            assumptions=assumptions,
        )

    async def _plan_same_floor(
        self,
        start_id: str,
        destination_id: str,
        language: str,
        accessible_only: bool,
        destination_type: str = "location",
        exhibit: dict[str, Any] | None = None,
    ) -> RouteResult:
        start_node = self.repository.data.nodes[start_id]
        destination_node = self.repository.data.nodes[destination_id]
        if start_id == destination_id:
            return RouteResult(
                from_id=start_id,
                to_id=destination_id,
                total_distance_m=0,
                announcement=(
                    f"You are already at {destination_node['name_en']}."
                    if language == "en"
                    else f"您已在{destination_node['name_zh']}。"
                ),
                steps=[],
                planner="qwen_vlm_map",
                confidence=1.0,
                assumptions=[],
            )

        floor = int(start_node["floor"])
        if floor != int(destination_node["floor"]):
            raise VlmResponseError("同楼层 VLM 分段收到跨楼层节点")
        floors = {floor}
        context = {
            "segment": "same_floor",
            "language": language,
            "accessible_only": accessible_only,
            "start": self._node_brief(start_node),
            "destination": self._node_brief(destination_node),
            "destination_type": destination_type,
            "destination_exhibit": exhibit,
            "floors": sorted(floors),
            "floor_scale": {
                "outer_outline_m": {"short_side": 70, "long_side": 80},
                "conservative_range_m": {"short_side": [65, 75], "long_side": [75, 85]},
            },
            "guest_elevator_rules": [
                "1F northwest restricted/no-entry elevator must not be used by visitors.",
                "Guest-elevator exits face north.",
            ],
            "known_nodes_on_uploaded_floors": self._floor_node_summaries(
                floors,
                {start_id, destination_id},
            ),
        }
        images = [self._floor_map_image(floor) for floor in sorted(floors)]
        raw_plan = await self.vlm_client.plan_route_from_maps(images, context)
        return self._parse_plan(
            raw_plan,
            start_id,
            destination_id,
            start_node,
            destination_node,
            language,
        )

    def _elevator_transfer_step(
        self,
        source_elevator_id: str,
        destination_elevator_id: str,
        language: str,
    ) -> RouteStep:
        source_floor = int(self.repository.data.nodes[source_elevator_id]["floor"])
        destination_floor = int(self.repository.data.nodes[destination_elevator_id]["floor"])
        distance = abs(destination_floor - source_floor) * 4.0
        if language == "en":
            instruction = (
                f"Take the guest elevator to Floor {destination_floor}; "
                "after exiting, face north before continuing."
            )
        else:
            numerals = {1: "一", 2: "二", 3: "三", 4: "四"}
            instruction = (
                f"乘坐访客电梯到{numerals.get(destination_floor, destination_floor)}楼，"
                "出电梯后面向北，再继续按地图路线前进。"
            )
        return RouteStep(
            from_id=source_elevator_id,
            to_id=destination_elevator_id,
            distance_m=distance,
            instruction=instruction,
        )

    async def _plan_cross_floor(
        self,
        start_id: str,
        destination_id: str,
        language: str,
        accessible_only: bool,
        destination_type: str,
        exhibit: dict[str, Any] | None,
    ) -> RouteResult:
        start_node = self.repository.data.nodes[start_id]
        destination_node = self.repository.data.nodes[destination_id]
        start_floor = int(start_node["floor"])
        destination_floor = int(destination_node["floor"])
        source_elevator_id = self._guest_elevator_for_floor(start_floor)
        destination_elevator_id = self._guest_elevator_for_floor(destination_floor)

        first = await self._plan_same_floor(
            start_id,
            source_elevator_id,
            language,
            accessible_only,
            "location",
            None,
        )
        second = await self._plan_same_floor(
            destination_elevator_id,
            destination_id,
            language,
            accessible_only,
            destination_type,
            exhibit,
        )
        transfer = self._elevator_transfer_step(
            source_elevator_id,
            destination_elevator_id,
            language,
        )
        steps = [*first.steps, transfer, *second.steps]
        destination_label = (
            destination_node.get("name_en") if language == "en" else destination_node.get("name_zh")
        ) or destination_id
        if language == "en":
            announcement = (
                f"Go to the guest elevator, take it to Floor {destination_floor}, "
                f"then follow the mapped route to {destination_label}."
            )
        else:
            numerals = {1: "一", 2: "二", 3: "三", 4: "四"}
            announcement = (
                f"请先前往访客电梯，乘坐电梯到{numerals.get(destination_floor, destination_floor)}楼，"
                f"出电梯后按地图路线前往{destination_label}。"
            )
        confidences = [
            item
            for item in [first.confidence, second.confidence, 0.8]
            if item is not None
        ]
        split_assumption = (
            "Cross-floor route is split into source-floor and destination-floor VLM map reads."
            if language == "en"
            else "跨楼层路线已拆分为起点楼层和目标楼层两次 VLM 地图读取。"
        )
        assumptions = [split_assumption, *first.assumptions, *second.assumptions]
        return RouteResult(
            from_id=start_id,
            to_id=destination_id,
            total_distance_m=sum(step.distance_m for step in steps),
            announcement=announcement,
            steps=steps,
            planner="qwen_vlm_map",
            confidence=min(confidences) if confidences else None,
            assumptions=list(dict.fromkeys(assumptions)),
        )

    async def plan(
        self,
        start_value: str,
        destination_value: str,
        language: str = "zh",
        accessible_only: bool = False,
    ) -> RouteResult:
        if not self.enabled:
            raise VlmNotConfiguredError("VLM 地图寻路未启用")
        start_id = self.repository.resolve_location(start_value)
        destination_id, destination_type, exhibit = self._resolve_destination(destination_value)
        start_node = self.repository.data.nodes[start_id]
        destination_node = self.repository.data.nodes[destination_id]
        if int(start_node["floor"]) == int(destination_node["floor"]):
            return await self._plan_same_floor(
                start_id,
                destination_id,
                language,
                accessible_only,
                destination_type,
                exhibit,
            )
        return await self._plan_cross_floor(
            start_id,
            destination_id,
            language,
            accessible_only,
            destination_type,
            exhibit,
        )
