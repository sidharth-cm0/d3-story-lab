"""Belief model representing character beliefs"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Belief(BaseModel):
    """Represents what a character believes about the world"""

    id: str = Field(..., description="Unique belief ID")
    statement: str = Field(..., description="What is believed")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level: 0.0 (certain false) to 1.0 (certain true)",
    )
    source: Optional[str] = Field(
        None, description="Where the belief came from (observation, inference, hearsay)"
    )
    character_id: str = Field(..., description="Character who holds this belief")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "bel_001",
                "statement": "Maya has important documents",
                "confidence": 0.9,
                "source": "observation",
                "character_id": "char_arjun",
            }
        }
    )
