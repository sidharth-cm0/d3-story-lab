"""Narrative Genome v0.1 domain models for D3 Story Lab.

Enforces:
1. STRUCTURE WITHOUT PUPPETRY:
   - Narrative Intelligence is strictly advisory.
   - Simulation remains authoritative.
   - canonical_mutation_allowed is frozen False on all recommendations.
2. Abstract narrative patterns:
   - Describes causality, dramatic functions, tension, information flow, and setup/payoff.
   - Strictly free of copyrighted screenplay dialogue or character scripts.
3. Full provenance tracking distinguishing system-authored, manually-authored, derived, retrieved, and model-generated.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

class DramaticFunction(str, Enum):
    """Dramatic functions for abstract narrative genome patterns and sequence evaluation."""
    SETUP = "SETUP"
    INCITING_INCIDENT = "INCITING_INCIDENT"
    INVESTIGATION = "INVESTIGATION"
    DISCOVERY = "DISCOVERY"
    ESCALATION = "ESCALATION"
    NEGOTIATION = "NEGOTIATION"
    REVERSAL = "REVERSAL"
    CONFRONTATION = "CONFRONTATION"
    CRISIS = "CRISIS"
    CHASE = "CHASE"
    REVELATION = "REVELATION"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"
    COMPLICATION = "COMPLICATION"
    PAYOFF = "PAYOFF"
    TRANSITION = "TRANSITION"


class ConflictType(str, Enum):
    """Abstract classification of conflict sources."""
    INTERNAL = "internal"
    INTERPERSONAL = "interpersonal"
    ENVIRONMENTAL = "environmental"
    INSTITUTIONAL = "institutional"
    IDEOLOGICAL = "ideological"
    INFORMATIONAL = "informational"
    RESOURCE = "resource"
    TEMPORAL = "temporal"


class CausalRelation(str, Enum):
    """Causal relationship between narrative beats or events."""
    CAUSES = "causes"
    ENABLES = "enables"
    PREVENTS = "prevents"
    COMPLICATES = "complicates"
    REVEALS = "reveals"
    MOTIVATES = "motivates"
    RESOLVES = "resolves"
    PAYS_OFF = "pays_off"


class TensionDirection(str, Enum):
    """Vector of tension progression."""
    RISING = "rising"
    FALLING = "falling"
    SUSTAINED = "sustained"
    RELEASE = "release"
    SPIKE = "spike"


class InformationPattern(str, Enum):
    """Patterns of knowledge asymmetry, discovery, and concealment."""
    REVELATION = "revelation"
    CONCEALMENT = "concealment"
    DRAMATIC_IRONY = "dramatic_irony"
    MISUNDERSTANDING = "misunderstanding"
    DISCOVERY = "discovery"
    CONFIRMATION = "confirmation"
    CONTRADICTION = "contradiction"


class ScenePurpose(str, Enum):
    """Dramatic intent of a sequence or beat."""
    ESTABLISH = "establish"
    ESCALATE = "escalate"
    REVEAL = "reveal"
    TEST_RELATIONSHIP = "test_relationship"
    CHANGE_RELATIONSHIP = "change_relationship"
    CREATE_CHOICE = "create_choice"
    INTRODUCE_OBSTACLE = "introduce_obstacle"
    RESOLVE_OBSTACLE = "resolve_obstacle"
    SETUP = "setup"
    PAYOFF = "payoff"
    TRANSITION = "transition"


class SetupPayoffState(str, Enum):
    """Lifecycle state of a narrative setup/payoff thread."""
    NONE = "none"
    SETUP = "setup"
    REINFORCED = "reinforced"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    ABANDONED = "abandoned"


class RecommendationLifecycleStatus(str, Enum):
    """Explicit lifecycle state of a Director narrative recommendation."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    BLOCKED_COOLDOWN = "BLOCKED_COOLDOWN"
    BLOCKED_BUDGET = "BLOCKED_BUDGET"
    BLOCKED_QUIET_PERIOD = "BLOCKED_QUIET_PERIOD"
    REJECTED_VALIDATION = "REJECTED_VALIDATION"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
    EXECUTED = "EXECUTED"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"
    FAILED = "FAILED"


class GenomeSourceType(str, Enum):
    """Provenance category for narrative knowledge and patterns."""
    SYSTEM_AUTHORED = "system-authored"
    MANUALLY_AUTHORED = "manually-authored"
    DERIVED = "derived"
    RETRIEVED = "retrieved"
    MODEL_GENERATED = "model-generated"


class GenomeProvenance(BaseModel):
    """Traceable origin metadata for narrative genome records and analysis."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    source_type: GenomeSourceType = GenomeSourceType.SYSTEM_AUTHORED
    author_or_model: str = "d3_narrative_core"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: Optional[str] = None


class NarrativeGenomeRecord(BaseModel):
    """A structured representation of an abstract, machine-readable dramatic pattern."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(..., description="Unique pattern ID, e.g. NG-001")
    version: str = "0.1.0"
    name: str = Field(..., description="Human-readable name of the abstract pattern")
    description: str = Field(..., description="Abstract description of dramatic pattern without copyrighted text")

    dramatic_function: DramaticFunction = Field(..., description="Primary dramatic function")
    conflict_types: List[ConflictType] = Field(default_factory=list)
    causal_relations: List[CausalRelation] = Field(default_factory=list)

    tension_before: float = Field(default=0.0, ge=0.0, le=1.0)
    tension_after: float = Field(default=0.0, ge=0.0, le=1.0)
    tension_delta: float = 0.0
    tension_direction: TensionDirection = TensionDirection.SUSTAINED

    information_patterns: List[InformationPattern] = Field(default_factory=list)
    scene_purposes: List[ScenePurpose] = Field(default_factory=list)

    setups: List[str] = Field(default_factory=list)
    payoffs: List[str] = Field(default_factory=list)

    character_pressures: List[str] = Field(default_factory=list)
    stakes: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    expected_effects: List[str] = Field(default_factory=list)

    genre_tags: List[str] = Field(default_factory=list)
    provenance: GenomeProvenance = Field(default_factory=GenomeProvenance)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class NarrativeAnalysisResult(BaseModel):
    """Typed evaluation of a simulation window grounded in canonical EventLog IDs."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique analysis result ID")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_ids: List[str] = Field(default_factory=list, description="Canonical event IDs analyzed")

    dramatic_functions: List[DramaticFunction] = Field(default_factory=list)
    active_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    causal_chain: List[Dict[str, Any]] = Field(default_factory=list)

    tension: Dict[str, float] = Field(default_factory=dict, description="Keys: before, after, delta")
    tension_direction: TensionDirection = TensionDirection.SUSTAINED

    information_state: List[Dict[str, Any]] = Field(default_factory=list)
    setup_payoff_status: List[Dict[str, Any]] = Field(default_factory=list)
    scene_purpose: List[ScenePurpose] = Field(default_factory=list)

    pacing_assessment: Dict[str, Any] = Field(default_factory=dict)
    unresolved_threads: List[Dict[str, Any]] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    matched_genome_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class NarrativeRecommendation(BaseModel):
    """Advisory recommendation describing dramatic pressure/opportunity without puppetry.

    CRITICAL INVARIANT:
    canonical_mutation_allowed MUST ALWAYS be False.
    Narrative recommendations can never directly execute character actions or mutate canonical state.
    """
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(..., description="Unique recommendation ID")
    source_analysis_id: str = Field(..., description="Traceable analysis result ID")
    recommendation_type: str = Field(..., description="Category of dramatic pressure advised")
    dramatic_goal: str = Field(..., description="Dramatic objective of applying this pressure")
    rationale: str = Field(..., description="Explainable reason citing specific events and tension signals")
    target_pressure: str = Field(..., description="Director intervention category or environmental condition")

    relevant_character_ids: List[str] = Field(default_factory=list)
    related_event_ids: List[str] = Field(default_factory=list)
    matched_genome_ids: List[str] = Field(default_factory=list)

    expected_narrative_effect: str = Field(..., description="Projected dramatic change if characters react")
    observed_issue: str = Field(default="", description="Explainable diagnostic finding motivating recommendation")
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Heuristic relevance to dramatic pacing need")
    counter_conditions: List[str] = Field(default_factory=list, description="Conditions under which this recommendation should NOT be applied")
    limitations: List[str] = Field(default_factory=list, description="Operational constraints or known limitations")
    status: RecommendationLifecycleStatus = Field(default=RecommendationLifecycleStatus.PENDING, description="Current lifecycle status")

    # Invariant: Must always be False
    canonical_mutation_allowed: Literal[False] = False
