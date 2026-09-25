"""Domain models for reconstructible Character State History and Graph APIs.

CRITICAL INVARIANTS:
1. Purely derived / observational analytics: NEVER canonical source of truth.
2. Event provenance: Every point representing a real change carries event_ids.
3. Sparse by default: Stores or emits points only when significant changes occur.
4. Non-mutating: Zero simulation state mutation paths.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class HistoryPoint(BaseModel):
    """A discrete temporal data point representing a character or relationship metric state."""

    tick: int = Field(..., ge=0, description="Simulation tick of this observation")
    value: float = Field(..., description="Numeric value of the metric at this tick")
    event_ids: List[str] = Field(
        default_factory=list,
        description="IDs of simulation events causing or evidencing this change",
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable summary or milestone description",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g. deltas, participants, raw classifications)",
    )

    model_config = ConfigDict(frozen=True)


class CharacterHistorySeries(BaseModel):
    """Reconstructed time-series for a single metric over the simulation timeline."""

    character_id: str = Field(..., description="Primary character ID")
    target_character_id: Optional[str] = Field(
        default=None,
        description="Target character ID if this is a pairwise relationship dimension",
    )
    metric: str = Field(
        ...,
        description="Metric key (e.g. 'trust', 'goal_pressure', 'emotional_valence', 'archetype_alignment')",
    )
    display_name: str = Field(
        ...,
        description="Human-readable title for UI visualization and legends",
    )
    points: List[HistoryPoint] = Field(
        default_factory=list,
        description="Chronological sequence of data points",
    )
    is_sparse: bool = Field(
        default=True,
        description="Whether this series emits only significant changes vs dense per-tick sampling",
    )
    is_analytical_only: bool = Field(
        default=True,
        description="Invariant flag confirming this series is strictly observational",
    )

    model_config = ConfigDict(extra="ignore")

    def get_latest_value(self, default: float = 0.0) -> float:
        """Return the most recent value in the series."""
        return self.points[-1].value if self.points else default

    def get_points_with_events(self) -> List[HistoryPoint]:
        """Return only points that have associated causal event provenance."""
        return [p for p in self.points if p.event_ids]


class CharacterHistoryReport(BaseModel):
    """Collection of reconstructed historical time-series for a character or character pair."""

    project_id: str = Field(..., description="Project ID")
    character_id: str = Field(..., description="Character ID")
    series: Dict[str, CharacterHistorySeries] = Field(
        default_factory=dict,
        description="Dictionary mapping metric name to CharacterHistorySeries",
    )
    generated_at_tick: int = Field(
        default=0,
        ge=0,
        description="Simulation tick at which this history was reconstructed",
    )
    total_events_analyzed: int = Field(
        default=0,
        ge=0,
        description="Count of immutable events evaluated during reconstruction",
    )
    is_observed_only: bool = Field(
        default=True,
        description="Invariant confirming this report is observational only",
    )

    model_config = ConfigDict(extra="ignore")
