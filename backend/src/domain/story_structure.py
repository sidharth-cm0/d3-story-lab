"""Story Structure Library, Blueprint, and Causal Models for D3 Story Lab.

Enforces:
1. STRUCTURE WITHOUT PUPPETRY:
   - StoryBlueprint provides soft constraints, expected dramatic functions, and pressure signals.
   - It NEVER forces dialogue, forced actions, or hidden scripts onto autonomous characters.
2. NO RETROACTIVE CANONICAL REWRITE:
   - Causal analysis, Arc tracking, and Structure analysis interpret immutable history without mutating it.
3. Backward schema compatibility with schema_version support.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class StoryStructureType(str, Enum):
    """Primary dramatic narrative structures."""
    THREE_ACT = "THREE_ACT"
    HERO_JOURNEY = "HERO_JOURNEY"
    FREYTAG = "FREYTAG"
    SAVE_THE_CAT = "SAVE_THE_CAT"
    STORY_CIRCLE = "STORY_CIRCLE"
    KISHOTENKETSU = "KISHOTENKETSU"


class PresentationStrategy(str, Enum):
    """Presentation / framing strategies. Note: IN_MEDIAS_RES is presentation, NOT primary structure."""
    CHRONOLOGICAL = "CHRONOLOGICAL"
    IN_MEDIAS_RES = "IN_MEDIAS_RES"
    FLASHBACK = "FLASHBACK"
    INTERCUT = "INTERCUT"
    PARALLEL_ACTION = "PARALLEL_ACTION"
    REVEAL_DELAY = "REVEAL_DELAY"


class StructureSelectionMode(str, Enum):
    """How the story structure was selected."""
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class ScenePurposeType(str, Enum):
    """Dramatic purpose of an individual scene."""
    SETUP = "SETUP"
    INVESTIGATION = "INVESTIGATION"
    DISCOVERY = "DISCOVERY"
    NEGOTIATION = "NEGOTIATION"
    CONFRONTATION = "CONFRONTATION"
    ESCALATION = "ESCALATION"
    REVERSAL = "REVERSAL"
    CHASE = "CHASE"
    REVELATION = "REVELATION"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"


class CausalTransitionType(str, Enum):
    """Causal progression between scenes or major beats."""
    BUT_THEREFORE = "BUT_THEREFORE"  # High dramatic causation (conflict creates consequence)
    AND_THEN = "AND_THEN"            # Weak / sequential causation
    COINCIDENCE = "COINCIDENCE"      # External disruption
    DISCONNECTED = "DISCONNECTED"    # Non-sequitur


class BeatDefinition(BaseModel):
    """A soft beat expectation in a dramatic structure."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    beat_id: str
    name: str
    act: str
    target_position_pct: float = Field(..., description="Target normalized position 0.0 - 1.0")
    expected_dramatic_function: str = Field(..., description="Soft dramatic expectation (e.g. status quo disruption)")
    pressure_signal: str = Field(..., description="Pacing and obstacle recommendation for Director")
    description: str


class StructureDefinition(BaseModel):
    """Complete specification of a dramatic structure."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    structure_type: StoryStructureType
    display_name: str
    description: str
    genre_affinities: List[str] = Field(default_factory=list)
    tone_affinities: List[str] = Field(default_factory=list)
    conflict_types: List[str] = Field(default_factory=list)
    beats: List[BeatDefinition] = Field(default_factory=list)
    compatible_secondary_structures: List[StoryStructureType] = Field(default_factory=list)


class StructureSelectionResult(BaseModel):
    """Result of analyzing input and selecting story structure."""
    model_config = ConfigDict(extra="ignore")

    primary_structure: StoryStructureType
    fit_score: float = Field(..., description="Normalized heuristic suitability score 0-100 (never statistical probability)")
    fit_rationale: str
    secondary_structure: Optional[StoryStructureType] = None
    candidate_scores: Dict[str, float] = Field(default_factory=dict)
    selection_mode: StructureSelectionMode = StructureSelectionMode.AUTO


class StoryBlueprint(BaseModel):
    """Soft narrative blueprint setting expected dramatic shape without puppetry."""
    model_config = ConfigDict(extra="ignore")

    story_title: str
    primary_structure: StoryStructureType
    secondary_structure: Optional[StoryStructureType] = None
    presentation_strategy: PresentationStrategy = PresentationStrategy.CHRONOLOGICAL
    theme: str
    dramatic_question: str
    stakes: str
    expected_beats: List[BeatDefinition] = Field(default_factory=list)
    soft_constraints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CoreEmotionalObjective(BaseModel):
    """Scene-level emotional driver for the focal character."""
    model_config = ConfigDict(extra="ignore")

    focal_character_id: str
    immediate_desire: str = Field(..., description="What the focal character urgently wants right now")
    immediate_obstacle: str = Field(..., description="What or who currently stands in the way")
    emotional_shift: str = Field(..., description="Expected or realized emotional transition in scene")
    stakes_at_risk: str = Field(..., description="What is at stake in this immediate interaction")


class SceneData(BaseModel):
    """First-class scene structure with emotional objective and purpose."""
    model_config = ConfigDict(extra="ignore")

    scene_id: str
    scene_number: int
    location_id: str
    location_name: str
    heading: str
    scene_purpose: ScenePurposeType
    core_emotional_objective: Optional[CoreEmotionalObjective] = None
    source_event_ids: List[str] = Field(default_factory=list)
    source_beat_id: Optional[str] = None
    characters_present: List[str] = Field(default_factory=list)
    start_tick: int = 0
    end_tick: int = 0
    dramatic_tension: float = 50.0
    chronological_position: int = 1
    presentation_position: int = 1
    framing_type: str = "chronological"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CausalTransitionReport(BaseModel):
    """Causal progression assessment between two consecutive narrative units."""
    model_config = ConfigDict(extra="ignore")

    from_id: str
    to_id: str
    transition_type: CausalTransitionType
    score: float = Field(..., description="Causality score between 0.0 and 1.0")
    rationale: str
    tension_delta: float = 0.0


class CausalContinuitySummary(BaseModel):
    """Overall causal coherence of simulation events without retroactive canonical modification."""
    model_config = ConfigDict(extra="ignore")

    overall_causal_score: float = Field(..., description="Normalized causality score 0 - 100")
    but_therefore_ratio: float = Field(..., description="Ratio of But/Therefore transitions")
    and_then_count: int = 0
    but_therefore_count: int = 0
    total_transitions: int = 0
    transitions: List[CausalTransitionReport] = Field(default_factory=list)
    pressure_recommendation: Optional[str] = None


class CharacterArcTurn(BaseModel):
    """Observational record of a turning point for a character."""
    model_config = ConfigDict(extra="ignore")

    tick: int
    event_id: str
    turn_description: str
    emotional_state_before: Dict[str, float] = Field(default_factory=dict)
    emotional_state_after: Dict[str, float] = Field(default_factory=dict)
    belief_delta: Optional[str] = None
    relationship_delta: Optional[str] = None


class CharacterArcReport(BaseModel):
    """Observational character arc tracker without mutation capability."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    character_name: str
    starting_state: Dict[str, Any] = Field(default_factory=dict)
    major_decisions: List[str] = Field(default_factory=list)
    key_turns: List[CharacterArcTurn] = Field(default_factory=list)
    relationship_deltas: Dict[str, str] = Field(default_factory=dict)
    ending_state: Dict[str, Any] = Field(default_factory=dict)
    arc_trajectory: str = "OBSERVED_STABLE"
    is_observed_only: bool = True  # strictly read-only
