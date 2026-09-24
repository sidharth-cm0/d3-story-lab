"""Completeness scoring for character profiles."""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from .character import Character
from .character_creation import CharacterProfileDraft

DEFAULT_FIELD_WEIGHTS: Dict[str, float] = {
    "name": 15.0,
    "role": 15.0,
    "goals": 20.0,
    "secrets": 15.0,
    "personality_traits": 15.0,
    "visual_profile": 15.0,
    "beliefs": 5.0,
}


class CompletenessReport(BaseModel):
    """Evaluation of a character profile's completeness and missing fields."""

    score: float = Field(..., description="Weighted completeness score between 0 and 100")
    normalized_score: float = Field(..., description="Score normalized to 0.0 - 1.0")
    is_complete: bool = Field(..., description="True if score >= 80 and essential fields are present")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing important fields")
    present_fields: List[str] = Field(default_factory=list, description="List of present fields")
    field_scores: Dict[str, float] = Field(default_factory=dict, description="Points earned per field")
    weights: Dict[str, float] = Field(default_factory=dict, description="Weights assigned per field")

    model_config = ConfigDict(extra="ignore")


def calculate_character_completeness(
    profile: Union[CharacterProfileDraft, Character, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> CompletenessReport:
    """Pure deterministic function scoring profile completeness and listing missing fields."""
    active_weights = dict(weights or DEFAULT_FIELD_WEIGHTS)
    field_scores: Dict[str, float] = {}
    missing_fields: List[str] = []
    present_fields: List[str] = []

    # Helper to extract value regardless of whether profile is draft, Character, or dict
    def get_val(key: str) -> Any:
        if isinstance(profile, dict):
            return profile.get(key)
        return getattr(profile, key, None)

    # 1. Name
    name = get_val("name")
    if name and isinstance(name, str) and name.strip():
        field_scores["name"] = active_weights.get("name", 15.0)
        present_fields.append("name")
    else:
        field_scores["name"] = 0.0
        missing_fields.append("name")

    # 2. Role / Profession
    role = get_val("role")
    if role and isinstance(role, str) and role.strip():
        field_scores["role"] = active_weights.get("role", 15.0)
        present_fields.append("role")
    else:
        field_scores["role"] = 0.0
        missing_fields.append("role")

    # 3. Goals
    goals = get_val("goals")
    if goals and isinstance(goals, (list, set, tuple)) and len(goals) > 0 and any(str(g).strip() for g in goals):
        field_scores["goals"] = active_weights.get("goals", 20.0)
        present_fields.append("goals")
    else:
        field_scores["goals"] = 0.0
        missing_fields.append("goals")

    # 4. Secrets / Fears
    secrets = get_val("secrets")
    if secrets and isinstance(secrets, (list, set, tuple)) and len(secrets) > 0 and any(str(s).strip() for s in secrets):
        field_scores["secrets"] = active_weights.get("secrets", 15.0)
        present_fields.append("secrets")
    else:
        field_scores["secrets"] = 0.0
        missing_fields.append("secrets")

    # 5. Personality traits
    traits = get_val("personality_traits")
    has_traits = False
    if traits:
        if isinstance(traits, dict) and len(traits) > 0:
            has_traits = True
        elif isinstance(traits, (list, set, tuple)) and len(traits) > 0:
            has_traits = True
    if has_traits:
        field_scores["personality_traits"] = active_weights.get("personality_traits", 15.0)
        present_fields.append("personality_traits")
    else:
        field_scores["personality_traits"] = 0.0
        missing_fields.append("personality_traits")

    # 6. Visual Profile / Appearance
    vis = get_val("visual_profile")
    has_vis = False
    if vis is not None:
        if isinstance(vis, dict):
            if any(vis.get(k) for k in ("clothing", "face_traits", "build", "hairstyle", "age")):
                has_vis = True
        elif hasattr(vis, "clothing") or hasattr(vis, "face_traits"):
            if getattr(vis, "clothing", None) or getattr(vis, "face_traits", None):
                has_vis = True
    if has_vis:
        field_scores["visual_profile"] = active_weights.get("visual_profile", 15.0)
        present_fields.append("visual_profile")
    else:
        field_scores["visual_profile"] = 0.0
        missing_fields.append("visual_profile")

    # 7. Beliefs
    beliefs = get_val("beliefs")
    if beliefs and isinstance(beliefs, (list, set, tuple)) and len(beliefs) > 0 and any(str(b).strip() for b in beliefs):
        field_scores["beliefs"] = active_weights.get("beliefs", 5.0)
        present_fields.append("beliefs")
    else:
        field_scores["beliefs"] = 0.0
        missing_fields.append("beliefs")

    total_weight = sum(active_weights.values()) or 100.0
    total_score = sum(field_scores.values())
    pct_score = round(min(100.0, max(0.0, (total_score / total_weight) * 100.0)), 1)
    normalized = round(pct_score / 100.0, 3)

    is_complete = pct_score >= 80.0 and "name" in present_fields and "role" in present_fields

    return CompletenessReport(
        score=pct_score,
        normalized_score=normalized,
        is_complete=is_complete,
        missing_fields=missing_fields,
        present_fields=present_fields,
        field_scores=field_scores,
        weights=active_weights,
    )
