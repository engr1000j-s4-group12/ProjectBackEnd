from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from .errors import (
    DataValidationError,
    LocationNotFoundError,
    RouteNotFoundError,
    VlmNotConfiguredError,
    VlmResponseError,
)
from .navigation import Navigator
from .repository import GuideRepository
from .schemas import (
    ExhibitContextResponse,
    ExhibitQuestionRequest,
    HealthResponse,
    LocalizeRequest,
    LocationResponse,
    RouteRequest,
    RouteResponse,
    VisualLocalizeRequest,
    VisualLocalizationResponse,
)
from .visual_localization import VisualLocalizer
from .vlm import VlmClient


MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def create_app(repository: GuideRepository | None = None) -> FastAPI:
    repo = repository or GuideRepository()
    navigator = Navigator(repo)
    visual_localizer = VisualLocalizer(repo)
    vlm_client = VlmClient()
    app = FastAPI(
        title="龙宾楼智能导览后端",
        description="为小智 ESP32 终端提供定位、路线规划和展品知识查询。",
        version="0.2.0",
    )

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="longbin-guide-server",
            version=app.version,
        )

    @app.get("/api/v1/places", tags=["places"])
    async def list_places() -> dict[str, list[dict]]:
        return {"places": repo.list_locations()}

    @app.post(
        "/api/v1/localize",
        response_model=LocationResponse,
        tags=["localization"],
    )
    async def localize(request: LocalizeRequest) -> LocationResponse:
        try:
            node = repo.get_location(request.marker_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return LocationResponse(
            node_id=node["id"],
            name_zh=node["name_zh"],
            name_en=node["name_en"],
            floor=node["floor"],
            kind=node["kind"],
        )

    @app.post(
        "/api/v1/localize/visual",
        response_model=VisualLocalizationResponse,
        tags=["localization"],
    )
    async def localize_visual(
        request: VisualLocalizeRequest,
    ) -> VisualLocalizationResponse:
        return visual_localizer.locate(request)

    @app.post(
        "/api/v1/localize/image",
        response_model=VisualLocalizationResponse,
        tags=["localization"],
    )
    async def localize_image(
        image: UploadFile = File(description="JPEG、PNG 或 WebP 室内照片"),
        floor_hint: int | None = Form(default=None),
    ) -> VisualLocalizationResponse:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail="仅支持 JPEG、PNG 或 WebP 图片",
            )
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="图片不得超过 5 MiB")
        if not content:
            raise HTTPException(status_code=400, detail="图片内容为空")
        try:
            evidence = await vlm_client.analyze(content, image.content_type)
        except VlmNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except VlmResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if floor_hint is not None:
            evidence.floor_hint = floor_hint
        return visual_localizer.locate(evidence)

    @app.post("/api/v1/route", response_model=RouteResponse, tags=["navigation"])
    async def route(request: RouteRequest) -> RouteResponse:
        try:
            result = navigator.plan(
                request.from_location,
                request.to_location,
                request.language,
                request.accessible_only,
            )
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return RouteResponse(
            from_id=result.from_id,
            to_id=result.to_id,
            total_distance_m=result.total_distance_m,
            steps=[step.__dict__ for step in result.steps],
        )

    @app.get("/api/v1/exhibits", tags=["exhibits"])
    async def list_exhibits() -> dict[str, list[dict]]:
        return {"exhibits": repo.list_exhibits()}

    @app.get("/api/v1/exhibits/{exhibit_id}", tags=["exhibits"])
    async def get_exhibit(exhibit_id: str) -> dict:
        try:
            return repo.get_exhibit(exhibit_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/v1/exhibits/{exhibit_id}/context",
        response_model=ExhibitContextResponse,
        tags=["exhibits"],
    )
    async def exhibit_context(
        exhibit_id: str, request: ExhibitQuestionRequest
    ) -> ExhibitContextResponse:
        try:
            exhibit = repo.get_exhibit(exhibit_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        suffix = "en" if request.language == "en" else "zh"
        return ExhibitContextResponse(
            exhibit_id=exhibit["id"],
            location_id=exhibit["location_id"],
            name=exhibit[f"name_{suffix}"],
            facts=exhibit[f"facts_{suffix}"],
            question=request.question,
            system_instruction=(
                "Answer only from the supplied facts. If the facts are insufficient, "
                "say that the curated exhibit data does not contain the answer."
                if request.language == "en"
                else "只能依据提供的展品事实回答。如果资料不足，明确说明展品资料中没有该信息。"
            ),
        )

    @app.get("/api/v1/resolve", tags=["places"])
    async def resolve_place(q: str = Query(min_length=1)) -> dict[str, str]:
        try:
            return {"node_id": repo.resolve_location(q)}
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


try:
    app = create_app()
except DataValidationError as exc:
    raise RuntimeError(f"导览数据加载失败：{exc}") from exc
