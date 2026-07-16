from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

from .errors import LocationNotFoundError, RouteNotFoundError, VlmNotConfiguredError, VlmResponseError
from .guide_persona import GUIDE_PERSONA
from .knowledge import KnowledgeStore
from .navigation import Navigator
from .repository import SqliteGuideRepository
from .schemas import (
    DeviceResolvePlaceRequest,
    DeviceRouteRequest,
    DeviceSessionStartRequest,
    VisualLocalizeRequest,
)
from .visual_localization import VisualLocalizer
from .vlm import VlmClient


MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _request_id(value: str | None) -> str:
    return value or uuid4().hex


def _identity(device_id: str | None, client_id: str | None) -> tuple[str, str]:
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DEVICE_ID_REQUIRED",
                "message": "Device-Id header is required.",
                "retryable": False,
                "speak": "设备信息不完整，请联系工作人员。",
            },
        )
    return device_id.strip(), (client_id or "").strip()


def _compact_record(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": entry["id"],
        "node_id": entry["node_id"],
        "floor": entry["floor"],
        "kind": entry["kind"],
        "title_zh": entry["title_zh"],
        "title_en": entry["title_en"],
        "content_zh": entry["content_zh"],
        "content_en": entry["content_en"],
        "updated_at": entry["updated_at"],
    }


def build_device_router(
    store: KnowledgeStore,
    repository: SqliteGuideRepository,
    navigator: Navigator,
    localizer: VisualLocalizer,
    vlm_client: VlmClient,
) -> APIRouter:
    router = APIRouter(prefix="/api/device/v1", tags=["xiaozhi-device"])

    def touch(
        device_id: str | None,
        client_id: str | None,
        firmware_version: str | None,
        **updates: Any,
    ) -> dict[str, Any]:
        resolved_device, resolved_client = _identity(device_id, client_id)
        return store.update_device_session(
            resolved_device,
            client_id=resolved_client,
            firmware_version=(firmware_version or "").strip(),
            **updates,
        )

    @router.get("/capabilities")
    async def capabilities(
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
    ) -> dict[str, Any]:
        session = touch(device_id, client_id, firmware_version)
        return {
            "ok": True,
            "service": "longbin-guide-device-api",
            "version": "1.0.0",
            "device_id": session["device_id"],
            "authentication_required": bool(os.getenv("DEVICE_API_TOKEN")),
            "image": {"field": "image", "types": sorted(IMAGE_TYPES), "max_bytes": MAX_IMAGE_BYTES},
            "features": {
                "image_localization": True,
                "visual_localization": True,
                "compact_route_announcement": True,
                "navigation_session": True,
                "knowledge_search": True,
            },
        }

    @router.post("/session/start")
    async def start_session(
        request: DeviceSessionStartRequest,
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
    ) -> dict[str, Any]:
        session = touch(
            device_id,
            client_id,
            firmware_version,
            visit_id=request.visit_id,
            current_node=request.current_node,
            destination_node=request.destination_node,
            preferred_language=request.preferred_language,
            state="ready" if request.current_node else "idle",
            last_error="",
        )
        return {"ok": True, "session": session}

    @router.get("/session")
    async def get_session(
        device_id: str | None = Header(default=None, alias="Device-Id"),
    ) -> dict[str, Any]:
        resolved_device, _ = _identity(device_id, None)
        session = store.get_device_session(resolved_device)
        return {"ok": True, "session": session}

    @router.post("/session/cancel")
    async def cancel_session(
        device_id: str | None = Header(default=None, alias="Device-Id"),
    ) -> dict[str, Any]:
        resolved_device, _ = _identity(device_id, None)
        session = store.update_device_session(
            resolved_device,
            state="cancelled",
            last_announcement="导航已取消。",
            last_error="",
        )
        return {"ok": True, "session": session, "announcement": "导航已取消。"}

    @router.get("/guide/context")
    async def guide_context(
        visit_id: int | None = None,
        current_node: str | None = None,
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
    ) -> dict[str, Any]:
        session = touch(device_id, client_id, firmware_version)
        selected_visit = visit_id if visit_id is not None else session.get("visit_id")
        visits = store.list_visits(include_archived=False)
        visit = next((item for item in visits if item["id"] == selected_visit), None)
        if visit is None and len(visits) == 1:
            visit = visits[0]
        node = current_node or session.get("current_node")
        records = store.list_entries(include_archived=False)
        if node:
            exact = [item for item in records if item["node_id"] == node]
            records = exact or [item for item in records if item["floor"] == int(node[3])]
        return {
            "ok": True,
            "persona": GUIDE_PERSONA,
            "visit": visit,
            "current_node": node,
            "location_records": [_compact_record(item) for item in records[:8]],
        }

    @router.post("/resolve-place")
    async def resolve_place(
        request: DeviceResolvePlaceRequest,
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
    ) -> dict[str, Any]:
        touch(device_id, client_id, firmware_version)
        try:
            node_id = repository.resolve_location(request.name)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail={"code": "DESTINATION_NOT_FOUND", "message": str(exc), "retryable": False, "speak": "没有找到这个目的地，请换一种说法。"}) from exc
        node = repository.data.nodes[node_id]
        return {"ok": True, "node": {"node_id": node_id, "name_zh": node["name_zh"], "name_en": node["name_en"], "floor": node["floor"], "kind": node["kind"]}}

    def localized_response(
        result: Any,
        device_id: str,
        request_id: str,
    ) -> dict[str, Any]:
        state = "ready" if result.status == "matched" else "needs_confirmation"
        speak = ""
        if result.status == "ambiguous":
            speak = "我暂时无法确认当前位置，请将设备朝向前方后再拍一次。"
        elif result.status == "not_found":
            speak = "没有识别到当前位置，请靠近门牌或展板后再试一次。"
        store.update_device_session(
            device_id,
            current_node=result.node_id,
            state=state,
            confidence=result.confidence,
            last_error="" if result.status == "matched" else result.status,
        )
        return {
            "ok": result.status == "matched",
            "request_id": request_id,
            "status": result.status,
            "current_node": result.node_id,
            "confidence": result.confidence,
            "needs_confirmation": result.needs_confirmation,
            "speak": speak,
            "candidates": [
                {"node_id": item.node_id, "name_zh": item.name_zh, "floor": item.floor, "score": item.score}
                for item in result.candidates
            ],
        }

    @router.post("/localize/visual")
    async def localize_visual(
        evidence: VisualLocalizeRequest,
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
        request_id: str | None = Header(default=None, alias="X-Request-Id"),
    ) -> dict[str, Any]:
        session = touch(device_id, client_id, firmware_version, state="locating")
        result = localizer.locate(evidence)
        return localized_response(result, session["device_id"], _request_id(request_id))

    @router.post("/localize/image")
    async def localize_image(
        image: UploadFile = File(...),
        floor_hint: int | None = Form(default=None),
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
        request_id: str | None = Header(default=None, alias="X-Request-Id"),
    ) -> dict[str, Any]:
        session = touch(device_id, client_id, firmware_version, state="locating")
        if image.content_type not in IMAGE_TYPES:
            raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_IMAGE", "message": "JPEG, PNG or WebP required.", "retryable": False, "speak": "设备照片格式不受支持。"})
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail={"code": "EMPTY_IMAGE", "message": "Image is empty.", "retryable": True, "speak": "拍照失败，请再试一次。"})
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail={"code": "IMAGE_TOO_LARGE", "message": "Image exceeds 5 MiB.", "retryable": True, "speak": "照片过大，请降低清晰度后重试。"})
        try:
            evidence = await vlm_client.analyze(content, image.content_type or "image/jpeg")
        except VlmNotConfiguredError as exc:
            store.update_device_session(session["device_id"], state="service_unavailable", last_error=str(exc))
            raise HTTPException(status_code=503, detail={"code": "VLM_NOT_CONFIGURED", "message": str(exc), "retryable": False, "speak": "定位服务暂时不可用，请联系工作人员。"}) from exc
        except VlmResponseError as exc:
            store.update_device_session(session["device_id"], state="service_unavailable", last_error=str(exc))
            raise HTTPException(status_code=502, detail={"code": "VLM_FAILED", "message": str(exc), "retryable": True, "speak": "照片识别失败，请再试一次。"}) from exc
        if floor_hint is not None:
            evidence.floor_hint = floor_hint
        return localized_response(localizer.locate(evidence), session["device_id"], _request_id(request_id))

    @router.post("/route")
    async def route(
        request: DeviceRouteRequest,
        debug_steps: bool = Query(default=False),
        device_id: str | None = Header(default=None, alias="Device-Id"),
        client_id: str | None = Header(default=None, alias="Client-Id"),
        firmware_version: str | None = Header(default=None, alias="Firmware-Version"),
        request_id: str | None = Header(default=None, alias="X-Request-Id"),
    ) -> dict[str, Any]:
        session = touch(device_id, client_id, firmware_version)
        start = request.from_location or session.get("current_node")
        if not start:
            raise HTTPException(status_code=409, detail={"code": "CURRENT_LOCATION_REQUIRED", "message": "Localize before planning a route.", "retryable": True, "speak": "我需要先确认当前位置，请稍等。"})
        try:
            result = navigator.plan(start, request.to_location, request.language, request.accessible_only)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail={"code": "DESTINATION_NOT_FOUND", "message": str(exc), "retryable": False, "speak": "没有找到这个目的地，请换一种说法。"}) from exc
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=422, detail={"code": "ROUTE_NOT_FOUND", "message": str(exc), "retryable": False, "speak": "这条路线尚未录入，请联系工作人员带领。"}) from exc
        state = "arrived" if not result.steps else "navigating"
        store.update_device_session(
            session["device_id"],
            current_node=result.from_id,
            destination_node=result.to_id,
            state=state,
            preferred_language=request.language,
            last_announcement=result.announcement,
            last_error="",
        )
        response: dict[str, Any] = {
            "ok": True,
            "request_id": _request_id(request_id),
            "state": state,
            "current_node": result.from_id,
            "destination_node": result.to_id,
            "announcement": result.announcement,
            "total_distance_m": round(result.total_distance_m, 1),
            "needs_relocalization": len(result.steps) > 1,
        }
        if debug_steps:
            response["steps"] = [step.__dict__ for step in result.steps]
        return response

    @router.get("/knowledge/search")
    async def knowledge_search(
        q: str = Query(min_length=1),
        floor: int | None = Query(default=None, ge=1, le=4),
        limit: int = Query(default=5, ge=1, le=10),
        device_id: str | None = Header(default=None, alias="Device-Id"),
    ) -> dict[str, Any]:
        _identity(device_id, None)
        records = store.list_entries(floor=floor, query=q, include_archived=False)
        return {"ok": True, "query": q, "records": [_compact_record(item) for item in records[:limit]]}

    return router
