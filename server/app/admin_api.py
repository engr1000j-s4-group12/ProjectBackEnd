from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from .errors import VlmNotConfiguredError, VlmResponseError
from .guide_persona import GUIDE_PERSONA, MCP_TOOL_CONTRACTS
from .knowledge import KnowledgeStore
from .schemas import KnowledgeEntryCreate, KnowledgeEntryUpdate, VisitCreate
from .vlm import VlmClient


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_UPLOAD_TYPES = IMAGE_TYPES | {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _floor_from_node(node_id: str) -> int | None:
    matched = re.search(r"LB-([1-4])F-", node_id.upper())
    return int(matched.group(1)) if matched else None


def build_data_router(
    store: KnowledgeStore,
    vlm_client: VlmClient,
    upload_dir: Path,
) -> APIRouter:
    router = APIRouter()
    upload_dir.mkdir(parents=True, exist_ok=True)

    async def process_media(
        entry: dict[str, Any],
        media: dict[str, Any],
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        context = {
            "record_id": entry["id"],
            "node_id": entry["node_id"],
            "floor": entry["floor"],
            "kind": entry["kind"],
            "manager_title": entry["title_zh"],
            "manager_description": entry["content_zh"],
        }
        try:
            extracted = await vlm_client.extract_record(content, content_type, context)
            media = store.update_media_vlm(media["id"], "completed", extracted)
            latest_entry = store.get_entry(entry["id"])
            existing_extracted = latest_entry.get("extracted") or {}
            extracted_items = existing_extracted.get("media", [])
            if not isinstance(extracted_items, list):
                extracted_items = []
            extracted_items = [
                item for item in extracted_items if item.get("media_id") != media["id"]
            ]
            combined_extracted = {
                "media": [*extracted_items, {"media_id": media["id"], **extracted}]
            }
            updates: dict[str, Any] = {
                "extracted": combined_extracted,
                "tags": sorted(
                    set(latest_entry["tags"] + extracted.get("visual_tags", []))
                ),
            }
            if not latest_entry["title_en"]:
                updates["title_en"] = extracted.get("suggested_title_en", "")
            if not latest_entry["content_en"]:
                updates["content_en"] = extracted.get("description_en", "")
            if not latest_entry["content_zh"]:
                updates["content_zh"] = extracted.get("description_zh", "")
            store.update_entry(entry["id"], updates)
        except VlmNotConfiguredError as exc:
            media = store.update_media_vlm(
                media["id"], "not_configured", {"error": str(exc)}
            )
        except VlmResponseError as exc:
            media = store.update_media_vlm(
                media["id"], "failed", {"error": str(exc)}
            )
        return media

    @router.get("/api/admin/bootstrap", tags=["admin"])
    async def admin_bootstrap() -> dict[str, Any]:
        entries = store.list_entries(include_archived=True)
        for entry in entries:
            entry["media"] = store.list_media(entry["id"])
        return {
            "floorplans": [
                {
                    **item,
                    "label": f"{item['floor']}楼",
                    "url": item["image_url"],
                }
                for item in store.list_floor_maps()
            ],
            "entries": entries,
            "visits": store.list_visits(include_archived=True),
            "map_summary": store.map_summary(),
            "map_nodes": store.list_map_nodes(include_archived=True),
            "map_edges": store.list_map_edges(include_archived=True),
            "kinds": {
                "permanent": "长期信息",
                "event": "活动/临时展览",
                "exhibit": "常设展品",
                "facility": "设施",
            },
        }

    @router.post("/api/admin/entries", tags=["admin"])
    async def create_entry(request: KnowledgeEntryCreate) -> dict[str, Any]:
        try:
            return store.create_entry(request.model_dump())
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="节点 ID 已存在") from exc

    @router.patch("/api/admin/entries/{record_id}", tags=["admin"])
    async def update_entry(
        record_id: int, request: KnowledgeEntryUpdate
    ) -> dict[str, Any]:
        try:
            return store.update_entry(record_id, request.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="记录不存在") from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="节点 ID 已存在") from exc

    @router.post("/api/admin/entries/{record_id}/archive", tags=["admin"])
    async def archive_entry(record_id: int) -> dict[str, Any]:
        try:
            return store.set_archived(record_id, True)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="记录不存在") from exc

    @router.post("/api/admin/entries/{record_id}/restore", tags=["admin"])
    async def restore_entry(record_id: int) -> dict[str, Any]:
        try:
            return store.set_archived(record_id, False)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="记录不存在") from exc

    @router.post("/api/admin/entries/{record_id}/media", tags=["admin"])
    async def upload_media(
        record_id: int,
        file: UploadFile = File(...),
        run_vlm: bool = Query(default=True),
    ) -> dict[str, Any]:
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise HTTPException(status_code=415, detail="暂不支持该文件格式")
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="单个文件不得超过 20 MiB")
        try:
            entry = store.get_entry(record_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="记录不存在") from exc

        digest = hashlib.sha256(content).hexdigest()
        suffix = Path(file.filename or "upload").suffix.lower()[:12]
        stored_name = f"{digest}{suffix}"
        path = upload_dir / stored_name
        if not path.exists():
            path.write_bytes(content)
        try:
            media = store.add_media(
                record_id,
                {
                    "original_name": file.filename or stored_name,
                    "stored_name": stored_name,
                    "content_type": content_type,
                    "sha256": digest,
                    "size_bytes": len(content),
                    "vlm_status": "pending" if run_vlm and content_type in IMAGE_TYPES else "skipped",
                },
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="该记录已经包含相同文件") from exc

        if run_vlm and content_type in IMAGE_TYPES:
            media = await process_media(entry, media, content, content_type)
        return {"media": media, "entry": store.get_entry(record_id)}

    @router.post("/api/admin/media/{media_id}/retry-vlm", tags=["admin"])
    async def retry_media_vlm(media_id: int) -> dict[str, Any]:
        try:
            media = store.get_media(media_id)
            entry = store.get_entry(media["record_id"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="媒体记录不存在") from exc
        if media["content_type"] not in IMAGE_TYPES:
            raise HTTPException(status_code=422, detail="该文件不是可供 VLM 处理的图片")
        path = upload_dir / media["stored_name"]
        if not path.is_file():
            raise HTTPException(status_code=404, detail="媒体文件不存在")
        processed = await process_media(
            entry, media, path.read_bytes(), media["content_type"]
        )
        return {"media": processed, "entry": store.get_entry(entry["id"])}

    @router.get("/api/admin/entries/{record_id}/media", tags=["admin"])
    async def list_media(record_id: int) -> dict[str, Any]:
        return {"media": store.list_media(record_id)}

    @router.get("/api/admin/history", tags=["admin"])
    async def history(
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> dict[str, Any]:
        return {"history": store.history(entity_type, entity_id)}

    @router.post("/api/admin/visits", tags=["admin"])
    async def create_visit(request: VisitCreate) -> dict[str, Any]:
        return store.create_visit(request.model_dump())

    @router.get("/api/admin/visits", tags=["admin"])
    async def list_visits(include_archived: bool = True) -> dict[str, Any]:
        return {"visits": store.list_visits(include_archived)}

    @router.post("/api/admin/visits/{visit_id}/archive", tags=["admin"])
    async def archive_visit(visit_id: int) -> dict[str, Any]:
        try:
            return store.set_visit_archived(visit_id, True)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="来访任务不存在") from exc

    @router.get("/api/v1/knowledge/search", tags=["knowledge", "mcp"])
    async def search_knowledge(
        q: str | None = None,
        node_id: str | None = None,
        kind: str | None = None,
        floor: int | None = Query(default=None, ge=1, le=4),
        include_archived: bool = False,
    ) -> dict[str, Any]:
        entries = store.list_entries(
            floor=floor,
            kind=kind,
            include_archived=include_archived,
            query=q or node_id,
        )
        if node_id:
            exact = [entry for entry in entries if entry["node_id"] == node_id]
            entries = exact or entries
        return {"query": q or node_id, "records": entries, "count": len(entries)}

    @router.get("/api/v1/maps", tags=["maps", "mcp"])
    async def map_database_summary() -> dict[str, Any]:
        return store.map_summary()

    @router.get("/api/v1/maps/{floor}", tags=["maps", "mcp"])
    async def get_floor_map_data(
        floor: int,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        if floor not in {1, 2, 3, 4}:
            raise HTTPException(status_code=404, detail="楼层不存在")
        return {
            "floor_map": store.get_floor_map(floor),
            "nodes": store.list_map_nodes(
                floor=floor, include_archived=include_archived
            ),
            "edges": store.list_map_edges(
                floor=floor, include_archived=include_archived
            ),
        }

    @router.get("/api/v1/map/nodes", tags=["maps", "mcp"])
    async def search_map_nodes(
        q: str | None = None,
        floor: int | None = Query(default=None, ge=1, le=4),
        kind: str | None = None,
        routable: bool | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        nodes = store.list_map_nodes(
            floor=floor,
            kind=kind,
            query=q,
            routable=routable,
            include_archived=include_archived,
        )
        return {"nodes": nodes, "count": len(nodes)}

    @router.get("/api/v1/map/nodes/{node_id}", tags=["maps", "mcp"])
    async def get_map_node(node_id: str) -> dict[str, Any]:
        try:
            return store.get_map_node(node_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="地图节点不存在") from exc

    @router.get("/api/v1/events/nearby", tags=["events", "mcp"])
    async def nearby_events(node_id: str) -> dict[str, Any]:
        floor = _floor_from_node(node_id)
        entries = store.list_entries(floor=floor, kind="event")
        entries.sort(key=lambda item: item["node_id"] != node_id)
        return {"node_id": node_id, "floor": floor, "events": entries}

    @router.get("/api/v1/events", tags=["events", "mcp"])
    async def search_events(
        q: str | None = None,
        floor: int | None = Query(default=None, ge=1, le=4),
        include_archived: bool = False,
    ) -> dict[str, Any]:
        entries = store.list_entries(
            floor=floor,
            kind="event",
            include_archived=include_archived,
            query=q,
        )
        return {"events": entries, "count": len(entries)}

    @router.get("/api/v1/events/{record_id}", tags=["events", "mcp"])
    async def get_event(record_id: int) -> dict[str, Any]:
        try:
            entry = store.get_entry(record_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="活动不存在") from exc
        if entry["kind"] != "event":
            raise HTTPException(status_code=404, detail="活动不存在")
        entry["media"] = store.list_media(record_id)
        return entry

    @router.get("/api/v1/guide/context", tags=["guide", "mcp"])
    async def guide_context(
        visit_id: int | None = None,
        current_node: str | None = None,
    ) -> dict[str, Any]:
        visits = store.list_visits(include_archived=False)
        visit = next((item for item in visits if item["id"] == visit_id), None)
        if visit_id is not None and visit is None:
            raise HTTPException(status_code=404, detail="当前来访任务不存在或已归档")
        if visit is None and len(visits) == 1:
            visit = visits[0]
        floor = _floor_from_node(current_node or "")
        location_records = (
            store.list_entries(floor=floor, include_archived=False) if floor else []
        )
        if current_node:
            exact = [entry for entry in location_records if entry["node_id"] == current_node]
            location_records = exact or location_records
        return {
            "persona": GUIDE_PERSONA,
            "visit": visit,
            "current_node": current_node,
            "location_records": location_records,
            "instruction": "只使用本响应中的活跃来访任务和知识记录进行讲解。",
        }

    @router.get("/api/v1/persona", tags=["guide"])
    async def persona() -> dict[str, Any]:
        return GUIDE_PERSONA

    @router.get("/api/v1/mcp/tools", tags=["mcp"])
    async def mcp_tools() -> dict[str, Any]:
        return {"tools": MCP_TOOL_CONTRACTS}

    return router
