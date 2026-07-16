from pathlib import Path

import httpx
import pytest

from server.app.knowledge import KnowledgeStore
from server.app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def mcp_client(tmp_path: Path):
    store = KnowledgeStore(tmp_path / "guide.sqlite3")
    app = create_app(knowledge_store=store)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def request(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    return body


@pytest.mark.anyio
async def test_mcp_initialize_and_list_tools(mcp_client: httpx.AsyncClient) -> None:
    response = await mcp_client.post("/mcp", json=request("initialize"))
    assert response.status_code == 200
    initialized = response.json()["result"]
    assert initialized["protocolVersion"] == "2025-06-18"
    assert initialized["serverInfo"]["name"] == "longbin-guide-mcp"

    response = await mcp_client.post("/mcp", json=request("tools/list"))
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert "museum.search_knowledge" in names
    assert "museum.get_guide_context" in names
    assert "museum.search_map_nodes" in names
    assert "museum.plan_route" in names


@pytest.mark.anyio
async def test_mcp_call_returns_structured_database_result(
    mcp_client: httpx.AsyncClient,
) -> None:
    response = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {
                "name": "museum.get_place_info",
                "arguments": {"node_id": "LB-1F-REGION-A"},
            },
        ),
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["records"][0]["group_code"] == "A"
    assert "浦江国际学院" in result["content"][0]["text"]


@pytest.mark.anyio
async def test_mcp_invalid_arguments_and_unknown_tool_are_distinct(
    mcp_client: httpx.AsyncClient,
) -> None:
    missing_argument = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {"name": "museum.get_place_info", "arguments": {}},
        ),
    )
    assert missing_argument.json()["error"]["code"] == -32602

    unknown = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {"name": "museum.not_found", "arguments": {}},
        ),
    )
    assert unknown.json()["error"]["code"] == -32601


@pytest.mark.anyio
async def test_mcp_route_uses_sqlite_map_edges(mcp_client: httpx.AsyncClient) -> None:
    response = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-4F-ROOM-400A",
                    "to_location": "LB-4F-ROOM-429B",
                    "language": "zh",
                },
            },
        ),
    )
    result = response.json()["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["total_distance_m"] == 127.3


@pytest.mark.anyio
async def test_mcp_plans_user_marked_three_floor_route(
    mcp_client: httpx.AsyncClient,
) -> None:
    response = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-3F-EVENT-LEE-ART",
                    "to_location": "LB-3F-ROOM-300",
                },
            },
        ),
    )
    result = response.json()["result"]
    assert result["isError"] is False
    route = result["structuredContent"]
    assert route["from_id"] == "LB-3F-EVENT-LEE-ART"
    assert route["to_id"] == "LB-3F-ROOM-300"
    assert len(route["steps"]) >= 6
    assert all(step["to_id"] != "LB-3F-OPEN-05" for step in route["steps"])
    assert route["announcement"] == "300会议室就在您所在的三楼，位于电梯出口附近。"
    assert "OPEN" not in route["announcement"]


@pytest.mark.anyio
async def test_mcp_uses_guest_elevator_for_floor_one_to_college_introduction(
    mcp_client: httpx.AsyncClient,
) -> None:
    response = await mcp_client.post(
        "/mcp",
        json=request(
            "tools/call",
            {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-1F-OPEN-08",
                    "to_location": "LB-4F-REGION-F",
                },
            },
        ),
    )
    route = response.json()["result"]["structuredContent"]
    assert route["announcement"] == (
        "学院介绍区域在四楼。请乘坐访客电梯到四楼，出电梯后右转，"
        "再右转，学院介绍在左侧。"
    )
    route_nodes = {route["from_id"], route["to_id"]}
    route_nodes.update(step["to_id"] for step in route["steps"])
    assert "LB-1F-ELEVATOR-GUEST" in route_nodes
    assert "LB-4F-ELEVATOR-GUEST" in route_nodes
    assert "LB-1F-ELEVATOR-NORTHWEST-RESTRICTED" not in route_nodes
