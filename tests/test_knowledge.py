from pathlib import Path

import httpx
import pytest

from server.app.knowledge import KnowledgeStore
from server.app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(tmp_path / "guide.sqlite3")


@pytest.fixture
async def knowledge_client(store: KnowledgeStore):
    app = create_app(knowledge_store=store)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def test_initial_regions_are_seeded(store: KnowledgeStore) -> None:
    entries = store.list_entries(include_archived=True)
    assert len(entries) == 8
    assert {entry["group_code"] for entry in entries} >= {"A", "B", "C", "D", "E", "F"}
    assert next(entry for entry in entries if entry["group_code"] == "E")["title_zh"] == "钢琴"
    assert any("李政道" in entry["title_zh"] for entry in entries)


def test_four_floor_maps_are_queryable_in_sqlite(store: KnowledgeStore) -> None:
    summary = store.map_summary()
    assert [item["floor"] for item in summary["floors"]] == [1, 2, 3, 4]
    assert all(item["nodes"] > 0 for item in summary["floors"])
    assert summary["floors"][3]["edges"] >= 129
    assert store.get_map_node("LB-3F-ROOM-300")["floor"] == 3
    assert store.get_map_node("LB-3F-EVENT-LEE-ART")["visual_landmarks"]

    incorrect = store.get_map_node("LB-1F-RESTROOM-NORTHWEST")
    assert incorrect["status"] == "archived"
    restricted = store.get_map_node("LB-1F-ELEVATOR-NORTHWEST-RESTRICTED")
    assert restricted["kind"] == "restricted"
    assert restricted["routable"] is False
    assert restricted["navigation_notes"]["guest_access"] is False
    guest_elevator = store.get_map_node("LB-4F-ELEVATOR-GUEST")
    assert guest_elevator["navigation_notes"]["exit_facing"] == "north"


@pytest.mark.anyio
async def test_admin_bootstrap_exposes_four_maps_and_regions(
    knowledge_client: httpx.AsyncClient,
) -> None:
    response = await knowledge_client.get("/api/admin/bootstrap")
    assert response.status_code == 200
    body = response.json()
    assert [item["floor"] for item in body["floorplans"]] == [1, 2, 3, 4]
    assert len(body["entries"]) == 8
    assert sum(item["nodes"] for item in body["map_summary"]["floors"]) > 300
    assert any(edge["calibration_status"] == "user_marked" for edge in body["map_edges"])
    assert any(node["kind"] == "restricted" for node in body["map_nodes"])


def test_english_admin_console_is_available(store: KnowledgeStore) -> None:
    app = create_app(knowledge_store=store)
    assert "/admin/en" in {
        route.path for route in app.routes if hasattr(route, "path")
    }
    page = (
        Path(__file__).resolve().parents[1]
        / "server/app/static/admin/index-en.html"
    ).read_text(encoding="utf-8")
    assert '<html lang="en">' in page
    assert "Guide Database Console" in page
    assert "Four Floor Maps and Exhibition Areas" in page
    assert 'href="/admin"' in page


@pytest.mark.anyio
async def test_create_search_archive_and_restore_content(
    knowledge_client: httpx.AsyncClient,
) -> None:
    response = await knowledge_client.post(
        "/api/admin/entries",
        json={
            "node_id": "LB-1F-REGION-TEST",
            "group_code": "T",
            "floor": 1,
            "geometry": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]],
            "kind": "event",
            "title_zh": "测试展览",
            "content_zh": "用于数据库查询测试",
            "tags": ["测试标签"],
        },
    )
    assert response.status_code == 200
    record_id = response.json()["id"]

    # The running SQLite navigation repository sees console writes immediately.
    route = await knowledge_client.post(
        "/api/v1/route",
        json={
            "from_location": "LB-1F-REGION-TEST",
            "to_location": "LB-1F-REGION-TEST",
            "language": "zh",
        },
    )
    assert route.status_code == 200
    assert route.json()["total_distance_m"] == 0

    response = await knowledge_client.get(
        "/api/v1/events", params={"q": "测试标签"}
    )
    assert response.json()["count"] == 1

    response = await knowledge_client.post(f"/api/admin/entries/{record_id}/archive")
    assert response.json()["status"] == "archived"
    map_node = await knowledge_client.get("/api/v1/map/nodes/LB-1F-REGION-TEST")
    assert map_node.json()["status"] == "archived"
    assert (await knowledge_client.get("/api/v1/events", params={"q": "测试展览"})).json()["count"] == 0
    archived = await knowledge_client.get(
        "/api/v1/events", params={"q": "测试展览", "include_archived": True}
    )
    assert archived.json()["events"][0]["status"] == "archived"

    response = await knowledge_client.post(f"/api/admin/entries/{record_id}/restore")
    assert response.json()["status"] == "active"
    map_node = await knowledge_client.get("/api/v1/map/nodes/LB-1F-REGION-TEST")
    assert map_node.json()["status"] == "active"


@pytest.mark.anyio
async def test_floor_map_query_api(knowledge_client: httpx.AsyncClient) -> None:
    response = await knowledge_client.get("/api/v1/maps/3")
    assert response.status_code == 200
    body = response.json()
    assert body["floor_map"]["image_width"] == 1536
    node_ids = {item["node_id"] for item in body["nodes"]}
    assert "LB-3F-ROOM-300" in node_ids
    assert "LB-3F-EVENT-LEE-ART" in node_ids

    localized = await knowledge_client.post(
        "/api/v1/localize/visual",
        json={
            "recognized_texts": ["李政道科学与艺术大奖赛历年主题画展"],
            "floor_hint": 3,
        },
    )
    assert localized.status_code == 200
    assert localized.json()["node_id"] == "LB-3F-EVENT-LEE-ART"


@pytest.mark.anyio
async def test_visit_context_only_uses_active_visit(
    knowledge_client: httpx.AsyncClient,
) -> None:
    response = await knowledge_client.post(
        "/api/admin/visits",
        json={
            "delegation_name": "美国 A 大学代表团",
            "institution": "A University",
            "country": "美国",
            "preferred_language": "en",
            "purpose": "讨论学院合作",
            "itinerary": [{"order": 1, "text": "前往300会议室"}],
            "script_en": "Welcome to Global College.",
        },
    )
    assert response.status_code == 200
    visit_id = response.json()["id"]

    context = await knowledge_client.get(
        "/api/v1/guide/context",
        params={"visit_id": visit_id, "current_node": "LB-1F-REGION-A"},
    )
    assert context.status_code == 200
    body = context.json()
    assert body["visit"]["preferred_language"] == "en"
    assert body["location_records"][0]["node_id"] == "LB-1F-REGION-A"
    assert body["persona"]["name"] == "Guide"

    await knowledge_client.post(f"/api/admin/visits/{visit_id}/archive")
    context = await knowledge_client.get(
        "/api/v1/guide/context", params={"visit_id": visit_id}
    )
    assert context.status_code == 404


@pytest.mark.anyio
async def test_upload_is_stored_without_runtime_vlm(
    knowledge_client: httpx.AsyncClient,
) -> None:
    bootstrap = (await knowledge_client.get("/api/admin/bootstrap")).json()
    record_id = bootstrap["entries"][0]["id"]
    response = await knowledge_client.post(
        f"/api/admin/entries/{record_id}/media",
        params={"run_vlm": False},
        files={"file": ("note.txt", b"curated note", "text/plain")},
    )
    assert response.status_code == 200
    media = response.json()["media"]
    assert media["vlm_status"] == "skipped"
    assert media["sha256"]


@pytest.mark.anyio
async def test_mcp_contracts_are_discoverable(
    knowledge_client: httpx.AsyncClient,
) -> None:
    response = await knowledge_client.get("/api/v1/mcp/tools")
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "museum.search_knowledge" in names
    assert "museum.get_guide_context" in names
