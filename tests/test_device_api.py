from base64 import b64encode
from pathlib import Path

import httpx
import pytest

from server.app.knowledge import KnowledgeStore
from server.app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def device_client(tmp_path: Path):
    app = create_app(knowledge_store=KnowledgeStore(tmp_path / "device.sqlite3"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


HEADERS = {
    "Device-Id": "AA:BB:CC:DD:EE:FF",
    "Client-Id": "xiaozhi-test-client",
    "Firmware-Version": "test-1.0",
}


@pytest.mark.anyio
async def test_device_capabilities_and_persistent_session(device_client: httpx.AsyncClient) -> None:
    response = await device_client.get("/api/device/v1/capabilities", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["image"]["field"] == "image"

    response = await device_client.post(
        "/api/device/v1/session/start",
        headers=HEADERS,
        json={"preferred_language": "zh"},
    )
    assert response.json()["session"]["device_id"] == HEADERS["Device-Id"]
    saved = await device_client.get("/api/device/v1/session", headers=HEADERS)
    assert saved.json()["session"]["client_id"] == HEADERS["Client-Id"]


@pytest.mark.anyio
async def test_device_visual_localization_then_compact_route(device_client: httpx.AsyncClient) -> None:
    localized = await device_client.post(
        "/api/device/v1/localize/visual",
        headers=HEADERS,
        json={
            "recognized_texts": ["李政道科学与艺术大奖赛历年主题画展"],
            "floor_hint": 3,
        },
    )
    assert localized.status_code == 200
    assert localized.json()["current_node"] == "LB-3F-EVENT-LEE-ART"

    route = await device_client.post(
        "/api/device/v1/route",
        headers=HEADERS,
        json={"to_location": "LB-3F-ROOM-300", "language": "zh"},
    )
    body = route.json()
    assert route.status_code == 200
    assert body["announcement"] == "300会议室就在您所在的三楼，位于电梯出口附近。"
    assert "steps" not in body
    assert body["state"] == "navigating"

    debug = await device_client.post(
        "/api/device/v1/route?debug_steps=true",
        headers=HEADERS,
        json={"to_location": "LB-3F-ROOM-300"},
    )
    assert len(debug.json()["steps"]) == 6


@pytest.mark.anyio
async def test_device_route_requires_current_location(device_client: httpx.AsyncClient) -> None:
    await device_client.get(
        "/api/device/v1/capabilities",
        headers={**HEADERS, "Device-Id": "unlocalized-device"},
    )
    response = await device_client.post(
        "/api/device/v1/route",
        headers={**HEADERS, "Device-Id": "unlocalized-device"},
        json={"to_location": "LB-4F-REGION-F"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CURRENT_LOCATION_REQUIRED"


@pytest.mark.anyio
async def test_configured_device_token_is_enforced(
    device_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEVICE_API_TOKEN", "device-secret")
    denied = await device_client.get("/api/device/v1/capabilities", headers=HEADERS)
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "DEVICE_UNAUTHORIZED"

    allowed = await device_client.get(
        "/api/device/v1/capabilities",
        headers={**HEADERS, "Authorization": "Bearer device-secret"},
    )
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_configured_admin_basic_auth_is_enforced(
    device_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "guide-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    denied = await device_client.get("/api/admin/bootstrap")
    assert denied.status_code == 401
    encoded = b64encode(b"guide-admin:admin-secret").decode()
    allowed = await device_client.get(
        "/api/admin/bootstrap", headers={"Authorization": f"Basic {encoded}"}
    )
    assert allowed.status_code == 200
