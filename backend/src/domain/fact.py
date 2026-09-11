"""Information and DiscoveredFact domain model for D3 Story Lab."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class DiscoveredFact(BaseModel):
    """An objective piece of evidence or subjective claim discovered by a character."""

    id: str = Field(..., description="Unique fact ID")
    statement: str = Field(..., description="Human-readable statement of the fact")
    source: str = Field(
        default="inspection",
        description="Source of fact: 'inspection', 'dialogue', 'observation', 'inference'",
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence level 0.0 to 1.0"
    )
    discovered_by: str = Field(..., description="Actor ID who discovered this fact")
    tick: int = Field(..., ge=0, description="Tick when discovered")
    related_entities: List[str] = Field(
        default_factory=list,
        description="IDs of related objects, characters, or locations",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata"
    )

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "id": "fact_001",
                "statement": "The dossier contains financial records of illicit payments.",
                "source": "inspection",
                "confidence": 1.0,
                "discovered_by": "char_alpha",
                "tick": 2,
                "related_entities": ["obj_dossier", "char_alpha"],
                "metadata": {"object_id": "obj_dossier"},
            }
        },
    )
