"""Relationship model representing connections between characters"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Relationship(BaseModel):
    """Represents a relationship between two characters with multidimensional depth and event provenance"""

    id: str = Field(..., description="Unique relationship ID")
    character_a_id: str = Field(..., description="First character ID")
    character_b_id: str = Field(..., description="Second character ID")
    affinity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="How much they like each other: -1.0 (hostile) to 1.0 (intimate)",
    )
    trust: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="How much they trust each other: -1.0 (no trust) to 1.0 (complete trust)",
    )
    affection: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Warmth and positive emotional attachment: -1.0 (revulsion) to 1.0 (deep affection)",
    )
    fear: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Intimidation or dread felt toward other: -1.0 (utterly unthreatened) to 1.0 (terrified)",
    )
    dependency: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Reliance on other: -1.0 (complete autonomy/detachment) to 1.0 (total reliance)",
    )
    respect: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Deference or esteem: -1.0 (contempt) to 1.0 (profound reverence)",
    )
    resentment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Accumulated bitterness or grudge: -1.0 (unreserved goodwill) to 1.0 (bitter grudge)",
    )
    suspicion: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Doubt of motives/honesty: -1.0 (unquestioning trust) to 1.0 (extreme paranoia)",
    )
    power_imbalance: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Perceived dominance/hierarchy: -1.0 (character B dominates A) to 1.0 (character A dominates B)",
    )
    event_provenance: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping of dimension name to list of event IDs that causally modified this dimension",
    )
    last_event_id: Optional[str] = Field(
        default=None,
        description="Event ID that most recently updated this relationship",
    )
    history: str = Field(
        default="", description="Description of their relationship history"
    )

    @field_validator(
        "affinity",
        "trust",
        "affection",
        "fear",
        "dependency",
        "respect",
        "resentment",
        "suspicion",
        "power_imbalance",
    )
    @classmethod
    def validate_values(cls, v):
        if not (-1.0 <= v <= 1.0):
            raise ValueError("Value must be between -1.0 and 1.0")
        return v

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "id": "rel_001",
                "character_a_id": "char_arjun",
                "character_b_id": "char_maya",
                "affinity": 0.6,
                "trust": 0.4,
                "affection": 0.3,
                "fear": 0.0,
                "dependency": 0.2,
                "respect": 0.7,
                "resentment": 0.0,
                "suspicion": 0.1,
                "power_imbalance": 0.0,
                "history": "Colleagues at a consulting firm",
            }
        },
    )
