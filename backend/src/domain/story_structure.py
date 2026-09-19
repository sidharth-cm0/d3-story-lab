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
from typing import Dict, List, Optional, Any, Literal, Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class NarrativeAxis(str, Enum):
    """The three orthogonal narrative axes."""
    MACRO = "MACRO"
    BEAT = "BEAT"
    FRAMING = "FRAMING"


class MacroStructure(str, Enum):
    """Macro dramatic narrative structures."""
    THREE_ACT = "three_act"
    KISHOTENKETSU = "kishotenketsu"
    FREYTAG = "freytag"
    STORY_CIRCLE = "story_circle"
    HEROS_JOURNEY = "heros_journey"


class BeatFramework(str, Enum):
    """Beat sheet frameworks."""
    SAVE_THE_CAT = "save_the_cat"
    FREYTAG_BEATS = "freytag_beats"
    STORY_CIRCLE_STATIONS = "story_circle_stations"
    VIRGINS_PROMISE = "virgins_promise"


class FramingStrategy(str, Enum):
    """Presentation / framing strategies. Note: IN_MEDIAS_RES is framing, never macro."""
    CHRONOLOGICAL = "chronological"
    IN_MEDIAS_RES = "in_medias_res"
    FLASHBACK = "flashback"
    INTERCUT = "intercut"
    PARALLEL_ACTION = "parallel_action"
    REVEAL_DELAY = "reveal_delay"


MACRO_STRUCTURES: Tuple[str, ...] = tuple(m.value for m in MacroStructure)
BEAT_FRAMEWORKS: Tuple[str, ...] = tuple(b.value for b in BeatFramework)
FRAMING_STRATEGIES: Tuple[str, ...] = tuple(f.value for f in FramingStrategy)


def normalize_beat_framework(name: str) -> str:
    """Normalize beat framework identifier, collapsing aliases such as fifteen_beat."""
    cleaned = name.strip().lower()
    if cleaned == "fifteen_beat":
        return BeatFramework.SAVE_THE_CAT.value
    return cleaned


def normalize_structure_id(structure_id: str) -> str:
    """Normalize any structure ID, collapsing aliases such as fifteen_beat."""
    cleaned = structure_id.strip().lower()
    if cleaned == "fifteen_beat":
        return BeatFramework.SAVE_THE_CAT.value
    return cleaned


class CompatibilityVerdict(str, Enum):
    """Verdict for structure pairing compatibility."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    REJECT = "REJECT"


# Single shared dramatic function vocabulary reusable by Scene Builder
class DramaticFunction(str, Enum):
    """Shared dramatic function vocabulary across structures, beats, and scenes."""
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


DRAMATIC_FUNCTIONS: Tuple[str, ...] = tuple(d.value for d in DramaticFunction)

# ScenePurpose and ScenePurposeType are exact 1:1 aliases to DramaticFunction ensuring single shared vocabulary
ScenePurpose = DramaticFunction
ScenePurposeType = DramaticFunction


class SceneLinkType(str, Enum):
    """Causal classification for scene transitions."""
    THEREFORE = "THEREFORE"
    BUT = "BUT"
    AND_THEN = "AND_THEN"
    MEANWHILE = "MEANWHILE"


class CausalTransitionType(str, Enum):
    """Causal progression between scenes or major beats."""
    BUT_THEREFORE = "BUT_THEREFORE"  # High dramatic causation (conflict creates consequence)
    THEREFORE = "THEREFORE"
    BUT = "BUT"
    AND_THEN = "AND_THEN"            # Weak / sequential causation
    MEANWHILE = "MEANWHILE"          # Concurrent different-location scene
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


class SceneObjective(BaseModel):
    """Core emotional objective and observational dynamics for a scene's POV character."""
    model_config = ConfigDict(extra="ignore")

    pov_character_id: str
    wants: str
    emotional_want: str
    obstacle: str
    tactics: List[str] = Field(default_factory=list)
    outcome: Literal["ACHIEVED", "DENIED", "PARTIAL", "ACHIEVED_AT_COST"] = "PARTIAL"
    state_delta: Dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility attributes matching CoreEmotionalObjective
    focal_character_id: Optional[str] = None
    immediate_desire: Optional[str] = None
    immediate_obstacle: Optional[str] = None
    emotional_shift: Optional[str] = None
    stakes_at_risk: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "focal_character_id" in data and "pov_character_id" not in data:
                data["pov_character_id"] = data["focal_character_id"]
            if "immediate_desire" in data and "wants" not in data:
                data["wants"] = data["immediate_desire"]
            if "immediate_obstacle" in data and "obstacle" not in data:
                data["obstacle"] = data["immediate_obstacle"]
            if "emotional_shift" in data and "emotional_want" not in data:
                data["emotional_want"] = data["emotional_shift"]
        return data

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> "SceneObjective":
        if not self.focal_character_id:
            self.focal_character_id = self.pov_character_id
        if not self.immediate_desire:
            self.immediate_desire = self.wants
        if not self.immediate_obstacle:
            self.immediate_obstacle = self.obstacle
        if not self.emotional_shift:
            self.emotional_shift = self.emotional_want
        if not self.stakes_at_risk:
            self.stakes_at_risk = f"Outcome: {self.outcome}"
        return self


# Backward-compatible alias / subclass
class CoreEmotionalObjective(SceneObjective):
    """Scene-level emotional driver for the focal character (backward compatible wrapper)."""
    pass


class Scene(BaseModel):
    """Canonical narrative scene grouping contiguous events."""
    model_config = ConfigDict(extra="ignore")

    scene_id: str
    location_id: str
    time_context: str = "CONTINUOUS"
    characters_present: List[str] = Field(default_factory=list)
    source_event_ids: List[str] = Field(default_factory=list)
    purpose: DramaticFunction = DramaticFunction.SETUP
    objective: Optional[SceneObjective] = None
    turning_point_event_id: Optional[str] = None
    outcome: Literal["ACHIEVED", "DENIED", "PARTIAL", "ACHIEVED_AT_COST", "STATIC"] = "PARTIAL"
    chronological_position: int = 1
    presentation_position: int = 1
    is_static: bool = False

    # Additional metadata and backward compatibility fields with SceneData
    scene_number: Optional[int] = None
    location_name: str = ""
    heading: str = ""
    scene_purpose: Optional[DramaticFunction] = None
    core_emotional_objective: Optional[SceneObjective] = None
    source_beat_id: Optional[str] = None
    start_tick: int = 0
    end_tick: int = 0
    dramatic_tension: float = 50.0
    framing_type: str = "chronological"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    subtext_analyses: List[Any] = Field(default_factory=list)
    performance_cues: List[Any] = Field(default_factory=list)
    character_arcs: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sync_scene_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "scene_purpose" in data and "purpose" not in data:
                data["purpose"] = data["scene_purpose"]
            elif "purpose" in data and "scene_purpose" not in data:
                data["scene_purpose"] = data["purpose"]
            if "core_emotional_objective" in data and "objective" not in data:
                data["objective"] = data["core_emotional_objective"]
            elif "objective" in data and "core_emotional_objective" not in data:
                data["core_emotional_objective"] = data["objective"]
            if "scene_number" in data and "chronological_position" not in data:
                data["chronological_position"] = data["scene_number"]
            elif "chronological_position" in data and "scene_number" not in data:
                data["scene_number"] = data["chronological_position"]
            if "presentation_position" not in data and "chronological_position" in data:
                data["presentation_position"] = data["chronological_position"]
        return data

    @model_validator(mode="after")
    def sync_scene_after(self) -> "Scene":
        if self.scene_number is None:
            self.scene_number = self.chronological_position
        if self.scene_purpose is None:
            self.scene_purpose = self.purpose
        if self.core_emotional_objective is None:
            self.core_emotional_objective = self.objective
        # Phase 5A requirement: presentation_position MUST equal chronological_position
        self.presentation_position = self.chronological_position
        return self


# SceneData is an exact alias for Scene ensuring seamless backward compatibility
SceneData = Scene



class SceneLink(BaseModel):
    """Causal progression link between two sequential scenes backed by typed evidence."""
    model_config = ConfigDict(extra="ignore")

    from_scene_id: str
    to_scene_id: str
    type: SceneLinkType
    evidence_event_ids: List[str] = Field(default_factory=list)
    rationale: str = ""


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

    overall_causal_score: float = Field(default=50.0, description="Normalized causality score 0 - 100")
    but_therefore_ratio: float = Field(default=0.0, description="Ratio of But/Therefore transitions")
    and_then_count: int = 0
    but_therefore_count: int = 0
    total_transitions: int = 0
    transitions: List[CausalTransitionReport] = Field(default_factory=list)
    pressure_recommendation: Optional[str] = None

    # Phase 5B SceneLink metrics
    scene_links: List[SceneLink] = Field(default_factory=list)
    therefore_count: int = 0
    but_count: int = 0
    meanwhile_count: int = 0
    total_scene_links: int = 0
    and_then_ratio: float = 0.0
    consecutive_and_then_runs: List[List[str]] = Field(default_factory=list)


class ArcClassification(str, Enum):
    """Classification of character transformation trajectory across simulation history."""
    POSITIVE_CHANGE = "POSITIVE_CHANGE"
    FALL = "FALL"
    FLAT_TESTING = "FLAT_TESTING"
    DISILLUSIONMENT = "DISILLUSIONMENT"
    NO_ARC_DETECTED = "NO_ARC_DETECTED"


class TurningPoint(BaseModel):
    """A turning point event contributing to a character's arc transformation."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    delta_magnitude: float
    description: str
    tick: Optional[int] = None
    state_change_type: Optional[str] = None


class CharacterArcTurn(BaseModel):
    """Observational record of a turning point for a character (legacy compatibility wrapper)."""
    model_config = ConfigDict(extra="ignore")

    tick: int
    event_id: str
    turn_description: str
    emotional_state_before: Dict[str, float] = Field(default_factory=dict)
    emotional_state_after: Dict[str, float] = Field(default_factory=dict)
    belief_delta: Optional[str] = None
    relationship_delta: Optional[str] = None


class CharacterArc(BaseModel):
    """Observational character arc tracker grounded in StateSnapshotDiffer state and causal events."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    classification: ArcClassification = ArcClassification.NO_ARC_DETECTED
    starting_state: Dict[str, Any] = Field(default_factory=dict)
    ending_state: Dict[str, Any] = Field(default_factory=dict)
    turning_points: List[TurningPoint] = Field(default_factory=list)
    evidence_event_ids: List[str] = Field(default_factory=list)
    reason_if_none: Optional[str] = None

    # Backward compatibility attributes matching legacy CharacterArcReport
    character_name: str = ""
    arc_trajectory: str = "OBSERVED_STABLE"
    major_decisions: List[str] = Field(default_factory=list)
    key_turns: List[CharacterArcTurn] = Field(default_factory=list)
    relationship_deltas: Dict[str, str] = Field(default_factory=dict)
    is_observed_only: bool = True

    @model_validator(mode="before")
    @classmethod
    def sync_legacy_arc(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "arc_trajectory" in data and "classification" not in data:
                traj = str(data["arc_trajectory"])
                if traj in ArcClassification.__members__:
                    data["classification"] = ArcClassification(traj)
                elif "DISILLUSIONMENT" in traj:
                    data["classification"] = ArcClassification.DISILLUSIONMENT
                elif traj in ("TRANSFORMATION", "REVELATION"):
                    data["classification"] = ArcClassification.POSITIVE_CHANGE
                elif traj in ("FALL", "DESCENT"):
                    data["classification"] = ArcClassification.FALL
                elif traj == "OBSERVED_STABLE":
                    data["classification"] = ArcClassification.NO_ARC_DETECTED
            elif "classification" in data and "arc_trajectory" not in data:
                val = data["classification"]
                data["arc_trajectory"] = val.value if hasattr(val, "value") else str(val)
        return data

    @model_validator(mode="after")
    def sync_legacy_after(self) -> "CharacterArc":
        if not self.arc_trajectory or self.arc_trajectory == "OBSERVED_STABLE":
            self.arc_trajectory = str(self.classification.value if hasattr(self.classification, "value") else self.classification)
        if not self.evidence_event_ids and self.turning_points:
            self.evidence_event_ids = [tp.event_id for tp in self.turning_points]
        return self


# Backward compatibility alias
CharacterArcReport = CharacterArc
