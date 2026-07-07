from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .repository import GuideRepository
from .schemas import (
    VisualCandidateResponse,
    VisualLocalizeRequest,
    VisualLocalizationResponse,
)


MIN_MATCH_SCORE = 0.20
AMBIGUITY_RATIO = 0.80
MAX_CANDIDATES = 3


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized).strip()


def _matches(alias: str, observation: str) -> bool:
    alias_normalized = _normalize(alias)
    observation_normalized = _normalize(observation)
    if not alias_normalized or not observation_normalized:
        return False
    if alias_normalized == observation_normalized:
        return True
    shorter = min(len(alias_normalized), len(observation_normalized))
    contains_cjk = bool(
        re.search(r"[\u4e00-\u9fff]", alias_normalized + observation_normalized)
    )
    minimum_substring = 2 if contains_cjk else 3
    return shorter >= minimum_substring and (
        alias_normalized in observation_normalized
        or observation_normalized in alias_normalized
    )


@dataclass(frozen=True)
class Observation:
    text: str
    confidence: float


class VisualLocalizer:
    def __init__(self, repository: GuideRepository) -> None:
        self.repository = repository

    def _observations(self, evidence: VisualLocalizeRequest) -> list[Observation]:
        observations = [
            Observation(item.label, item.confidence) for item in evidence.objects
        ]
        observations.extend(
            Observation(text, 1.0)
            for text in evidence.recognized_texts
            if text.strip()
        )
        if evidence.scene_description.strip():
            observations.append(Observation(evidence.scene_description, 0.7))
        return observations

    def locate(self, evidence: VisualLocalizeRequest) -> VisualLocalizationResponse:
        observations = self._observations(evidence)
        candidates: list[VisualCandidateResponse] = []

        for node in self.repository.data.nodes.values():
            if evidence.floor_hint is not None and node["floor"] != evidence.floor_hint:
                continue
            landmarks = node.get("visual_landmarks", [])
            if not landmarks:
                continue

            total_weight = sum(float(item.get("weight", 1)) for item in landmarks)
            matched_weight = 0.0
            matched_features: list[str] = []

            for landmark in landmarks:
                aliases = landmark["aliases"]
                best_confidence = 0.0
                best_observation = ""
                for observation in observations:
                    if any(_matches(alias, observation.text) for alias in aliases):
                        if observation.confidence > best_confidence:
                            best_confidence = observation.confidence
                            best_observation = observation.text
                if best_confidence:
                    matched_weight += float(landmark.get("weight", 1)) * best_confidence
                    matched_features.append(best_observation)

            score = matched_weight / total_weight if total_weight else 0
            if score > 0:
                candidates.append(
                    VisualCandidateResponse(
                        node_id=node["id"],
                        name_zh=node["name_zh"],
                        name_en=node["name_en"],
                        floor=node["floor"],
                        score=round(score, 4),
                        matched_features=matched_features,
                    )
                )

        candidates.sort(key=lambda candidate: (-candidate.score, candidate.node_id))
        candidates = candidates[:MAX_CANDIDATES]

        if not candidates or candidates[0].score < MIN_MATCH_SCORE:
            return VisualLocalizationResponse(
                status="not_found",
                node_id=None,
                confidence=candidates[0].score if candidates else 0,
                needs_confirmation=True,
                candidates=candidates,
                evidence=evidence,
            )

        best = candidates[0]
        ambiguous = (
            len(candidates) > 1
            and candidates[1].score >= best.score * AMBIGUITY_RATIO
        )
        return VisualLocalizationResponse(
            status="ambiguous" if ambiguous else "matched",
            node_id=None if ambiguous else best.node_id,
            confidence=best.score,
            needs_confirmation=ambiguous or best.score < 0.60,
            candidates=candidates,
            evidence=evidence,
        )
