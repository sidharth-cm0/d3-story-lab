"""Conflict domain models for narrative tension and dramatic incompatibility analysis."""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from .character_creation import FieldAuthority


class ConflictDimension(str, Enum):
    """Specific dimensions of interpersonal and dramatic conflict between characters."""

    GOAL_OPPOSITION = "goal_opposition"
    VALUE_OPPOSITION = "value_opposition"
    BELIEF_CONTRADICTION = "belief_contradiction"
    RESOURCE_COMPETITION = "resource_competition"
    SECRET_EXPOSURE_RISK = "secret_exposure_risk"
    RELATIONSHIP_TENSION = "relationship_tension"
    DEPENDENCY = "dependency"
    HISTORICAL_GRIEVANCE = "historical_grievance"
    POWER_CONFLICT = "power_conflict"
    MORAL_CONFLICT = "moral_conflict"


class ConflictEvidence(BaseModel):
    """Concrete, traceable evidence justifying an observed conflict dimension."""

    dimension: ConflictDimension = Field(..., description="The dimension of conflict evidenced")
    source_id: str = Field(..., description="ID or identifier of the source entity (e.g. goal_id, secret_id, value name)")
    target_id: Optional[str] = Field(default=None, description="ID of the target entity or peer character if applicable")
    description: str = Field(..., description="Explainable description of the conflict mechanism")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured evidence parameters")
    is_user_authored: bool = Field(
        default=False,
        description="Whether this evidence represents explicit user/author design intent",
    )

    model_config = ConfigDict(frozen=True)


class ConflictEdge(BaseModel):
    """Directed or pairwise analytical conflict assessment between two characters.

    CRITICAL INVARIANT:
    ConflictEdge is purely design-time / analytical metadata.
    It creates dramatic PRESSURE and OPPORTUNITY only.
    It must NEVER directly mutate canonical WorldState, create simulation Events,
    or force confrontation actions bypassing DecisionPolicy.
    """

    source_character_id: str = Field(..., description="Source character ID")
    target_character_id: str = Field(..., description="Target character ID")
    dimensions: Dict[ConflictDimension, float] = Field(
        default_factory=dict,
        description="Dimension scores mapped from 0.0 (none) to 1.0 (acute tension)",
    )
    evidence: List[ConflictEvidence] = Field(
        default_factory=list,
        description="List of traceable evidence items substantiating the scores",
    )
    aggregate_intensity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Derived secondary intensity score. NEVER authoritative, for diagnostic/UI convenience only.",
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of conflict assessment",
    )
    is_analytical_only: bool = Field(
        default=True,
        description="Invariant flag confirming this edge never directly mutates simulation state",
    )
    authority: FieldAuthority = Field(
        default=FieldAuthority.SYSTEM_INFERRED,
        description="Authority level of this assessment (respects USER_LOCKED)",
    )
    is_locked: bool = Field(
        default=False,
        description="Whether this conflict assessment is locked against automated re-derivation",
    )
    locked_dimensions: List[ConflictDimension] = Field(
        default_factory=list,
        description="Explicit dimensions locked by user authorial design",
    )

    model_config = ConfigDict(extra="ignore")

    def get_dimension_score(self, dimension: ConflictDimension) -> float:
        """Return score for a given dimension, defaulting to 0.0."""
        return self.dimensions.get(dimension, 0.0)

    def get_evidence_for(self, dimension: ConflictDimension) -> List[ConflictEvidence]:
        """Filter evidence items matching a specific dimension."""
        return [e for e in self.evidence if e.dimension == dimension]


class ConflictGraph(BaseModel):
    """Collection of derived ConflictEdges for a project cast.

    CRITICAL INVARIANT:
    Stored as a design-time snapshot or refreshed analytically.
    Never writes to WorldState.
    """

    project_id: str = Field(..., description="Project ID")
    edges: List[ConflictEdge] = Field(
        default_factory=list,
        description="Collection of pairwise conflict edges",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Generation timestamp",
    )
    derived_at_tick: Optional[int] = Field(
        default=None,
        description="Simulation tick at which this conflict graph was derived",
    )

    model_config = ConfigDict(extra="ignore")

    def get_edge(self, char_a_id: str, char_b_id: str) -> Optional[ConflictEdge]:
        """Find an edge between two characters in either direction."""
        for edge in self.edges:
            if (edge.source_character_id == char_a_id and edge.target_character_id == char_b_id) or (
                edge.source_character_id == char_b_id and edge.target_character_id == char_a_id
            ):
                return edge
        return None

    def get_edges_for_character(self, character_id: str) -> List[ConflictEdge]:
        """Return all edges involving the given character."""
        return [
            edge
            for edge in self.edges
            if edge.source_character_id == character_id or edge.target_character_id == character_id
        ]
