from typing import Literal

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
    steps: list[RouteStepResponse]


class ExhibitQuestionRequest(BaseModel):
    question: str = Field(min_length=1, examples=["这个展品有什么意义？"])
    language: Language = "zh"


class ExhibitContextResponse(BaseModel):
    exhibit_id: str
    location_id: str
    name: str
    facts: list[str]
    question: str
    system_instruction: str
