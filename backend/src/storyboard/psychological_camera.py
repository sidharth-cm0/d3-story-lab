"""Psychological camera planner mapping character internal states to cinematic framing."""

from __future__ import annotations
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import ShotType, CameraAngle, ShotPurpose
from src.domain.character import Character
from src.narrative.subtext import SubtextAnalysis, DeceptionClassification


class PsychologicalState(BaseModel):
    """Dynamic psychological scores driving camera placement."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    power: float = Field(ge=-1.0, le=1.0, default=0.0)
    fear: float = Field(ge=0.0, le=1.0, default=0.0)
    certainty: float = Field(ge=0.0, le=1.0, default=0.5)
    information_advantage: float = Field(ge=-1.0, le=1.0, default=0.0)
    goal_progress: float = Field(ge=0.0, le=1.0, default=0.5)
    social_dominance: float = Field(ge=-1.0, le=1.0, default=0.0)
    emotional_intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    relationship_shift: float = Field(ge=-1.0, le=1.0, default=0.0)


class CinematicShotRecommendation(BaseModel):
    """Recommended camera framing, elevation, and movement derived from character psychology."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    shot_type: ShotType
    camera_angle: CameraAngle
    camera_movement: str  # "STATIC", "PUSH IN", "DOLLY OUT", "TRACK ->", "PAN ->", "DUTCH TILT", "HANDHELD"
    dutch_angle_deg: float = 0.0
    lens_feel: str
    composition_guide: str
    psychological_rationale: str


class PsychologicalCameraPlanner:
    """Computes sophisticated cinematic framing from actor internal states rather than flat 1:1 maps."""

    @staticmethod
    def derive_psychological_state(
        character: Optional[Character],
        subtext: Optional[SubtextAnalysis] = None,
        opponent: Optional[Character] = None,
    ) -> PsychologicalState:
        """Calculate normalized psychological vector from character emotional and social attributes."""
        if not character:
            return PsychologicalState()

        emo = character.emotional_state
        fear = max(0.0, min(1.0, (emo.fear + 1.0) / 2.0 if emo.fear < 0 else emo.fear))
        anger = max(0.0, min(1.0, (emo.anger + 1.0) / 2.0 if emo.anger < 0 else emo.anger))
        trust = max(-1.0, min(1.0, emo.trust))

        power = 0.0
        dominance = 0.0
        if "boss" in character.role.lower() or "guard" in character.role.lower():
            power = 0.6
            dominance = 0.5
        elif "undercover" in character.role.lower() or "detective" in character.role.lower():
            power = 0.2
            dominance = 0.1

        # Adjust based on fear vs anger
        power = max(-1.0, min(1.0, power + (anger * 0.4) - (fear * 0.5)))
        dominance = max(-1.0, min(1.0, dominance + (anger * 0.5) - (fear * 0.4)))

        # Information advantage and certainty
        info_adv = 0.0
        certainty = 0.5
        if character.secrets:
            info_adv += 0.4
        if subtext:
            if DeceptionClassification.LYING in subtext.classifications or DeceptionClassification.CONCEALING in subtext.classifications:
                info_adv += 0.3
                certainty -= 0.2  # Dissonance creates uncertainty
            elif DeceptionClassification.THREATENING in subtext.classifications:
                dominance = min(1.0, dominance + 0.4)

        intensity = max(0.1, min(1.0, (fear * 0.4 + anger * 0.4 + abs(power) * 0.2)))

        return PsychologicalState(
            power=round(power, 2),
            fear=round(fear, 2),
            certainty=round(certainty, 2),
            information_advantage=round(info_adv, 2),
            goal_progress=0.5,
            social_dominance=round(dominance, 2),
            emotional_intensity=round(intensity, 2),
            relationship_shift=round(-0.3 if emo.trust < 0 else 0.2, 2),
        )

    def plan_camera(
        self,
        psych_state: PsychologicalState,
        action_text: str,
        shot_purpose: ShotPurpose,
        last_shot_type: Optional[ShotType] = None,
        core_emotional_objective: Optional[Dict[str, Any]] = None,
    ) -> CinematicShotRecommendation:
        """Determine camera framing, elevation, and movement from psychological state and purpose."""
        act_lower = action_text.lower()

        # 1. Sudden Realization / Shock / Revelation
        if shot_purpose in (ShotPurpose.REVELATION, ShotPurpose.REACTION) or any(w in act_lower for w in ["gasps", "stares", "realizes", "shock", "freeze"]):
            rec = CinematicShotRecommendation(
                shot_type=ShotType.CLOSE_UP,
                camera_angle=CameraAngle.DUTCH_ANGLE if psych_state.certainty < 0.4 else CameraAngle.EYE_LEVEL,
                camera_movement="PUSH IN",
                dutch_angle_deg=-6.0 if psych_state.certainty < 0.4 else 0.0,
                lens_feel="50mm prime, razor-sharp eye highlight",
                composition_guide="Off-center reaction framing with dramatic negative space",
                psychological_rationale="Sudden psychological shift; rapid push in conveys realization.",
            )

        # 2. Clue / Object Insert
        elif shot_purpose in (ShotPurpose.CLUE, ShotPurpose.DISCOVERY) or any(w in act_lower for w in ["dossier", "key", "ledger", "safe", "drawer", "lock"]):
            rec = CinematicShotRecommendation(
                shot_type=ShotType.INSERT,
                camera_angle=CameraAngle.HIGH_ANGLE if psych_state.power < 0 else CameraAngle.EYE_LEVEL,
                camera_movement="PUSH IN",
                lens_feel="85mm macro, ultra-shallow focal depth",
                composition_guide="Tight isolation on focal prop with hand interaction",
                psychological_rationale="Tight focal emphasis on objective evidence; narrowing audience focus.",
            )

        # 3. High Dominance / High Information Advantage -> Controlled Low-Angle Medium
        elif psych_state.social_dominance > 0.3 and psych_state.power > 0.2:
            rec = CinematicShotRecommendation(
                shot_type=ShotType.MEDIUM,
                camera_angle=CameraAngle.LOW_ANGLE,
                camera_movement="STATIC",
                lens_feel="35mm cinematic standard, imposing vertical horizon",
                composition_guide="Low architectural angle emphasizing physical dominance",
                psychological_rationale="Low angle conveys authority, dominance, and intimidation.",
            )

        # 4. Low Power / High Fear / Low Certainty -> Slightly High-Angle Medium Close-Up
        elif psych_state.power < -0.2 and psych_state.fear > 0.5:
            rec = CinematicShotRecommendation(
                shot_type=ShotType.CLOSE_UP,
                camera_angle=CameraAngle.HIGH_ANGLE,
                camera_movement="DOLLY OUT",
                lens_feel="40mm prime, compressed depth",
                composition_guide="Slight high angle placing character beneath ceiling rafters",
                psychological_rationale="High angle diminishes subject, reinforcing vulnerability and claustrophobia.",
            )

        # 5. Betrayal / Evasion / High Deception -> Dutch Angle or Canted Framing
        elif psych_state.certainty < 0.35 or any(w in act_lower for w in ["deflect", "lie", "denies", "evades", "betray"]):
            rec = CinematicShotRecommendation(
                shot_type=ShotType.MEDIUM,
                camera_angle=CameraAngle.DUTCH_ANGLE,
                camera_movement="TRACK ->",
                dutch_angle_deg=8.0,
                lens_feel="35mm anamorphic, canted horizon",
                composition_guide="Diagonal tilt throwing room perspective off balance",
                psychological_rationale="Canted Dutch angle communicates psychological imbalance and deception.",
            )

        # 6. Action / Pursuit -> Dynamic Tracking
        elif shot_purpose in (ShotPurpose.ACTION, ShotPurpose.CLIMAX) or any(w in act_lower for w in ["sprint", "run", "pursue", "shoot", "detonate"]):
            rec = CinematicShotRecommendation(
                shot_type=ShotType.MEDIUM,
                camera_angle=CameraAngle.LOW_ANGLE if psych_state.power >= 0 else CameraAngle.HIGH_ANGLE,
                camera_movement="TRACK ->",
                lens_feel="28mm wide action lens, motion vector streaks",
                composition_guide="Dynamic diagonal axis cutting across frame",
                psychological_rationale="Kinetic tracking reinforces velocity and urgent stakes.",
            )

        # Default standard dialogue / scene coverage
        else:
            shot_t = ShotType.CLOSE_UP if last_shot_type == ShotType.MEDIUM else ShotType.MEDIUM
            rec = CinematicShotRecommendation(
                shot_type=shot_t,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_movement="STATIC",
                lens_feel="50mm portrait standard",
                composition_guide="Rule of thirds framing, balanced chiaroscuro negative space",
                psychological_rationale="Balanced eye-level intimacy allowing actor micro-performance to register.",
            )

        if core_emotional_objective:
            desire = core_emotional_objective.get("immediate_desire")
            obstacle = core_emotional_objective.get("immediate_obstacle")
            need = core_emotional_objective.get("internal_need")
            clauses = []
            if desire:
                clauses.append(f"pursuing '{desire}'")
            if obstacle:
                clauses.append(f"confronting '{obstacle}'")
            if need:
                clauses.append(f"need for '{need}'")
            if clauses:
                enriched_rationale = f"{rec.psychological_rationale} Reflects focal objective: {', '.join(clauses)}."
                return CinematicShotRecommendation(
                    shot_type=rec.shot_type,
                    camera_angle=rec.camera_angle,
                    camera_movement=rec.camera_movement,
                    dutch_angle_deg=rec.dutch_angle_deg,
                    lens_feel=rec.lens_feel,
                    composition_guide=rec.composition_guide,
                    psychological_rationale=enriched_rationale,
                )

        return rec
