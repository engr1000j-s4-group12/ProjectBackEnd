from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .admin_api import build_data_router
from .device_api import build_device_router
from .errors import (
    DataValidationError,
    LocationNotFoundError,
    RouteNotFoundError,
    VlmNotConfiguredError,
    VlmResponseError,
)
from .navigation import Navigator
from .knowledge import KnowledgeStore
from .mcp_api import build_mcp_router
from .repository import GuideRepository, SqliteGuideRepository
from .security import AccessControlMiddleware
from .schemas import (
    ExhibitContextResponse,
    ExhibitQuestionRequest,
    ExhibitResolveContextRequest,
    ExhibitResolveContextResponse,
    ExhibitResolveResponse,
    GuideFlowRequest,
    GuideFlowResponse,
    HealthResponse,
    LocalizeRequest,
    LocationResponse,
    RouteRequest,
    RouteResponse,
    VisualCandidateResponse,
    VisualLocalizeRequest,
    VisualLocalizationResponse,
)
from .visual_localization import VisualLocalizer
from .vlm import VlmClient
from .vlm_navigation import VlmMapNavigator


MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
FLOW_LAB_DIR = Path(__file__).resolve().parent / "static" / "flow_lab"
ADMIN_DIR = Path(__file__).resolve().parent / "static" / "admin"
DEFAULT_UPLOAD_DIR = ADMIN_DIR / "uploads"


def create_app(
    repository: GuideRepository | None = None,
    knowledge_store: KnowledgeStore | None = None,
) -> FastAPI:
    store = knowledge_store or KnowledgeStore()
    repo = repository or SqliteGuideRepository(store)
    navigator = Navigator(repo)
    visual_localizer = VisualLocalizer(repo)
    vlm_client = VlmClient()
    vlm_map_navigator = VlmMapNavigator(repo, vlm_client, ADMIN_DIR / "maps")
    upload_dir = Path(os.getenv("GUIDE_UPLOAD_DIR") or DEFAULT_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(
        title="Longbin Building Smart Guide Backend",
        description="Provides localization, route planning, and exhibit knowledge services for the XiaoZhi ESP32 terminal.",
        version="1.0.0",
    )
    app.add_middleware(AccessControlMiddleware)
    app.mount(
        "/flow/static",
        StaticFiles(directory=FLOW_LAB_DIR),
        name="flow_lab_static",
    )
    app.mount(
        "/admin/static",
        StaticFiles(directory=ADMIN_DIR),
        name="admin_static",
    )
    app.mount(
        "/admin/uploads",
        StaticFiles(directory=upload_dir),
        name="admin_uploads",
    )
    app.include_router(build_data_router(store, vlm_client, upload_dir))
    app.include_router(build_mcp_router(store, navigator))
    app.include_router(
        build_device_router(
            store,
            repo,
            navigator,
            visual_localizer,
            vlm_client,
            vlm_map_navigator,
        )
    )

    def route_response_from_result(result) -> RouteResponse:
        return RouteResponse(
            from_id=result.from_id,
            to_id=result.to_id,
            total_distance_m=result.total_distance_m,
            announcement=result.announcement,
            steps=[step.__dict__ for step in result.steps],
            planner=result.planner,
            confidence=result.confidence,
            assumptions=result.assumptions,
        )

    async def plan_route_result(
        from_location: str,
        to_location: str,
        language: str,
        accessible_only: bool,
    ):
        try:
            if vlm_map_navigator.enabled:
                return await vlm_map_navigator.plan(
                    from_location,
                    to_location,
                    language,
                    accessible_only,
                )
        except LocationNotFoundError:
            raise
        except (VlmNotConfiguredError, VlmResponseError) as exc:
            if vlm_map_navigator.strict:
                status_code = 503 if isinstance(exc, VlmNotConfiguredError) else 502
                raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        resolved_to_location, _, _ = repo.resolve_destination(to_location)
        return navigator.plan(
            from_location,
            resolved_to_location,
            language,
            accessible_only,
        )

    def build_exhibit_context(
        exhibit_id: str,
        question: str,
        language: str,
    ) -> ExhibitContextResponse:
        exhibit = repo.get_exhibit(exhibit_id)
        suffix = "en" if language == "en" else "zh"
        instruction = (
            "Answer only from the supplied facts. If the facts are insufficient, say that the curated exhibit data does not contain the answer."
            if language == "en"
            else "Answer only from the supplied exhibit facts. If the information is insufficient, clearly state that the curated exhibit data does not contain the answer."
        )
        return ExhibitContextResponse(
            exhibit_id=exhibit["id"],
            location_id=exhibit["location_id"],
            name=exhibit[f"name_{suffix}"],
            summary=exhibit[f"summary_{suffix}"],
            facts=exhibit[f"facts_{suffix}"],
            question=question,
            system_instruction=instruction,
        )

    def build_personalized_reply(
        request: GuideFlowRequest,
        localization: VisualLocalizationResponse,
        route: RouteResponse | None,
        exhibit_context: ExhibitContextResponse | None,
        destination_label: str,
    ) -> str:
        profile = request.visitor_profile
        audience_bits = [bit for bit in [profile.user_type, profile.age_group] if bit]
        profile_prefix = f"For this visitor ({', '.join(audience_bits)}), " if audience_bits else ""

        if localization.status == "not_found":
            return "I cannot reliably determine the current location yet. Please upload a clearer photo showing a room number or a strong landmark, and then I can continue with navigation."

        if localization.status == "ambiguous":
            names = [candidate.name_en for candidate in localization.candidates[:2]]
            joined = " / ".join(names)
            return f"I think you may be near {joined}, but I still need confirmation of your current location before planning the route to {destination_label}."

        segments: list[str] = []
        current_name = localization.candidates[0].name_en
        segments.append(f"{profile_prefix}I identified the current location as {current_name}.")
        if route is not None:
            segments.append(
                f"The route to {destination_label} is about {route.total_distance_m:g} meters and includes {len(route.steps)} steps."
            )
            if route.announcement:
                segments.append(route.announcement)
        if exhibit_context is not None:
            facts = "; ".join(exhibit_context.facts[:2])
            segments.append(f"At the destination, you can explain: {facts}")
        if profile.preferences:
            segments.append(f"Visitor preferences to keep in mind: {', '.join(profile.preferences)}.")
        if profile.accessibility_needs or request.accessible_only:
            needs = profile.accessibility_needs or ["accessible route"]
            segments.append(f"Accessibility considerations: {', '.join(needs)}.")
        return " ".join(segments)

    @app.get("/flow", include_in_schema=False)
    async def flow_lab() -> FileResponse:
        return FileResponse(FLOW_LAB_DIR / "index.html")

    @app.get("/admin", include_in_schema=False)
    async def admin_console() -> FileResponse:
        return FileResponse(ADMIN_DIR / "index.html")

    @app.get("/admin/en", include_in_schema=False)
    async def admin_console_en() -> FileResponse:
        return FileResponse(ADMIN_DIR / "index-en.html")

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
        image: UploadFile = File(description="Indoor photo in JPEG, PNG, or WebP format"),
        floor_hint: int | None = Form(default=None),
    ) -> VisualLocalizationResponse:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Only JPEG, PNG, or WebP images are supported",
            )
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image must not exceed 5 MiB")
        if not content:
            raise HTTPException(status_code=400, detail="Image content is empty")
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
            result = await plan_route_result(
                request.from_location,
                request.to_location,
                request.language,
                request.accessible_only,
            )
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return route_response_from_result(result)

    @app.get("/api/v1/exhibits", tags=["exhibits"])
    async def list_exhibits() -> dict[str, list[dict]]:
        return {"exhibits": repo.list_exhibits()}

    @app.post(
        "/api/v1/exhibits/resolve",
        response_model=ExhibitResolveResponse,
        tags=["exhibits"],
    )
    async def resolve_exhibit(
        request: VisualLocalizeRequest,
    ) -> ExhibitResolveResponse:
        return visual_localizer.resolve_exhibit(request)

    @app.post(
        "/api/v1/exhibits/resolve-context",
        response_model=ExhibitResolveContextResponse,
        tags=["exhibits"],
    )
    async def resolve_exhibit_context(
        request: ExhibitResolveContextRequest,
    ) -> ExhibitResolveContextResponse:
        evidence = VisualLocalizeRequest(
            objects=request.objects,
            recognized_texts=request.recognized_texts,
            scene_description=request.scene_description,
            floor_hint=request.floor_hint,
        )
        resolved = visual_localizer.resolve_exhibit(evidence)
        if resolved.status != "matched" or resolved.exhibit_id is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": resolved.status,
                    "confidence": resolved.confidence,
                    "needs_confirmation": resolved.needs_confirmation,
                    "candidates": [candidate.model_dump() for candidate in resolved.candidates],
                },
            )

        exhibit = repo.get_exhibit(resolved.exhibit_id)
        suffix = "en" if request.language == "en" else "zh"
        matched_features = (
            resolved.candidates[0].matched_features if resolved.candidates else []
        )
        return ExhibitResolveContextResponse(
            status="matched",
            exhibit_id=exhibit["id"],
            location_id=exhibit["location_id"],
            confidence=resolved.confidence,
            needs_confirmation=resolved.needs_confirmation,
            matched_features=matched_features,
            candidates=resolved.candidates,
            evidence=evidence,
            name=exhibit[f"name_{suffix}"],
            summary=exhibit[f"summary_{suffix}"],
            facts=exhibit[f"facts_{suffix}"],
            question=request.question,
            system_instruction=(
                "Answer only from the supplied exhibit name, summary, and facts. If they are insufficient, say that the curated exhibit data does not contain the answer."
                if request.language == "en"
                else "Answer only from the supplied exhibit name, summary, and facts. If they are insufficient, clearly state that the curated exhibit data does not contain the answer."
            ),
        )

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
            return build_exhibit_context(exhibit_id, request.question, request.language)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/v1/guide/from-image",
        response_model=GuideFlowResponse,
        tags=["guide-flow"],
    )
    async def guide_from_image(
        payload: str = Form(..., description="GuideFlowRequest JSON string"),
        image: UploadFile = File(description="Indoor photo used to identify the current location"),
    ) -> GuideFlowResponse:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Only JPEG, PNG, or WebP images are supported")
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image must not exceed 5 MiB")
        if not content:
            raise HTTPException(status_code=400, detail="Image content is empty")

        try:
            request = GuideFlowRequest.model_validate_json(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc

        try:
            evidence = await vlm_client.analyze(content, image.content_type)
        except VlmNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except VlmResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        localization = visual_localizer.locate(evidence)

        if request.current_location:
            try:
                node = repo.get_location(request.current_location)
            except LocationNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            localization = VisualLocalizationResponse(
                status="matched",
                node_id=node["id"],
                confidence=1.0,
                needs_confirmation=False,
                candidates=[
                    VisualCandidateResponse(
                        node_id=node["id"],
                        name_zh=node["name_zh"],
                        name_en=node["name_en"],
                        floor=node["floor"],
                        score=1.0,
                        matched_features=["manual_override"],
                    )
                ],
                evidence=evidence,
            )

        try:
            resolved_destination_id, destination_type, exhibit = repo.resolve_destination(request.destination)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        route_response: RouteResponse | None = None
        exhibit_response: ExhibitContextResponse | None = None

        if localization.node_id is not None:
            try:
                route_result = await plan_route_result(
                    localization.node_id,
                    resolved_destination_id,
                    request.language,
                    request.accessible_only or bool(request.visitor_profile.accessibility_needs),
                )
                route_response = route_response_from_result(route_result)
            except RouteNotFoundError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except LocationNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

        if destination_type == "exhibit" and exhibit is not None:
            exhibit_question = request.question or "Give me a short introduction suitable for this visitor"
            exhibit_response = build_exhibit_context(exhibit["id"], exhibit_question, request.language)
            destination_label = exhibit["name_en"] if request.language == "en" else exhibit["name_zh"]
        else:
            destination_node = repo.get_location(resolved_destination_id)
            destination_label = destination_node["name_en"] if request.language == "en" else destination_node["name_zh"]

        reply = build_personalized_reply(
            request=request,
            localization=localization,
            route=route_response,
            exhibit_context=exhibit_response,
            destination_label=destination_label,
        )

        return GuideFlowResponse(
            localization=localization,
            resolved_destination_id=resolved_destination_id,
            destination_type=destination_type,
            route=route_response,
            exhibit_context=exhibit_response,
            reply=reply,
        )

    @app.get("/api/v1/resolve", tags=["places"])
    async def resolve_place(
        q: str | None = Query(default=None, min_length=1),
        name: str | None = Query(default=None, min_length=1),
    ) -> dict[str, str]:
        value = q or name
        if value is None:
            raise HTTPException(status_code=422, detail="A query parameter q or name is required")
        try:
            return {"node_id": repo.resolve_location(value)}
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


try:
    app = create_app()
except DataValidationError as exc:
    raise RuntimeError(f"Failed to load guide data: {exc}") from exc
