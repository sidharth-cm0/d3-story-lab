"""Performance cue generator for translating hidden subtext and emotion into observable physical behavior.

Generates subtle, cinematic physical cues:
- avoids eye contact
- hesitates
- swallows
- tightens jaw
- forces a smile
- glances toward object
- shifts weight
- steps backward
- folds arms
- grips object tighter
- interrupts
- lowers voice
- speaks too quickly
- lets silence hang

Crucial Rule:
Prefers action beats over parentheticals to prevent repetitive stacking.
Stores explicit provenance marking cues as interpretive performance, NOT canonical world events.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from src.domain.character import Character
from src.domain.world import WorldState
from src.narrative.subtext import SubtextAnalysis, DeceptionClassification


class PerformanceCueType(str, Enum):
    """Observable physical performance beat types."""
    AVOIDS_EYE_CONTACT = "avoids_eye_contact"
    HESITATES = "hesitates"
    SWALLOWS = "swallows"
    TIGHTENS_JAW = "tightens_jaw"
    FORCES_SMILE = "forces_smile"
    GLANCES_TOWARD_OBJECT = "glances_toward_object"
    SHIFTS_WEIGHT = "shifts_weight"
    STEPS_BACKWARD = "steps_backward"
    FOLDS_ARMS = "folds_arms"
    GRIPS_OBJECT_TIGHTER = "grips_object_tighter"
    INTERRUPTS = "interrupts"
    LOWERS_VOICE = "lowers_voice"
    SPEAKS_TOO_QUICKLY = "speaks_too_quickly"
    LETS_SILENCE_HANG = "lets_silence_hang"


class PerformanceCue(BaseModel):
    """An interpretive physical micro-action grounded in subtext analysis."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"cue_{uuid.uuid4().hex[:8]}")
    character_id: str
    cue_type: PerformanceCueType
    action_text: str
    parenthetical_text: Optional[str] = None
    derived_from_event_id: Optional[str] = None
    derived_from_actor_state_ids: List[str] = Field(default_factory=list)
    is_performance_cue: bool = True
    focal_object: Optional[str] = None
    gaze_direction_deg: Optional[float] = None
    posture_description: Optional[str] = None


class PerformanceCueGenerator:
    """Generates subtle, grounded physical acting beats from actor subtext and emotion."""

    def __init__(self) -> None:
        self._cue_history: List[PerformanceCueType] = []

    def generate_cue(
        self,
        analysis: SubtextAnalysis,
        character: Character,
        world: WorldState,
        source_event_id: Optional[str] = None,
        prefer_action: bool = True,
        social_tension: float = 0.5,
    ) -> PerformanceCue:
        """Derive an observable physical cue from subtext and emotional pressure."""
        primary = analysis.primary_classification
        emotions = character.emotional_state
        name = character.name
        focal_obj = analysis.conflict_focus_object or "the door"

        # Determine actor state IDs for provenance
        actor_state_ids = [
            f"char_{character.id}",
            f"emo_f{int(emotions.fear*100)}_a{int(emotions.anger*100)}_t{int(emotions.trust*100)}",
        ]
        if character.secrets:
            actor_state_ids.extend([f"sec_{s}" for s in character.secrets[:2]])

        cue_type: PerformanceCueType
        action_text: str
        parenthetical: Optional[str] = None
        gaze_deg: Optional[float] = None
        posture: Optional[str] = None

        if primary == DeceptionClassification.LYING:
            if focal_obj:
                cue_type = PerformanceCueType.GLANCES_TOWARD_OBJECT
                action_text = f"{name}'s gaze flicks involuntarily toward {focal_obj}."
                gaze_deg = 12.0
                posture = "guarded turn"
            else:
                cue_type = PerformanceCueType.AVOIDS_EYE_CONTACT
                action_text = f"{name} looks away, jaw set tight."
                gaze_deg = 45.0
                posture = "rigid"

        elif primary == DeceptionClassification.DEFLECTING:
            cue_type = PerformanceCueType.SHIFTS_WEIGHT
            action_text = f"{name} shifts weight, arms crossing defensively."
            parenthetical = "deflecting" if not prefer_action else None
            posture = "arms crossed"

        elif primary == DeceptionClassification.CONCEALING:
            cue_type = PerformanceCueType.TIGHTENS_JAW
            action_text = f"{name}'s jaw tightens. A beat of calculated stillness."
            posture = "unyielding stillness"

        elif primary == DeceptionClassification.EVASIVE:
            if emotions.fear > 0.5:
                cue_type = PerformanceCueType.SWALLOWS
                action_text = f"{name} swallows hard before answering."
                posture = "slight backstep"
            else:
                cue_type = PerformanceCueType.AVOIDS_EYE_CONTACT
                action_text = f"{name} looks past the question, studying the floor."
                gaze_deg = -30.0

        elif primary == DeceptionClassification.HALF_TRUTH:
            cue_type = PerformanceCueType.HESITATES
            action_text = f"{name} hesitates for a fraction of a second, measuring words."
            parenthetical = "guarded" if not prefer_action else None

        elif primary == DeceptionClassification.MISDIRECTING:
            cue_type = PerformanceCueType.STEPS_BACKWARD
            action_text = f"{name} gestures casually away, creating distance."
            posture = "distancing posture"

        elif primary == DeceptionClassification.THREATENING:
            cue_type = PerformanceCueType.LOWERS_VOICE
            action_text = f"{name} steps forward, voice dropping to a low razor edge."
            posture = "looming forward stance"

        elif primary == DeceptionClassification.MANIPULATIVE:
            cue_type = PerformanceCueType.FORCES_SMILE
            action_text = f"{name} forces a calm, disarming smile that doesn't reach the eyes."
            posture = "open yet tense"

        elif primary == DeceptionClassification.VULNERABLE:
            cue_type = PerformanceCueType.LETS_SILENCE_HANG
            action_text = f"{name} lets the silence hang, breathing shallowly."
            posture = "defensive slouch"

        else:  # TRUTHFUL
            if emotions.fear > 0.6:
                cue_type = PerformanceCueType.SPEAKS_TOO_QUICKLY
                action_text = f"{name}'s words tumble out with nervous speed."
            elif emotions.anger > 0.6:
                cue_type = PerformanceCueType.TIGHTENS_JAW
                action_text = f"{name}'s eyes flash with restrained fury."
            else:
                cue_type = PerformanceCueType.HESITATES
                action_text = f"{name} holds steady eye contact."
                posture = "neutral upright"

        # Track history to ensure variety
        self._cue_history.append(cue_type)
        if len(self._cue_history) > 10:
            self._cue_history.pop(0)

        return PerformanceCue(
            character_id=character.id,
            cue_type=cue_type,
            action_text=action_text,
            parenthetical_text=parenthetical,
            derived_from_event_id=source_event_id,
            derived_from_actor_state_ids=actor_state_ids,
            is_performance_cue=True,
            focal_object=focal_obj,
            gaze_direction_deg=gaze_deg,
            posture_description=posture,
        )
