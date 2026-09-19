"""Performance cue generator for translating hidden subtext and emotion into observable physical behavior.

Show, Don't Tell:
Internal thoughts and unobservable emotions must never be asserted directly in action text.
Hidden conflict, subtext, and stress are translated into concrete, observable physical cues.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.character import Character
from src.domain.world import WorldState
from src.narrative.subtext import SubtextAnalysis, DeceptionClassification


class PerformanceCueType(str, Enum):
    """Observable physical performance beat types."""
    # Phase 6 canonical categories
    EYE_MOVEMENT = "EYE_MOVEMENT"
    PHYSICAL_DISTANCE = "PHYSICAL_DISTANCE"
    GESTURE_TICK = "GESTURE_TICK"
    BREATHING = "BREATHING"
    MICRO_EXPRESSION = "MICRO_EXPRESSION"
    OBJECT_DISPLACEMENT = "OBJECT_DISPLACEMENT"
    VOICE_CRACK = "VOICE_CRACK"
    POSTURE_SHIFT = "POSTURE_SHIFT"

    # Legacy enum values supported for backward compatibility
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


class InternalStateVerbGuard:
    """Validates that action text contains NO unobservable internal verbs. Show, don't tell."""

    FORBIDDEN_VERBS: Tuple[str, ...] = (
        "knows",
        "realizes",
        "feels",
        "remembers",
        "is afraid",
        "decides",
    )

    @classmethod
    def validate_action_text(cls, text: str) -> bool:
        """Return True if text passes guard (contains NO forbidden internal verbs), else False."""
        text_lower = text.lower()
        for forbidden in cls.FORBIDDEN_VERBS:
            pattern = rf"\b{re.escape(forbidden)}\b"
            if re.search(pattern, text_lower):
                return False
        return True

    @classmethod
    def check_and_raise(cls, text: str) -> None:
        """Raise ValueError if text contains forbidden internal verbs."""
        text_lower = text.lower()
        for forbidden in cls.FORBIDDEN_VERBS:
            pattern = rf"\b{re.escape(forbidden)}\b"
            if re.search(pattern, text_lower):
                raise ValueError(
                    f"Action text violates 'Show, Don't Tell' rule. Contains unobservable internal verb: '{forbidden}' in: {text}"
                )


class PerformanceCue(BaseModel):
    """An interpretive physical micro-action grounded in subtext analysis."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"cue_{uuid.uuid4().hex[:8]}")
    character_id: str
    type: PerformanceCueType = PerformanceCueType.MICRO_EXPRESSION
    observable_behaviour: str = ""
    internal_trigger: str = ""
    event_id: str = ""

    # Backward compatibility attributes
    cue_type: Optional[PerformanceCueType] = None
    action_text: str = ""
    parenthetical_text: Optional[str] = None
    derived_from_event_id: Optional[str] = None
    derived_from_actor_state_ids: List[str] = Field(default_factory=list)
    is_performance_cue: bool = True
    focal_object: Optional[str] = None
    gaze_direction_deg: Optional[float] = None
    posture_description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_cue_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # type <-> cue_type
            if "type" in data and "cue_type" not in data:
                data["cue_type"] = data["type"]
            elif "cue_type" in data and "type" not in data:
                data["type"] = data["cue_type"]

            # observable_behaviour <-> action_text
            if "observable_behaviour" in data and "action_text" not in data:
                data["action_text"] = data["observable_behaviour"]
            elif "action_text" in data and "observable_behaviour" not in data:
                data["observable_behaviour"] = data["action_text"]

            # event_id <-> derived_from_event_id
            if "event_id" in data and "derived_from_event_id" not in data:
                data["derived_from_event_id"] = data["event_id"]
            elif "derived_from_event_id" in data and "event_id" not in data:
                data["event_id"] = data["derived_from_event_id"]

            if "internal_trigger" not in data:
                data["internal_trigger"] = data.get("parenthetical_text") or "Subtext tension"
        return data

    @model_validator(mode="after")
    def sync_after(self) -> "PerformanceCue":
        if not self.cue_type:
            object.__setattr__(self, "cue_type", self.type)
        if not self.action_text and self.observable_behaviour:
            object.__setattr__(self, "action_text", self.observable_behaviour)
        if not self.observable_behaviour and self.action_text:
            object.__setattr__(self, "observable_behaviour", self.action_text)
        if not self.derived_from_event_id and self.event_id:
            object.__setattr__(self, "derived_from_event_id", self.event_id)
        if not self.event_id and self.derived_from_event_id:
            object.__setattr__(self, "event_id", self.derived_from_event_id)
        return self


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
                cue_type = PerformanceCueType.EYE_MOVEMENT
                action_text = f"{name}'s gaze flicks involuntarily toward {focal_obj}."
                gaze_deg = 12.0
                posture = "guarded turn"
            else:
                cue_type = PerformanceCueType.EYE_MOVEMENT
                action_text = f"{name} looks away, jaw set tight."
                gaze_deg = 45.0
                posture = "rigid"

        elif primary == DeceptionClassification.DEFLECTING:
            cue_type = PerformanceCueType.POSTURE_SHIFT
            action_text = f"{name} shifts weight, arms crossing defensively."
            parenthetical = "deflecting" if not prefer_action else None
            posture = "arms crossed"

        elif primary == DeceptionClassification.CONCEALING:
            cue_type = PerformanceCueType.MICRO_EXPRESSION
            action_text = f"{name}'s jaw tightens. A beat of calculated stillness."
            posture = "unyielding stillness"

        elif primary == DeceptionClassification.EVASIVE:
            if emotions.fear > 0.5:
                cue_type = PerformanceCueType.GESTURE_TICK
                action_text = f"{name} swallows hard before answering."
                posture = "slight backstep"
            else:
                cue_type = PerformanceCueType.EYE_MOVEMENT
                action_text = f"{name} looks past the question, studying the floor."
                gaze_deg = -30.0

        elif primary == DeceptionClassification.HALF_TRUTH:
            cue_type = PerformanceCueType.BREATHING
            action_text = f"{name} hesitates for a fraction of a second, measuring words."
            parenthetical = "guarded" if not prefer_action else None

        elif primary == DeceptionClassification.MISDIRECTING:
            cue_type = PerformanceCueType.PHYSICAL_DISTANCE
            action_text = f"{name} gestures casually away, creating distance."
            posture = "distancing posture"

        elif primary == DeceptionClassification.THREATENING:
            cue_type = PerformanceCueType.VOICE_CRACK
            action_text = f"{name} steps forward, voice dropping to a low razor edge."
            posture = "looming forward stance"

        elif primary == DeceptionClassification.MANIPULATIVE:
            cue_type = PerformanceCueType.MICRO_EXPRESSION
            action_text = f"{name} forces a calm, disarming smile that doesn't reach the eyes."
            posture = "open yet tense"

        elif primary == DeceptionClassification.VULNERABLE:
            cue_type = PerformanceCueType.BREATHING
            action_text = f"{name} lets the silence hang, breathing shallowly."
            posture = "defensive slouch"

        else:  # TRUTHFUL
            if emotions.fear > 0.6:
                cue_type = PerformanceCueType.VOICE_CRACK
                action_text = f"{name}'s words tumble out with nervous speed."
            elif emotions.anger > 0.6:
                cue_type = PerformanceCueType.MICRO_EXPRESSION
                action_text = f"{name}'s eyes flash with restrained fury."
            else:
                cue_type = PerformanceCueType.EYE_MOVEMENT
                action_text = f"{name} holds steady eye contact."
                posture = "neutral upright"

        # Show, don't tell verification: Every generated action text must pass InternalStateVerbGuard
        InternalStateVerbGuard.check_and_raise(action_text)

        # Track history to ensure variety
        self._cue_history.append(cue_type)
        if len(self._cue_history) > 10:
            self._cue_history.pop(0)

        trigger_desc = analysis.underlying_motive or f"Subtext motive: {primary.value}"

        return PerformanceCue(
            character_id=character.id,
            type=cue_type,
            observable_behaviour=action_text,
            internal_trigger=trigger_desc,
            event_id=source_event_id or "",
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
