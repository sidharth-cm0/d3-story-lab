"""Domain models for narrative archetypes and observational trajectory tracking."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ArchetypeType(str, Enum):
    """Standard narrative archetype orientations.
    
    CRITICAL INVARIANT:
    Archetype is DESIGN METADATA + DERIVED ANALYTICS only.
    It represents initial orientation, values, tendencies, and thematic pressure.
    It must NEVER force actions, grant knowledge, or hard-code behavior.
    """

    HERO = "HERO"
    RULER = "RULER"
    CAREGIVER = "CAREGIVER"
    CREATOR = "CREATOR"
    INNOCENT = "INNOCENT"
    SAGE = "SAGE"
    EXPLORER = "EXPLORER"
    OUTLAW = "OUTLAW"
    MAGICIAN = "MAGICIAN"
    LOVER = "LOVER"
    JESTER = "JESTER"
    EVERYMAN = "EVERYMAN"

    @classmethod
    def from_str(cls, val: Optional[str]) -> Optional[ArchetypeType]:
        """Safely parse an archetype string, supporting aliases like ARTIST -> CREATOR."""
        if not val or not isinstance(val, str):
            return None
        cleaned = val.strip().upper()
        if cleaned in ("ARTIST", "CREATOR"):
            return cls.CREATOR
        try:
            return cls(cleaned)
        except ValueError:
            return None


class ArchetypeShiftPoint(BaseModel):
    """An observed historical point where character behavioral expression shifted orientation."""

    tick: int = Field(ge=0, description="Simulation tick where orientation shift was observed")
    dominant_archetype: ArchetypeType = Field(description="Expressed dominant archetype during this window")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of the observed orientation")
    evidence_event_ids: List[str] = Field(default_factory=list, description="IDs of events evidencing this shift")
    rationale: str = Field(description="Human-readable explanation of the observed transition")

    model_config = ConfigDict(frozen=True)


class ArchetypeTrajectory(BaseModel):
    """Strictly observational, read-only analysis of a character's archetype alignment drift over time.
    
    CRITICAL INVARIANTS:
    1. Read-only analyzer result: ZERO mutation methods.
    2. Does NOT alter WorldState, character beliefs, or emotions.
    3. Does NOT force future behavior or restrict autonomous simulation.
    """

    character_id: str = Field(description="Character ID analyzed")
    character_name: str = Field(description="Character name")
    initial_archetype: Optional[ArchetypeType] = Field(
        default=None, description="Starting archetype from design profile"
    )
    current_dominant_archetype: Optional[ArchetypeType] = Field(
        default=None, description="Latest observed dominant archetype orientation"
    )
    shift_points: List[ArchetypeShiftPoint] = Field(
        default_factory=list, description="Chronological record of observed archetype shifts"
    )
    trajectory_summary: str = Field(
        default="", description="Narrative synthesis of the character's orientation journey"
    )
    stability_score: float = Field(
        ge=0.0, le=1.0, default=1.0, description="1.0 = highly stable initial orientation, <0.7 = substantial shift"
    )
    is_observed_only: bool = Field(
        default=True, description="Always True; highlights post-hoc observational nature"
    )

    model_config = ConfigDict(frozen=True)
