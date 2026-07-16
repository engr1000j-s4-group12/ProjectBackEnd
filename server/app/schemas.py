from typing import Any, Literal

from pydantic import BaseModel, Field


Language = Literal["zh", "en"]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class LocalizeRequest(BaseModel):
    marker_id: str = Field(
        min_length=1,
        examples=["LB-1F-ENTRANCE"],
        description="二维码中保存的地点 ID，也支持地点别名",
    )


class LocationResponse(BaseModel):
    node_id: str
    name_zh: str
    name_en: str
    floor: int
    kind: str
    confidence: float = 1.0


class VisualObject(BaseModel):
    label: str = Field(min_length=1, examples=["red reception desk"])
    confidence: float = Field(default=1.0, ge=0, le=1)


class VisualLocalizeRequest(BaseModel):
    objects: list[VisualObject] = Field(default_factory=list)
    recognized_texts: list[str] = Field(default_factory=list)
    scene_description: str = ""
    floor_hint: int | None = None


class VisualCandidateResponse(BaseModel):
    node_id: str
    name_zh: str
    name_en: str
    floor: int
    score: float
    matched_features: list[str]


class VisualLocalizationResponse(BaseModel):
    status: Literal["matched", "ambiguous", "not_found"]
    node_id: str | None
    confidence: float
    needs_confirmation: bool
    candidates: list[VisualCandidateResponse]
    evidence: VisualLocalizeRequest


class ExhibitResolveCandidateResponse(BaseModel):
    exhibit_id: str
    location_id: str
    name_zh: str
    name_en: str
    score: float
    matched_features: list[str]


class ExhibitResolveResponse(BaseModel):
    status: Literal["matched", "ambiguous", "not_found"]
    exhibit_id: str | None
    location_id: str | None
    confidence: float
    needs_confirmation: bool
    candidates: list[ExhibitResolveCandidateResponse]
    evidence: VisualLocalizeRequest


class RouteRequest(BaseModel):
    from_location: str = Field(examples=["LB-1F-ENTRANCE"])
    to_location: str = Field(examples=["EXHIBIT-ROBOT"])
    language: Language = "zh"
    accessible_only: bool = False


class RouteStepResponse(BaseModel):
    from_id: str
    to_id: str
    distance_m: float
    instruction: str


class RouteResponse(BaseModel):
    from_id: str
    to_id: str
    total_distance_m: float
    announcement: str
    steps: list[RouteStepResponse]


class ExhibitQuestionRequest(BaseModel):
    question: str = Field(min_length=1, examples=["这个展品有什么意义？"])
    language: Language = "zh"


class ExhibitResolveContextRequest(VisualLocalizeRequest):
    question: str = Field(min_length=1, examples=["介绍一下这个展品"])
    language: Language = "zh"


class ExhibitContextResponse(BaseModel):
    exhibit_id: str
    location_id: str
    name: str
    summary: str
    facts: list[str]
    question: str
    system_instruction: str


class ExhibitResolveContextResponse(ExhibitContextResponse):
    status: Literal["matched"]
    confidence: float
    needs_confirmation: bool
    matched_features: list[str]
    candidates: list[ExhibitResolveCandidateResponse]
    evidence: VisualLocalizeRequest


KnowledgeKind = Literal["permanent", "event", "exhibit", "facility"]


class KnowledgeEntryCreate(BaseModel):
    node_id: str = Field(min_length=1, pattern=r"^LB-[1-4]F-[A-Z0-9-]+$")
    group_code: str = ""
    floor: int = Field(ge=1, le=4)
    geometry: list[list[float]] = Field(min_length=3)
    kind: KnowledgeKind
    title_zh: str = Field(min_length=1)
    title_en: str = ""
    content_zh: str = ""
    content_en: str = ""
    tags: list[str] = Field(default_factory=list)
    source: str = ""


class KnowledgeEntryUpdate(BaseModel):
    node_id: str | None = Field(default=None, pattern=r"^LB-[1-4]F-[A-Z0-9-]+$")
    group_code: str | None = None
    floor: int | None = Field(default=None, ge=1, le=4)
    geometry: list[list[float]] | None = None
    kind: KnowledgeKind | None = None
    title_zh: str | None = Field(default=None, min_length=1)
    title_en: str | None = None
    content_zh: str | None = None
    content_en: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    extracted: dict[str, Any] | None = None


class VisitCreate(BaseModel):
    delegation_name: str = Field(min_length=1)
    institution: str = ""
    country: str = ""
    preferred_language: Language = "en"
    purpose: str = ""
    itinerary: list[dict[str, Any]] = Field(default_factory=list)
    script_zh: str = ""
    script_en: str = ""


class DeviceSessionStartRequest(BaseModel):
    visit_id: int | None = None
    current_node: str | None = None
    destination_node: str | None = None
    preferred_language: Language = "zh"


class DeviceResolvePlaceRequest(BaseModel):
    name: str = Field(min_length=1)


class DeviceRouteRequest(BaseModel):
    from_location: str | None = None
    to_location: str = Field(min_length=1)
    language: Language = "zh"
    accessible_only: bool = False
