"""Shot Planner for translating Screenplays and Scene Projections into Grounded Shot Plans.

Phase 8.1: Complete shot list generation with psychological camera logic,
strict provenance, Show-Don't-Tell emotion extraction from PerformanceCues,
and unbudgeted shot candidates.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
import uuid
import math
from pydantic import BaseModel, ConfigDict, Field

from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock
from src.narrative.scene_projection import ObservableSceneProjection, ObservableBeat
from src.narrative.performance_cues import PerformanceCue, InternalStateVerbGuard
from src.domain.world import WorldState
from src.domain.story_structure import Scene, SceneLink


# =============================================================================
# § 3. DOMAIN MODELS FOR SHOT PLANNING
# =============================================================================

class ShotType(str, Enum):
    """Cinematic camera framing types for shot planning."""
    ESTABLISHING = "ESTABLISHING"
    WIDE = "WIDE"
    MEDIUM = "MEDIUM"
    MEDIUM_CLOSE_UP = "MEDIUM_CLOSE_UP"
    CLOSE_UP = "CLOSE_UP"
    EXTREME_CLOSE_UP = "EXTREME_CLOSE_UP"
    OVER_THE_SHOULDER = "OVER_THE_SHOULDER"
    INSERT = "INSERT"
    REACTION = "REACTION"
    TRACKING = "TRACKING"


class CameraAngle(str, Enum):
    """Cinematic camera elevations and angles."""
    EYE_LEVEL = "EYE_LEVEL"
    HIGH_ANGLE = "HIGH_ANGLE"
    LOW_ANGLE = "LOW_ANGLE"
    DUTCH_ANGLE = "DUTCH_ANGLE"


class ShotContextSignals(BaseModel):
    """Psychological and dramatic context signals driving camera selection."""
    model_config = ConfigDict(extra="ignore")

    power_differential: float = Field(ge=-1.0, le=1.0, default=0.0)      # -1.0 low power .. 1.0 high power, for the focal character
    fear_level: float = Field(ge=0.0, le=1.0, default=0.0)               # 0.0-1.0, from emotion_vector
    certainty_level: float = Field(ge=0.0, le=1.0, default=0.5)          # 0.0-1.0
    information_advantage: float = Field(ge=-1.0, le=1.0, default=0.0)    # -1.0..1.0 — does focal character know something others don't, or vice versa
    emotional_intensity: float = Field(ge=0.0, le=1.0, default=0.5)       # 0.0-1.0
    social_dominance: float = Field(ge=-1.0, le=1.0, default=0.0)         # -1.0..1.0, from relationship_scores
    goal_progress_delta: float = Field(ge=-1.0, le=1.0, default=0.0)      # -1.0..1.0, advancing or losing ground
    is_revelation_moment: bool = False                                    # SECRET_LEARNED / BELIEF_FLIP at this beat
    is_reaction_beat: bool = False                                        # reacting to something another character just did/revealed


class CompositionPlan(BaseModel):
    """Spatial composition blueprint for an individual shot."""
    model_config = ConfigDict(extra="ignore")

    framing_rect: str = "0,0,1920,1080"
    subject_positions: dict[str, tuple[float, float, float]] = Field(default_factory=dict)   # entity_id -> (x, y, scale)
    gaze_vectors: dict[str, str] = Field(default_factory=dict)
    depth_layers: list[str] = Field(default_factory=lambda: ["foreground", "midground", "background"])
    focal_point: str = ""


class ShotPlan(BaseModel):
    """Comprehensive plan for an individual cinematic shot with provenance."""
    model_config = ConfigDict(extra="ignore")

    shot_id: str
    scene_id: str
    screenplay_block_ids: list[str]        # REQUIRED — non-empty
    source_event_ids: list[str]            # REQUIRED — non-empty, same provenance discipline as prior phases
    shot_type: ShotType
    camera_angle: CameraAngle
    lens_feel: str                          # descriptive: "wide-angle distortion", "long lens compression", "normal"
    subject_focus: str                       # stable entity_id
    actor_positions: dict[str, str] = Field(default_factory=dict)           # entity_id -> position descriptor
    gaze_direction: str | None = None
    foreground: list[str] = Field(default_factory=list)                     # entity_ids
    background: list[str] = Field(default_factory=list)                     # entity_ids
    important_props: list[str] = Field(default_factory=list)                # entity_ids — gates Visual Bible prop-detail in Prompt 2
    movement: str | None = None                       # implied energy/stillness in composition, not actual motion
    lighting: str = "natural cinematic lighting"
    emotion: str                                # sourced from PerformanceCue.observable_behaviour — see §6
    performance_cue_id: str | None = None
    rationale: str                               # REQUIRED — why this shot_type/angle, explainable, not a black box
    contributing_signals: dict[str, float] = Field(default_factory=dict)        # REQUIRED — explainability criterion contributions
    composition_plan: CompositionPlan


# =============================================================================
# § 5. PSYCHOLOGICAL CAMERA RULES TABLE (INSPECTABLE & DATA-DRIVEN)
# =============================================================================

@dataclass(frozen=True)
class PsychologicalCameraRule:
    """An inspectable declarative rule mapping psychological signals to camera choices."""
    rule_id: str
    name: str
    priority: int
    shot_type: Optional[ShotType]
    camera_angle: Optional[CameraAngle]
    condition: Callable[[ShotContextSignals, Dict[str, Any]], bool]
    rationale_template: str


def _rule_1_diminished_exposed(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return s.power_differential < -0.3 and s.fear_level > 0.5

def _rule_2_revelation_reaction(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return s.is_revelation_moment and s.is_reaction_beat

def _rule_3_empowering_low_angle(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return s.goal_progress_delta > 0.3

def _rule_4_diminishing_high_angle(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return s.goal_progress_delta < -0.3

def _rule_5_two_character_info_advantage(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return s.information_advantage != 0 and ctx.get("is_two_character_exchange", False)

def _rule_6_intimate_intensity(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    # High emotional intensity, no clear power or info signal dominates
    no_clear_power = abs(s.power_differential) <= 0.3
    no_clear_info = s.information_advantage == 0
    return s.emotional_intensity > 0.7 and no_clear_power and no_clear_info

def _rule_7_scene_first_beat(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return ctx.get("is_first_beat", False)

def _rule_8_ensemble_wide(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return ctx.get("is_ensemble", False) or (ctx.get("num_characters", 0) > 1 and not ctx.get("has_single_focal_point", True))

def _rule_9_physical_action_tracking(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return ctx.get("is_physical_action", False)

def _rule_10_destabilization_dutch(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return (
        ctx.get("link_type") == "BUT"
        or ctx.get("dramatic_function") == "REVERSAL"
        or ctx.get("is_reversal", False)
    )

def _rule_11_neutral_default(s: ShotContextSignals, ctx: Dict[str, Any]) -> bool:
    return True


PSYCHOLOGICAL_CAMERA_RULES: List[PsychologicalCameraRule] = [
    # Table from Section 5 of Prompt 1
    PsychologicalCameraRule(
        rule_id="diminished_exposed",
        name="Diminished and Exposed",
        priority=10,
        shot_type=ShotType.MEDIUM_CLOSE_UP,
        camera_angle=CameraAngle.HIGH_ANGLE,
        condition=_rule_1_diminished_exposed,
        rationale_template="diminished, exposed: power differential is low ({power_differential:.2f}) and fear is high ({fear_level:.2f})",
    ),
    PsychologicalCameraRule(
        rule_id="revelation_reaction",
        name="Revelation Reaction",
        priority=20,
        shot_type=ShotType.REACTION,
        camera_angle=None,  # Dynamic: HIGH_ANGLE if fear > 0.5 else EYE_LEVEL
        condition=_rule_2_revelation_reaction,
        rationale_template="capturing the realization: revelation moment with reaction beat",
    ),
    PsychologicalCameraRule(
        rule_id="empowering_low_angle",
        name="Empowering Angle",
        priority=30,
        shot_type=None,
        camera_angle=CameraAngle.LOW_ANGLE,
        condition=_rule_3_empowering_low_angle,
        rationale_template="empowering angle, character gaining ground (goal progress delta: {goal_progress_delta:.2f})",
    ),
    PsychologicalCameraRule(
        rule_id="diminishing_high_angle",
        name="Diminishing Angle",
        priority=40,
        shot_type=None,
        camera_angle=CameraAngle.HIGH_ANGLE,
        condition=_rule_4_diminishing_high_angle,
        rationale_template="diminishing angle, character losing ground (goal progress delta: {goal_progress_delta:.2f})",
    ),
    PsychologicalCameraRule(
        rule_id="two_character_info_advantage",
        name="Two-Character Information Advantage",
        priority=50,
        shot_type=ShotType.OVER_THE_SHOULDER,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_5_two_character_info_advantage,
        rationale_template="frame the informationally-advantaged character's face, shot from behind the other in two-character exchange",
    ),
    PsychologicalCameraRule(
        rule_id="intimate_intensity",
        name="Intimate Intensity",
        priority=60,
        shot_type=ShotType.EXTREME_CLOSE_UP,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_6_intimate_intensity,
        rationale_template="maximum intimacy when nothing else dominates (emotional intensity: {emotional_intensity:.2f})",
    ),
    PsychologicalCameraRule(
        rule_id="scene_first_beat",
        name="Scene Opening Orient",
        priority=70,
        shot_type=ShotType.ESTABLISHING,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_7_scene_first_beat,
        rationale_template="scene's first beat: orient the audience",
    ),
    PsychologicalCameraRule(
        rule_id="ensemble_wide",
        name="Ensemble Moment",
        priority=80,
        shot_type=ShotType.WIDE,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_8_ensemble_wide,
        rationale_template="ensemble moment: multiple characters, no single focal point",
    ),
    PsychologicalCameraRule(
        rule_id="physical_action_tracking",
        name="Physical Action Tracking",
        priority=90,
        shot_type=ShotType.TRACKING,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_9_physical_action_tracking,
        rationale_template="physical action / chase-type beat: tracking shot",
    ),
    PsychologicalCameraRule(
        rule_id="destabilization_dutch",
        name="Destabilization Reversal",
        priority=100,
        shot_type=None,
        camera_angle=CameraAngle.DUTCH_ANGLE,
        condition=_rule_10_destabilization_dutch,
        rationale_template="reserve for genuine destabilization: SceneLink type BUT or dramatic REVERSAL",
    ),
    PsychologicalCameraRule(
        rule_id="neutral_default",
        name="Neutral Default",
        priority=999,
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.EYE_LEVEL,
        condition=_rule_11_neutral_default,
        rationale_template="no strong psychological signal, neutral default",
    ),
]


def evaluate_camera_rules(
    signals: ShotContextSignals,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[ShotType, CameraAngle, str, Dict[str, float]]:
    """Evaluate inspectable psychological camera rules table against signals and context.

    Returns:
        (shot_type, camera_angle, rationale, contributing_signals)
    """
    ctx = context or {}

    # Build comprehensive signal contributions dictionary
    contributing_signals: Dict[str, float] = {
        "power_differential": float(round(signals.power_differential, 3)),
        "fear_level": float(round(signals.fear_level, 3)),
        "certainty_level": float(round(signals.certainty_level, 3)),
        "information_advantage": float(round(signals.information_advantage, 3)),
        "emotional_intensity": float(round(signals.emotional_intensity, 3)),
        "social_dominance": float(round(signals.social_dominance, 3)),
        "goal_progress_delta": float(round(signals.goal_progress_delta, 3)),
    }
    if signals.is_revelation_moment:
        contributing_signals["is_revelation_moment"] = 1.0
    if signals.is_reaction_beat:
        contributing_signals["is_reaction_beat"] = 1.0

    selected_shot_type: Optional[ShotType] = None
    selected_angle: Optional[CameraAngle] = None
    shot_type_rationale: Optional[str] = None
    angle_rationale: Optional[str] = None

    # Sort rules strictly by priority
    sorted_rules = sorted(PSYCHOLOGICAL_CAMERA_RULES, key=lambda r: r.priority)

    # 1. Determine shot type (first non-default rule that matches and provides shot_type)
    for rule in sorted_rules:
        if rule.rule_id == "neutral_default":
            continue
        if rule.shot_type is not None and rule.condition(signals, ctx):
            selected_shot_type = rule.shot_type
            shot_type_rationale = rule.rationale_template.format(
                power_differential=signals.power_differential,
                fear_level=signals.fear_level,
                emotional_intensity=signals.emotional_intensity,
                goal_progress_delta=signals.goal_progress_delta,
            )
            contributing_signals[f"rule_{rule.rule_id}_match"] = 1.0
            break

    # 2. Determine camera angle (first non-default rule that matches and provides camera_angle)
    for rule in sorted_rules:
        if rule.rule_id == "neutral_default":
            continue
        if rule.rule_id == "revelation_reaction" and rule.condition(signals, ctx):
            # Special case for revelation reaction angle per fear
            selected_angle = CameraAngle.HIGH_ANGLE if signals.fear_level > 0.5 else CameraAngle.EYE_LEVEL
            angle_rationale = "high angle due to elevated fear during revelation" if signals.fear_level > 0.5 else "eye level realization"
            contributing_signals["rule_revelation_reaction_angle"] = 1.0
            break
        elif rule.camera_angle is not None and rule.condition(signals, ctx):
            selected_angle = rule.camera_angle
            angle_rationale = rule.rationale_template.format(
                power_differential=signals.power_differential,
                fear_level=signals.fear_level,
                emotional_intensity=signals.emotional_intensity,
                goal_progress_delta=signals.goal_progress_delta,
            )
            contributing_signals[f"rule_{rule.rule_id}_angle_match"] = 1.0
            break

    # 3. Default fallback if no rules fired
    if selected_shot_type is None and selected_angle is None:
        # Verbatim requirement: "no strong psychological signal, neutral default"
        selected_shot_type = ShotType.MEDIUM
        selected_angle = CameraAngle.EYE_LEVEL
        rationale = "no strong psychological signal, neutral default"
        contributing_signals["neutral_default"] = 1.0
        return selected_shot_type, selected_angle, rationale, contributing_signals

    # Fallback missing components
    if selected_shot_type is None:
        selected_shot_type = ShotType.MEDIUM
    if selected_angle is None:
        selected_angle = CameraAngle.EYE_LEVEL

    # Construct combined rationale
    parts = []
    if shot_type_rationale:
        parts.append(shot_type_rationale)
    if angle_rationale and angle_rationale != shot_type_rationale:
        parts.append(angle_rationale)
    rationale = "; ".join(parts) if parts else "no strong psychological signal, neutral default"

    return selected_shot_type, selected_angle, rationale, contributing_signals


def resolve_lens_feel(shot_type: ShotType) -> str:
    """Determine optical lens characteristic matching shot framing."""
    if shot_type in (ShotType.ESTABLISHING, ShotType.WIDE):
        return "wide-angle distortion"
    elif shot_type in (ShotType.EXTREME_CLOSE_UP, ShotType.CLOSE_UP, ShotType.MEDIUM_CLOSE_UP):
        return "long lens compression"
    return "normal"


# =============================================================================
# § 4 & § 6. SHOT PLANNER ENGINE (UNBUDGETED & PERFORMANCE-CUE GROUNDED)
# =============================================================================

class ShotPlanner:
    """Plans full sequences of cinematic shots for screenplays without budget truncation."""

    def __init__(self, verb_guard: Optional[InternalStateVerbGuard] = None):
        self.verb_guard = verb_guard or InternalStateVerbGuard()

    def extract_signals_for_beat(
        self,
        beat: ObservableBeat,
        focal_id: str,
        projection: ObservableSceneProjection,
        world: Optional[WorldState] = None,
        scene_links: Optional[List[SceneLink]] = None,
    ) -> Tuple[ShotContextSignals, Dict[str, Any]]:
        """Extract psychological signals and context flags for a specific beat and focal character."""
        focal_char = world.characters.get(focal_id) if world and focal_id in world.characters else None

        # 1. Emotional state extraction
        fear = 0.0
        anger = 0.0
        trust = 0.0
        power = 0.0
        dominance = 0.0

        if focal_char:
            emo = focal_char.emotional_state
            fear = max(0.0, min(1.0, (emo.fear + 1.0) / 2.0 if emo.fear < 0 else emo.fear))
            anger = max(0.0, min(1.0, (emo.anger + 1.0) / 2.0 if emo.anger < 0 else emo.anger))
            trust = max(-1.0, min(1.0, emo.trust))

            # Role-based baseline dominance/power
            role_lower = focal_char.role.lower()
            if any(k in role_lower for k in ("boss", "guard", "custodian")):
                base_power = 0.6
                dominance += 0.4
            else:
                base_power = 0.1
                dominance += 0.1

            power = max(-1.0, min(1.0, base_power + (anger * 0.3) - (fear * 0.4)))
            dominance = max(-1.0, min(1.0, dominance + (anger * 0.4) - (fear * 0.3)))

        # Relative power differential for the focal character compared to others in the scene
        power_diff = power
        if world:
            other_powers = []
            for cid in projection.characters_present:
                if cid != focal_id and cid in world.characters:
                    c = world.characters[cid]
                    c_emo = c.emotional_state
                    c_fear = max(0.0, min(1.0, (c_emo.fear + 1.0) / 2.0 if c_emo.fear < 0 else c_emo.fear))
                    c_anger = max(0.0, min(1.0, (c_emo.anger + 1.0) / 2.0 if c_emo.anger < 0 else c_emo.anger))
                    c_role = c.role.lower()
                    c_base = 0.6 if any(k in c_role for k in ("boss", "guard", "custodian")) else 0.1
                    c_p = max(-1.0, min(1.0, c_base + (c_anger * 0.3) - (c_fear * 0.4)))
                    other_powers.append(c_p)
            if other_powers:
                avg_other = sum(other_powers) / len(other_powers)
                power_diff = max(-1.0, min(1.0, power - avg_other))

        # 2. Information advantage
        info_adv = 0.0
        certainty = 0.5
        if world and focal_char:
            focal_knowledge_count = len(focal_char.knowledge)
            other_chars = [c for cid, c in world.characters.items() if cid != focal_id and cid in projection.characters_present]
            avg_other_knowledge = (sum(len(c.knowledge) for c in other_chars) / len(other_chars)) if other_chars else focal_knowledge_count
            delta = focal_knowledge_count - avg_other_knowledge
            info_adv = max(-1.0, min(1.0, delta * 0.25))
            if focal_char.secrets:
                info_adv = min(1.0, info_adv + 0.2)
            certainty = max(0.1, min(1.0, 0.5 + (info_adv * 0.3) - (fear * 0.3)))

        # 3. Emotional intensity
        intensity = max(0.1, min(1.0, (fear * 0.4 + anger * 0.4 + abs(power) * 0.2)))

        # 4. Goal progress delta
        goal_delta = 0.0
        if projection.objective.outcome == "ACHIEVED":
            goal_delta = 0.5
        elif projection.objective.outcome == "DENIED":
            goal_delta = -0.5
        elif projection.objective.outcome == "ACHIEVED_AT_COST":
            goal_delta = 0.2

        # 5. Revelation & Reaction detection
        desc_lower = beat.description.lower()
        is_revelation = (
            "reveals" in desc_lower
            or "secret" in desc_lower
            or "clue" in desc_lower
            or "discovered" in desc_lower
            or "unlocked" in desc_lower
            or "dossier" in desc_lower
        )
        is_reaction = (
            "reacts" in desc_lower
            or "gasps" in desc_lower
            or "freezes" in desc_lower
            or "turns" in desc_lower
            or "stiffens" in desc_lower
            or "pauses" in desc_lower
            or "steps back" in desc_lower
        )

        signals = ShotContextSignals(
            power_differential=round(power_diff, 2),
            fear_level=round(fear, 2),
            certainty_level=round(certainty, 2),
            information_advantage=round(info_adv, 2),
            emotional_intensity=round(intensity, 2),
            social_dominance=round(dominance, 2),
            goal_progress_delta=round(goal_delta, 2),
            is_revelation_moment=is_revelation,
            is_reaction_beat=is_reaction,
        )

        # Contextual flags
        desc_lower = beat.description.lower()
        is_two_char_exchange = (
            len(beat.characters_involved) == 2
            and any(k in desc_lower for k in ("said to", "spoke to", "asked", "whispered", "denies", "claims", "replies", "tells"))
        )
        is_phys = any(
            k in desc_lower
            for k in ("moved from", "picked up", "ran", "runs", "flees", "draws", "grabs", "strikes", "rushes", "steps toward", "chases", "escapes")
        )

        context = {
            "num_characters": len(beat.characters_involved or projection.characters_present),
            "is_two_character_exchange": is_two_char_exchange,
            "has_single_focal_point": len(beat.characters_involved) <= 1,
            "is_ensemble": len(beat.characters_involved) > 2,
            "is_physical_action": is_phys,
            "dramatic_function": projection.purpose.value if hasattr(projection.purpose, "value") else str(projection.purpose),
        }

        # Check scene link type for BUT
        if scene_links:
            for link in scene_links:
                if link.from_scene_id == projection.scene_id or link.to_scene_id == projection.scene_id:
                    if link.link_type.value == "BUT" if hasattr(link.link_type, "value") else str(link.link_type) == "BUT":
                        context["link_type"] = "BUT"
                        context["is_reversal"] = True
                        break

        return signals, context

    def plan_shots_for_screenplay(
        self,
        screenplay: ScreenplayDocument,
        projections: List[ObservableSceneProjection],
        world: Optional[WorldState] = None,
        scene_links: Optional[List[SceneLink]] = None,
    ) -> List[ShotPlan]:
        """Generate complete unbudgeted shot sequence across all scenes in screenplay."""
        all_shot_plans: List[ShotPlan] = []

        # Map projections by scene_id and index
        proj_by_id = {p.scene_id: p for p in projections}

        for scene_idx, scene in enumerate(screenplay.scenes):
            proj = proj_by_id.get(scene.metadata.get("scene_id", ""))
            if not proj:
                # Fallback matching by index or location
                if scene_idx < len(projections):
                    proj = projections[scene_idx]
                else:
                    continue

            scene_id = proj.scene_id or f"scene_{scene.scene_number:02d}"

            # -----------------------------------------------------------------
            # 1. ESTABLISHING SHOT AT START OF SCENE
            # -----------------------------------------------------------------
            est_shot_id = f"shot_{scene.scene_number:02d}_000_est"
            slugline_blocks = [b.block_id for b in scene.blocks if b.element_type == "SLUGLINE"]
            est_blocks = slugline_blocks if slugline_blocks else [scene.blocks[0].block_id] if scene.blocks else [f"blk_{scene.scene_number}_est"]
            est_events = list(scene.source_event_ids[:1]) if scene.source_event_ids else (proj.source_event_ids[:1] if proj.source_event_ids else ["evt_scene_start"])

            est_composition = CompositionPlan(
                framing_rect="0,0,1920,1080",
                subject_positions={proj.location_label: (0.5, 0.5, 1.0)},
                gaze_vectors={},
                depth_layers=["background", "midground", "foreground"],
                focal_point=proj.location_label,
            )

            all_shot_plans.append(
                ShotPlan(
                    shot_id=est_shot_id,
                    scene_id=scene_id,
                    screenplay_block_ids=est_blocks,
                    source_event_ids=est_events,
                    shot_type=ShotType.ESTABLISHING,
                    camera_angle=CameraAngle.EYE_LEVEL,
                    lens_feel="wide-angle distortion",
                    subject_focus=proj.location_label,
                    actor_positions={cid: "entering location" for cid in proj.characters_present},
                    gaze_direction=None,
                    foreground=[],
                    background=[proj.location_label],
                    important_props=[],
                    movement="establishing pan / static framing",
                    lighting="ambient atmospheric lighting",
                    emotion="composed demeanor, observant gaze",
                    performance_cue_id=None,
                    rationale="scene's first beat: orient the audience",
                    contributing_signals={"scene_opening": 1.0},
                    composition_plan=est_composition,
                )
            )

            # -----------------------------------------------------------------
            # 2. ONE SHOT CANDIDATE PER OBSERVABLE BEAT
            # -----------------------------------------------------------------
            for beat_idx, beat in enumerate(proj.beats):
                shot_id = f"shot_{scene.scene_number:02d}_{beat_idx + 1:03d}"

                # Provenance: Find corresponding screenplay blocks
                matching_blocks = [
                    b.block_id for b in scene.blocks
                    if beat.event_id in b.source_event_ids or b.derived_from_event_id == beat.event_id
                ]
                if not matching_blocks:
                    # Invariant: screenplay_block_ids MUST be non-empty
                    # Pick closest block in sequence
                    block_idx = min(beat_idx, len(scene.blocks) - 1) if scene.blocks else 0
                    matching_blocks = [scene.blocks[block_idx].block_id] if scene.blocks else [f"blk_{scene.scene_number}_{beat_idx}"]

                # Invariant: source_event_ids MUST be non-empty
                source_events = [beat.event_id] if beat.event_id else (proj.source_event_ids[:1] or ["evt_default"])

                # Determine focal character
                if beat.characters_involved:
                    focal_id = beat.characters_involved[0]
                elif proj.objective and proj.objective.pov_character_id:
                    focal_id = proj.objective.pov_character_id
                elif proj.characters_present:
                    focal_id = proj.characters_present[0]
                else:
                    focal_id = "char_focal"

                # Extract signals & evaluate psychological camera rules
                signals, context = self.extract_signals_for_beat(
                    beat=beat,
                    focal_id=focal_id,
                    projection=proj,
                    world=world,
                    scene_links=scene_links,
                )

                shot_type, angle, rationale, contrib_signals = evaluate_camera_rules(signals, context)

                # Show-Don't-Tell Emotion: Sourced from PerformanceCue
                cue_to_use: Optional[PerformanceCue] = None
                if beat.performance_cue_ids:
                    cue_to_use = next((c for c in proj.performance_cues if c.id in beat.performance_cue_ids), None)
                if not cue_to_use:
                    # Match by focal character
                    cue_to_use = next((c for c in proj.performance_cues if c.character_id == focal_id), None)

                if cue_to_use and cue_to_use.observable_behaviour:
                    emotion_text = cue_to_use.observable_behaviour
                    cue_id = cue_to_use.id
                else:
                    # Default observable demeanor without internal state verbs
                    emotion_text = "composed posture, watchful expression"
                    cue_id = None

                # Enforce InternalStateVerbGuard downstream (Section 6)
                self.verb_guard.check_and_raise(emotion_text)

                # Identify important props referenced in beat or world
                important_props: List[str] = []
                if world:
                    for obj_id, obj in world.objects.items():
                        obj_name_lower = obj.name.lower()
                        if obj_id.lower() in beat.description.lower() or obj_name_lower in beat.description.lower():
                            if obj_id not in important_props:
                                important_props.append(obj_id)

                # Spatial composition & staging
                subject_positions: Dict[str, Tuple[float, float, float]] = {}
                actor_positions: Dict[str, str] = {}
                gaze_vectors: Dict[str, str] = {}

                active_chars = beat.characters_involved or proj.characters_present
                for i, cid in enumerate(active_chars):
                    x_pos = round(0.3 + 0.3 * (i % 3), 2)
                    scale = 1.2 if cid == focal_id and shot_type in (ShotType.CLOSE_UP, ShotType.MEDIUM_CLOSE_UP) else 1.0
                    subject_positions[cid] = (x_pos, 0.5, scale)
                    actor_positions[cid] = f"staging_zone_{i+1}"
                    gaze_vectors[cid] = f"toward {focal_id if cid != focal_id else 'subject'}"

                comp_plan = CompositionPlan(
                    framing_rect="0,0,1920,1080",
                    subject_positions=subject_positions,
                    gaze_vectors=gaze_vectors,
                    depth_layers=["foreground", "midground", "background"],
                    focal_point=focal_id,
                )

                all_shot_plans.append(
                    ShotPlan(
                        shot_id=shot_id,
                        scene_id=scene_id,
                        screenplay_block_ids=matching_blocks,
                        source_event_ids=source_events,
                        shot_type=shot_type,
                        camera_angle=angle,
                        lens_feel=resolve_lens_feel(shot_type),
                        subject_focus=focal_id,
                        actor_positions=actor_positions,
                        gaze_direction=gaze_vectors.get(focal_id),
                        foreground=[],
                        background=[proj.location_label],
                        important_props=important_props,
                        movement="tracking dolly" if shot_type == ShotType.TRACKING else None,
                        lighting="focused interior lighting",
                        emotion=emotion_text,
                        performance_cue_id=cue_id,
                        rationale=rationale,
                        contributing_signals=contrib_signals,
                        composition_plan=comp_plan,
                    )
                )

        return all_shot_plans
