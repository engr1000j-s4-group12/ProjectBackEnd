import json

import httpx
import pytest

from server.app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.anyio
async def test_localize_marker(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/localize",
        json={"marker_id": "LB-4F-ROOM-400A"},
    )
    assert response.status_code == 200
    assert response.json()["node_id"] == "LB-4F-ROOM-400A"


@pytest.mark.anyio
async def test_visual_localize_from_vlm_features(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/localize/visual",
        json={
            "objects": [
                {"label": "northwest stairs", "confidence": 0.95},
            ],
            "recognized_texts": ["northwest side stairs"],
            "scene_description": "northwest stairwell on the 4th floor",
            "floor_hint": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("matched", "ambiguous")
    candidate_ids = {c["node_id"] for c in body["candidates"]}
    assert "LB-4F-STAIRS-NORTHWEST" in candidate_ids


@pytest.mark.anyio
async def test_image_localize_rejects_non_image(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/localize/image",
        files={"image": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


@pytest.mark.anyio
async def test_route(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/route",
        json={
            "from_location": "LB-4F-ROOM-400A",
            "to_location": "LB-4F-ROOM-429B",
            "language": "zh",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_distance_m"] > 0
    assert len(body["steps"]) > 1
    assert body["from_id"] == "LB-4F-ROOM-400A"
    assert body["to_id"] == "LB-4F-ROOM-429B"
    assert isinstance(body.get("announcement", ""), str)


@pytest.mark.anyio
async def test_unknown_location_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/localize",
        json={"marker_id": "UNKNOWN"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_exhibit_context_is_grounded(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/exhibits/ROBOT-001/context",
        json={"question": "Where is it?", "language": "zh"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["facts"]
    assert "Answer only from the supplied" in body["system_instruction"]


@pytest.mark.anyio
async def test_resolve_place_accepts_firmware_name_parameter(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/v1/resolve", params={"name": "400A"})
    assert response.status_code == 200
    assert response.json() == {"node_id": "LB-4F-ROOM-400A"}


@pytest.mark.anyio
async def test_resolve_exhibit_for_mcp(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/exhibits/resolve",
        json={"recognized_texts": ["Robotics Demonstration Exhibit"], "floor_hint": 4},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matched"
    assert body["exhibit_id"] == "ROBOT-001"
    assert body["location_id"] == "LB-4F-ROOM-400"


@pytest.mark.anyio
async def test_resolve_exhibit_context_for_mcp(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/exhibits/resolve-context",
        json={
            "recognized_texts": ["Robotics Demonstration Exhibit"],
            "floor_hint": 4,
            "question": "Please briefly introduce it",
            "language": "zh",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matched"
    assert body["exhibit_id"] == "ROBOT-001"
    assert body["summary"]
    assert body["facts"]


@pytest.mark.anyio
async def test_guide_from_image_requires_image_type(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/guide/from-image",
        data={"payload": json.dumps({"destination": "ROBOT-001", "language": "zh"})},
        files={"image": ("bad.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
