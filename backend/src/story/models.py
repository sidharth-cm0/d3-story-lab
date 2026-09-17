"""Story Structure Engine and Blueprint domain models."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Literal, Any
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.story_structure import (
    DramaticFunction,
    DRAMATIC_FUNCTIONS,
    NarrativeAxis,
    MacroStructure,
    BeatFramework,
    FramingStrategy,
    MACRO_STRUCTURES,
    BEAT_FRAMEWORKS,
    FRAMING_STRATEGIES,
    CompatibilityVerdict,
    normalize_beat_framework,
    normalize_structure_id,
)

# §A.5 PredicateClause & PredicateSpec
class PredicateClause(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal[
        "GOAL_ADOPTED",
        "BELIEF_FLIP",
        "POSSESSION_CHANGE",
        "RELATIONSHIP_THRESHOLD_CROSSED",
        "SECRET_LEARNED",
        "WORLD_FACT_CHANGED",
    ]
    subject: Optional[str] = None      # symbolic or literal proposition/subject ref
    object: Optional[str] = None       # symbolic or literal object ref
    character: Optional[str] = None    # optional: restrict to a role ("protagonist") or literal character_id
    threshold: Optional[float] = None  # for RELATIONSHIP_THRESHOLD_CROSSED


class PredicateSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    any_of: Optional[List[PredicateClause]] = None
    all_of: Optional[List[PredicateClause]] = None

    @model_validator(mode="after")
    def validate_any_xor_all(self) -> "PredicateSpec":
        has_any = self.any_of is not None
        has_all = self.all_of is not None
        if has_any and has_all:
            raise ValueError("PredicateSpec must specify exactly one of 'any_of' or 'all_of', not both")
        if not has_any and not has_all:
            raise ValueError("PredicateSpec must specify at least one of 'any_of' or 'all_of'")
        return self


# §A.4 Structure definitions as data
class ActDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    position: Tuple[float, float]  # [start, end] normalized 0.0 - 1.0


class BeatSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    dramatic_function: DramaticFunction
    window: Tuple[float, float]
    required: bool = True
    satisfaction: PredicateSpec
    name: Optional[str] = None
    description: Optional[str] = None


class StoryStructureDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    axis: Literal["MACRO", "BEAT", "FRAMING"]
    display_name: str
    description: Optional[str] = None
    acts: Optional[List[ActDefinition]] = None
    stages: Optional[List[ActDefinition]] = None
    beats: List[BeatSpec] = Field(default_factory=list)
    compatible_beat_frameworks: List[str] = Field(default_factory=list)
    affinity: Dict[str, float] = Field(default_factory=dict)
    affinity_rules: Optional[Dict[str, float]] = None
    disqualifiers: List[str] = Field(default_factory=list)
    manual_only: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # collapse fifteen_beat into save_the_cat
            raw_id = str(data.get("id", "")).strip().lower()
            if raw_id == "fifteen_beat":
                data["id"] = "save_the_cat"
            # virgins_promise is manual-only, excluded from auto scoring
            if raw_id == "virgins_promise":
                data["manual_only"] = True
            # support stages as acts
            if "stages" in data and "acts" not in data:
                data["acts"] = data["stages"]
            # support affinity_rules as affinity
            if "affinity_rules" in data and "affinity" not in data:
                data["affinity"] = data["affinity_rules"]
        return data

    @model_validator(mode="after")
    def validate_rules(self) -> "StoryStructureDefinition":
        # Rule: in_medias_res is FRAMING, never MACRO
        if self.id.lower() == "in_medias_res" and self.axis == "MACRO":
            raise ValueError("in_medias_res is FRAMING, never MACRO")
        if self.id == "virgins_promise" and not self.manual_only:
            self.manual_only = True
        return self


# §A.7 StoryFeatures
class StoryFeatures(BaseModel):
    model_config = ConfigDict(extra="ignore")

    input_position: Literal["BEGINNING", "MIDPOINT", "ENDING", "FULL_CONCEPT", "SOURCE_MATERIAL"] = "BEGINNING"
    genre_signals: List[str] = Field(default_factory=list)
    protagonist_count: int = 1
    conflict_axis: Literal["INTERNAL", "EXTERNAL", "SOCIAL"] = "EXTERNAL"
    transformation_expected: bool = True
    withheld_information_present: bool = False
    return_to_origin: bool = False
    ensemble: bool = False
    tone: str = "dramatic"
    scope: Literal["INTIMATE", "LOCAL", "EPIC"] = "LOCAL"
    timespan: Literal["SINGLE_SCENE", "HOURS", "DAYS", "YEARS"] = "HOURS"
    ending_known: bool = False
    moral_polarity: float = 0.0  # -1.0 .. 1.0
    twist_or_juxtaposition_driven: bool = False
    material_driver: Literal["CONFLICT_ESCALATION", "TWIST_JUXTAPOSITION"] = "CONFLICT_ESCALATION"

    @model_validator(mode="before")
    @classmethod
    def sync_material_driver_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("twist_or_juxtaposition_driven") and "material_driver" not in data:
                data["material_driver"] = "TWIST_JUXTAPOSITION"
            elif data.get("material_driver") == "TWIST_JUXTAPOSITION" and "twist_or_juxtaposition_driven" not in data:
                data["twist_or_juxtaposition_driven"] = True
        return data

    @model_validator(mode="after")
    def validate_material_driver(self) -> "StoryFeatures":
        if self.twist_or_juxtaposition_driven:
            self.material_driver = "TWIST_JUXTAPOSITION"
        elif self.material_driver == "TWIST_JUXTAPOSITION":
            self.twist_or_juxtaposition_driven = True
        return self


# §A.8 Rubric scoring models
class StructureCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    structure_id: str
    fit_score: float                              # 0.0–1.0
    criterion_contributions: Dict[str, float]     # REQUIRED — no black-box number
    disqualified: bool = False
    disqualifier_reasons: List[str] = Field(default_factory=list)


class StructureSelection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    primary_macro: str
    beat_layer: Optional[str] = None
    framing: str = "chronological"
    candidates: List[StructureCandidate] = Field(default_factory=list)
    selection_mode: Literal["AUTO", "MANUAL"] = "AUTO"
    overridden_by_user: bool = False


# §B.1 - §B.6 Phase 4 models
class CanonFact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    proposition_id: str      # references a Proposition seeded with enforced=True
    source_span: str         # traceable back to the user's input text
    role_tag: Optional[str] = None     # e.g. "protagonist_identity", "focal_object" — feeds StoryRoleBindings


class NarrativeIntent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = "Untitled"
    logline: str = ""
    genre: str = "Drama"
    tone: str = "Neutral"
    theme: str = ""
    dramatic_question: str = ""
    central_conflict: str = ""
    stakes: str = ""
    expected_arc_direction: str = "TRANSFORMATIVE"


class StoryRoleBindings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protagonist_character_id: Optional[str] = None
    antagonist_character_id: Optional[str] = None
    central_proposition_id: Optional[str] = None
    focal_object_id: Optional[str] = None


# §B.5 Allowed Director Intervention types
DirectorIntervention = Literal[
    "INTRODUCE_OBSTACLE",
    "CHANGE_DOOR_STATE",
    "MOVE_NPC",
    "REVEAL_CLUE",
    "ANNOUNCE_DEADLINE",
    "ENVIRONMENTAL_EVENT",
    "INCREASE_TIME_PRESSURE",
]

ALLOWED_DIRECTOR_INTERVENTIONS: Tuple[str, ...] = (
    "INTRODUCE_OBSTACLE",
    "CHANGE_DOOR_STATE",
    "MOVE_NPC",
    "REVEAL_CLUE",
    "ANNOUNCE_DEADLINE",
    "ENVIRONMENTAL_EVENT",
    "INCREASE_TIME_PRESSURE",
)


class BeatPressure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beat_id: str
    dramatic_function: DramaticFunction
    target_window: Tuple[float, float]        # normalized [0,1] position
    satisfaction_predicate: PredicateSpec      # resolved, per §B.3
    escalation_ladder: List[DirectorIntervention] = Field(default_factory=list)
    status: Literal["PENDING", "SATISFIED", "PARTIAL", "UNSATISFIED"] = "PENDING"
    deviation_note: Optional[str] = None
    unevaluable: bool = False
    required: bool = True
    satisfaction_tick: Optional[int] = None


class StoryBlueprint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    canon: List[CanonFact] = Field(default_factory=list)           # HARD — validator-enforced
    intent: NarrativeIntent = Field(default_factory=NarrativeIntent) # SOFT — evaluated, never enforced
    beats: List[BeatPressure] = Field(default_factory=list)
    structure: StructureSelection
    role_bindings: Optional[StoryRoleBindings] = None


class SufficiencyReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    required_beats_satisfied: bool
    climax_detected: bool
    arc_detected: bool
    unsatisfied_beats: List[BeatPressure] = Field(default_factory=list)
    recommendation: Literal[
        "CONTINUE", "ADJUST_PRESSURE_AND_CONTINUE", "PROCEED", "HALT_INSUFFICIENT"
    ]
    reason: str
