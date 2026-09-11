"""Secret model representing private knowledge"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Secret(BaseModel):
    """Represents private knowledge that a character holds"""

    id: str = Field(..., description="Unique secret ID")
    character_id: str = Field(..., description="Character who knows this secret")
    statement: str = Field(..., description="The secret information")
    known_by: List[str] = Field(
        default_factory=list,
        description="Other character IDs who know this secret (may be empty)",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How important this secret is",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sec_001",
                "character_id": "char_maya",
                "statement": "The documents contain evidence of corporate fraud",
                "known_by": [],
                "importance": 1.0,
            }
        }
    )
