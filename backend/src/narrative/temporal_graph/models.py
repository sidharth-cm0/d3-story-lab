"""Domain models for the Temporal Character-Relationship Graph.

CRITICAL INVARIANTS:
1. PURELY OBSERVATIONAL:
   The temporal graph is a derived visualization of canonical WorldState and EventLog.
   It NEVER mutates the canonical state.
2. REPLAY CONTINUITY & DETERMINISM:
   Projecting at tick T always yields the exact same graph snapshot for the same events.
3. EVENT PROVENANCE:
   Every edge and state shift carries verifiable event IDs linking back to the EventLog.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class TemporalGraphNode(BaseModel):
    """Character node in the temporal graph at a discrete simulation tick."""

    id: str = Field(..., description="Unique character identifier (e.g. 'char_cross')")
    name: str = Field(..., description="Character display name")
    role: str = Field(..., description="Character role or archetype")
    location_id: Optional[str] = Field(default=None, description="Location ID at this tick")
    location_name: Optional[str] = Field(default=None, description="Location display name")
    goals: List[str] = Field(default_factory=list, description="Active goal descriptions or IDs at this tick")
    beliefs: Dict[str, bool] = Field(
        default_factory=dict,
        description="Private proposition truth values believed by the character at this tick",
    )
    emotional_state: Dict[str, float] = Field(
        default_factory=dict,
        description="Emotion metrics (happiness, fear, anger, trust, curiosity) in range [-1.0, 1.0]",
    )
    active_conflicts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Analytical conflict summaries involving this character",
    )
    secrets_count: int = Field(default=0, description="Count of private secrets held by this character")
    inventory_count: int = Field(default=0, description="Count of items in inventory")

    model_config = ConfigDict(frozen=True)


class TemporalGraphEdge(BaseModel):
    """Multidimensional relationship edge between two characters at a discrete simulation tick."""

    id: str = Field(..., description="Unique edge identifier (e.g. 'rel_cross_vane')")
    source_id: str = Field(..., description="Source character ID")
    target_id: str = Field(..., description="Target character ID")
    source_name: str = Field(..., description="Source character name")
    target_name: str = Field(..., description="Target character name")
    relationship_type: str = Field(
        default="neutral",
        description="High-level classification (e.g. 'allies', 'rivals', 'conflicted', 'neutral', 'hostile')",
    )
    dimensions: Dict[str, float] = Field(
        default_factory=dict,
        description="Multidimensional values: affinity, trust, affection, fear, dependency, respect, resentment, suspicion, power_imbalance",
    )
    aggregate_intensity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall dramatic intensity of the relationship (0.0 to 1.0)",
    )
    directionality: str = Field(
        default="mutual",
        description="'mutual' if symmetric, 'directed' if asymmetric",
    )
    evidence_event_ids: List[str] = Field(
        default_factory=list,
        description="IDs of historical simulation events that shaped or altered this edge up to this tick",
    )
    recent_event_id: Optional[str] = Field(
        default=None,
        description="Most recent event ID that modified this relationship",
    )
    first_observed_tick: int = Field(default=0, description="Tick when edge first emerged")
    last_changed_tick: int = Field(default=0, description="Tick when edge was most recently modified")

    model_config = ConfigDict(frozen=True)


class TemporalGraphSnapshot(BaseModel):
    """Complete temporal character graph snapshot at a specific simulation tick."""

    project_id: str = Field(..., description="Associated project ID")
    tick: int = Field(..., ge=0, description="Discrete simulation tick of this snapshot")
    max_tick: int = Field(..., ge=0, description="Maximum available simulation tick in the project")
    nodes: List[TemporalGraphNode] = Field(default_factory=list, description="Character nodes")
    edges: List[TemporalGraphEdge] = Field(default_factory=list, description="Relationship edges")
    event_count: int = Field(default=0, description="Total events elapsed up to this tick")
    summary: str = Field(
        default="",
        description="Observational summary of the interpersonal dynamics at this tick",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of projection",
    )

    model_config = ConfigDict(frozen=True)


class TemporalGraphDiff(BaseModel):
    """Deterministic delta between two temporal graph snapshots."""

    project_id: str = Field(..., description="Associated project ID")
    from_tick: int = Field(..., ge=0, description="Start tick")
    to_tick: int = Field(..., ge=0, description="End tick")
    node_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Changes in character state (locations, emotions, goals, beliefs)",
    )
    edge_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Shifts in relationship dimensions (delta values, evidence events)",
    )
    causal_event_ids: List[str] = Field(
        default_factory=list,
        description="IDs of events that occurred strictly between from_tick and to_tick",
    )
    summary: str = Field(
        default="",
        description="Human-readable synthesis of how the social landscape transformed",
    )

    model_config = ConfigDict(frozen=True)
