"""Memory model representing character memories"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Memory(BaseModel):
    """Represents a character's memory of an event"""

    id: str = Field(..., description="Unique memory ID")
    character_id: str = Field(..., description="Character who has this memory")
    event_id: Optional[str] = Field(
        None, description="Event ID this memory is based on"
    )
    summary: str = Field(..., description="Summary of what was remembered")
    importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How important this memory is: 0.0 (trivial) to 1.0 (critical)",
    )
    emotional_weight: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Emotional association: -1.0 (very negative) to 1.0 (very positive)",
    )
    participants: List[str] = Field(
        default_factory=list, description="Other character IDs involved"
    )
    tick: int = Field(..., ge=0, description="Simulation tick when memory was formed")
    tags: List[str] = Field(default_factory=list, description="Descriptive or categorical tags")
    created_at: Optional[str] = Field(None, description="ISO timestamp of memory formation")

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Importance must be between 0.0 and 1.0")
        return v

    @field_validator("emotional_weight")
    @classmethod
    def validate_emotional_weight(cls, v):
        if not (-1.0 <= v <= 1.0):
            raise ValueError("Emotional weight must be between -1.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "mem_001",
                "character_id": "char_arjun",
                "event_id": "evt_001",
                "summary": "Maya showed me the confidential documents",
                "importance": 0.95,
                "emotional_weight": 0.3,
                "participants": ["char_maya"],
                "tick": 5,
            }
        }
    )
