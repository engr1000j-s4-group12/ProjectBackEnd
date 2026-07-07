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
        json={"marker_id": "LB-1F-ENTRANCE"},
    )
    assert response.status_code == 200
    assert response.json()["node_id"] == "LB-1F-ENTRANCE"


@pytest.mark.anyio
async def test_visual_localize_from_vlm_features(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/localize/visual",
        json={
            "objects": [
                {"label": "机器人展品", "confidence": 0.98},
                {"label": "机器人介绍展板", "confidence": 0.90},
            ],
            "recognized_texts": ["ROBOT-001"],
            "scene_description": "二楼走廊内的机器人展示区",
            "floor_hint": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matched"
    assert body["node_id"] == "EXHIBIT-ROBOT"


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
            "from_location": "主入口",
            "to_location": "机器人",
            "language": "zh",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_distance_m"] == 51
    assert len(body["steps"]) == 5


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
        json={"question": "它在哪里？", "language": "zh"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["facts"]
    assert "只能依据" in body["system_instruction"]
