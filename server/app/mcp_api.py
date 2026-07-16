from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Body

from .errors import GuideServerError
from .guide_persona import GUIDE_PERSONA
from .knowledge import KnowledgeStore
from .navigation import Navigator


PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "museum.search_knowledge",
        "description": "查询浦江国际学院、龙宾楼、设施和展品资料。默认不返回归档内容。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "kind": {"type": "string", "enum": ["permanent", "event", "exhibit", "facility"]},
                "floor": {"type": "integer", "minimum": 1, "maximum": 4},
                "include_archived": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "museum.get_place_info",
        "description": "按地图区域节点 ID 查询该位置绑定的介绍、展览或设施。",
        "inputSchema": {
            "type": "object",
            "properties": {"node_id": {"type": "string"}},
            "required": ["node_id"],
        },
    },
    {
        "name": "museum.search_events",
        "description": "查询当前或已归档的活动和临时展览。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "floor": {"type": "integer", "minimum": 1, "maximum": 4},
                "include_archived": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "museum.get_event",
        "description": "按数据库记录 ID 读取一个活动或展览。",
        "inputSchema": {
            "type": "object",
            "properties": {"record_id": {"type": "integer"}},
            "required": ["record_id"],
        },
    },
    {
        "name": "museum.get_nearby_events",
        "description": "根据当前节点查询同一楼层的有效活动，精确节点优先。",
        "inputSchema": {
            "type": "object",
            "properties": {"node_id": {"type": "string"}},
            "required": ["node_id"],
        },
    },
    {
        "name": "museum.get_visitor_context",
        "description": "读取管理者预先录入且尚未归档的代表团来访任务。",
        "inputSchema": {
            "type": "object",
            "properties": {"visit_id": {"type": "integer"}},
        },
    },
    {
        "name": "museum.get_guide_context",
        "description": "组合 Guide Persona、代表团任务和当前位置资料。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "visit_id": {"type": "integer"},
                "current_node": {"type": "string"},
            },
        },
    },
    {
        "name": "museum.search_map_nodes",
        "description": "查询 SQLite 中的四层楼房间、开放空间和公共设施节点。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "floor": {"type": "integer", "minimum": 1, "maximum": 4},
                "kind": {"type": "string"},
                "routable": {"type": "boolean"},
            },
        },
    },
    {
        "name": "museum.get_map_node",
        "description": "按节点 ID 读取 SQLite 地图节点、坐标和校准状态。",
        "inputSchema": {
            "type": "object",
            "properties": {"node_id": {"type": "string"}},
            "required": ["node_id"],
        },
    },
    {
        "name": "museum.plan_route",
        "description": "使用 SQLite 地图节点和连线计算确定性最短路线。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_location": {"type": "string"},
                "to_location": {"type": "string"},
                "language": {"type": "string", "enum": ["zh", "en"], "default": "zh"},
                "accessible_only": {"type": "boolean", "default": False},
            },
            "required": ["from_location", "to_location"],
        },
    },
]


def _floor(node_id: str) -> int | None:
    match = re.search(r"LB-([1-4])F-", node_id.upper())
    return int(match.group(1)) if match else None


def _visit_context(store: KnowledgeStore, visit_id: int | None) -> dict[str, Any] | None:
    visits = store.list_visits(include_archived=False)
    if visit_id is not None:
        return next((item for item in visits if item["id"] == visit_id), None)
    return visits[0] if len(visits) == 1 else None


def _call_tool(
    store: KnowledgeStore,
    navigator: Navigator,
    name: str,
    arguments: dict[str, Any],
) -> Any:
    if name == "museum.search_knowledge":
        records = store.list_entries(
            floor=arguments.get("floor"),
            kind=arguments.get("kind"),
            include_archived=bool(arguments.get("include_archived", False)),
            query=arguments.get("q"),
        )
        return {"records": records, "count": len(records)}
    if name == "museum.get_place_info":
        node_id = str(arguments["node_id"])
        records = store.list_entries(
            include_archived=False,
            query=node_id,
        )
        records = [item for item in records if item["node_id"] == node_id]
        return {"node_id": node_id, "records": records}
    if name == "museum.search_events":
        events = store.list_entries(
            floor=arguments.get("floor"),
            kind="event",
            include_archived=bool(arguments.get("include_archived", False)),
            query=arguments.get("q"),
        )
        return {"events": events, "count": len(events)}
    if name == "museum.get_event":
        event = store.get_entry(int(arguments["record_id"]))
        if event["kind"] != "event":
            raise KeyError(arguments["record_id"])
        event["media"] = store.list_media(event["id"])
        return event
    if name == "museum.get_nearby_events":
        node_id = str(arguments["node_id"])
        events = store.list_entries(floor=_floor(node_id), kind="event")
        events.sort(key=lambda item: item["node_id"] != node_id)
        return {"node_id": node_id, "events": events}
    if name == "museum.get_visitor_context":
        return {"visit": _visit_context(store, arguments.get("visit_id"))}
    if name == "museum.get_guide_context":
        current_node = arguments.get("current_node")
        records = (
            store.list_entries(floor=_floor(current_node), include_archived=False)
            if current_node
            else []
        )
        exact = [item for item in records if item["node_id"] == current_node]
        return {
            "persona": GUIDE_PERSONA,
            "visit": _visit_context(store, arguments.get("visit_id")),
            "current_node": current_node,
            "location_records": exact or records,
        }
    if name == "museum.search_map_nodes":
        nodes = store.list_map_nodes(
            floor=arguments.get("floor"),
            kind=arguments.get("kind"),
            query=arguments.get("q"),
            routable=arguments.get("routable"),
        )
        return {"nodes": nodes, "count": len(nodes)}
    if name == "museum.get_map_node":
        return store.get_map_node(str(arguments["node_id"]))
    if name == "museum.plan_route":
        route = navigator.plan(
            str(arguments["from_location"]),
            str(arguments["to_location"]),
            str(arguments.get("language", "zh")),
            bool(arguments.get("accessible_only", False)),
        )
        return {
            "from_id": route.from_id,
            "to_id": route.to_id,
            "total_distance_m": route.total_distance_m,
            "announcement": route.announcement,
            "steps": [step.__dict__ for step in route.steps],
        }
    raise NotImplementedError(name)


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def build_mcp_router(store: KnowledgeStore, navigator: Navigator) -> APIRouter:
    router = APIRouter()

    @router.post("/mcp", tags=["mcp"])
    async def mcp_rpc(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return _error(request_id, -32600, "Invalid Request")
        method = request["method"]
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "longbin-guide-mcp", "version": "1.0.0"},
                },
            )
        if method == "notifications/initialized":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": TOOLS})
        if method != "tools/call":
            return _error(request_id, -32601, "Method not found")

        params = request.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(request_id, -32602, "Invalid params")
        try:
            structured = _call_tool(store, navigator, name, arguments)
        except NotImplementedError:
            return _error(request_id, -32601, f"Unknown tool: {name}")
        except (KeyError, TypeError, ValueError) as exc:
            return _error(request_id, -32602, f"Invalid tool arguments: {exc}")
        except GuideServerError as exc:
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
        return _result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(structured, ensure_ascii=False),
                    }
                ],
                "structuredContent": structured,
                "isError": False,
            },
        )

    return router
