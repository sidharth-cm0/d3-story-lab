"""Proposition and Knowledge domain models for D3 Story Lab."""
from __future__ import annotations
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict


class Proposition(BaseModel):
    """Canonical objective proposition registered in the WorldState source of truth."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique proposition ID, e.g. 'prop_maya_has_dossier'")
    subject: str = Field(..., description="Subject entity ID or name")
    predicate: str = Field(..., description="Predicate relation, e.g. 'has', 'knows', 'stole'")
    object: str = Field(..., description="Object entity ID, name, or claim")
    truth_value: bool = Field(default=True, description="Canonical objective truth in the world")
    is_secret: bool = Field(default=False, description="Whether this proposition is private/secret knowledge")


class KnowledgeItem(BaseModel):
    """Subjective knowledge held by an individual character about a proposition."""
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    proposition_id: str = Field(..., description="ID of the referenced Proposition")
    holder_id: str = Field(..., description="ID of the character holding this knowledge")
    certainty: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence certainty [0.0, 1.0]")
    acquired_at_event: str = Field(default="", description="Event ID when this knowledge was acquired")
    source: Literal["observed", "inferred", "told"] = Field(
        default="observed", description="Source of knowledge: observed, inferred, or told"
    )
    source_character_id: Optional[str] = Field(
        default=None, description="Character ID who shared/told this knowledge, if source is 'told'"
    )
    shared_with: List[str] = Field(
        default_factory=list, description="IDs of characters this holder has shared the knowledge with"
    )
    believed_truth_value: bool = Field(
        default=True, description="What the holder believes the truth value to be (supports deception)"
    )

    def __init__(self, **data: Any):
        if "truth_value" in data and "believed_truth_value" not in data:
            data["believed_truth_value"] = data.pop("truth_value")
        super().__init__(**data)

    @property
    def truth_value(self) -> bool:
        """Subjective truth value believed by this holder."""
        return self.believed_truth_value
