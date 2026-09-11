"""Relationship model representing connections between characters"""
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Relationship(BaseModel):
    """Represents a relationship between two characters"""

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
    history: str = Field(
        default="", description="Description of their relationship history"
    )

    @field_validator("affinity", "trust")
    @classmethod
    def validate_values(cls, v):
        if not (-1.0 <= v <= 1.0):
            raise ValueError("Value must be between -1.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "rel_001",
                "character_a_id": "char_arjun",
                "character_b_id": "char_maya",
                "affinity": 0.6,
                "trust": 0.4,
                "history": "Colleagues at a consulting firm",
            }
        }
    )
