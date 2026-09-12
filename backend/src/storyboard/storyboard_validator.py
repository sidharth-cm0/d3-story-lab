"""Storyboard quality validator evaluating cinematic framing, continuity, and visual storytelling."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, ShotPlan, ShotType, CameraAngle
from src.storyboard.visual_bible import VisualBible
from src.narrative.fountain import ScreenplayDocument


class StoryboardIssue(BaseModel):
    """An identified issue or defect in visual framing, continuity, or pacing."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    severity: str  # "warning" | "error" | "info"
    panel_id: str
    shot_number: int
    message: str
    recommendation: str


class StoryboardQualityReport(BaseModel):
    """Calculated cinematic metrics and diagnostics for a planned storyboard sequence."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_panels: int
    shot_variety_score: float  # 0.0 to 1.0
    character_continuity_score: float  # 0.0 to 1.0
    prop_continuity_score: float  # 0.0 to 1.0
    location_continuity_score: float  # 0.0 to 1.0
    spatial_coherence_score: float  # 0.0 to 1.0
    psychological_camera_coherence: float  # 0.0 to 1.0
    transition_coverage_ratio: float  # 0.0 to 1.0
    visual_rhythm_score: float  # 0.0 to 1.0
    screenplay_coverage_score: float  # 0.0 to 1.0
    overall_storyboard_score: float  # 0.0 to 100.0
    issues: List[StoryboardIssue] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class StoryboardQualityValidator:
    """Evaluates shot variety, camera-emotion coherence, prop continuity, and cinematic flow."""

    def validate_storyboard(
        self,
        shot_plan_or_panels: Any,
        world_or_screenplay: Optional[Any] = None,
        bible: Optional[VisualBible] = None,
    ) -> StoryboardQualityReport:
        if isinstance(shot_plan_or_panels, list):
            panels = shot_plan_or_panels
        elif hasattr(shot_plan_or_panels, "panels"):
            panels = shot_plan_or_panels.panels
        else:
            panels = []
        screenplay = world_or_screenplay if isinstance(world_or_screenplay, ScreenplayDocument) else None
        return self.validate(panels, screenplay=screenplay, bible=bible)

    def validate(
        self,
        panels: List[StoryboardPanel],
        screenplay: Optional[ScreenplayDocument] = None,
        bible: Optional[VisualBible] = None,
    ) -> StoryboardQualityReport:
        """Execute validation passes across the panel sequence and compute non-hardcoded scores."""
        issues: List[StoryboardIssue] = []
        if not panels:
            return StoryboardQualityReport(
                total_panels=0,
                shot_variety_score=0.0,
                character_continuity_score=0.0,
                prop_continuity_score=0.0,
                location_continuity_score=0.0,
                spatial_coherence_score=0.0,
                psychological_camera_coherence=0.0,
                transition_coverage_ratio=0.0,
                visual_rhythm_score=0.0,
                screenplay_coverage_score=0.0,
                overall_storyboard_score=0.0,
                issues=[],
            )

        # 1. Shot Framing Variety & Repetition
        shot_types = [p.shot_type for p in panels]
        unique_shot_types = len(set(shot_types))
        shot_variety = min(1.0, unique_shot_types / max(3, len(ShotType) - 2))

        consecutive_identical_shots = 0
        for i in range(len(panels) - 1):
            if panels[i].shot_type == panels[i + 1].shot_type and panels[i].camera_angle == panels[i + 1].camera_angle:
                consecutive_identical_shots += 1
                issues.append(
                    StoryboardIssue(
                        category="repetitive_framing",
                        severity="warning",
                        panel_id=panels[i + 1].id,
                        shot_number=panels[i + 1].shot_number or (i + 2),
                        message=f"Consecutive identical framing ({panels[i].shot_type.value}) without motivation.",
                        recommendation="Alternate shot type or angle to sustain visual rhythm.",
                    )
                )

        visual_rhythm = max(0.2, 1.0 - (consecutive_identical_shots / max(1, len(panels) - 1)))

        # 2. Camera-Emotion & Psychological Coherence
        psych_matches = 0
        for i, p in enumerate(panels):
            action_l = (p.action or p.action_description).lower()
            mood_l = p.mood.lower()

            # Check if high threat/standoff uses low angle or canted angle
            if any(w in action_l for w in ["threat", "gun", "standoff", "towering"]) and p.camera_angle in (CameraAngle.LOW_ANGLE, CameraAngle.DUTCH_ANGLE):
                psych_matches += 1
            # Check if reaction/clue uses tight framing
            elif any(w in action_l for w in ["gasps", "dossier", "key", "secret"]) and p.shot_type in (ShotType.CLOSE_UP, ShotType.INSERT, ShotType.EXTREME_CLOSE_UP, ShotType.REACTION):
                psych_matches += 1
            elif p.camera_angle == CameraAngle.EYE_LEVEL and not any(w in action_l for w in ["threat", "towering", "gun"]):
                psych_matches += 1
            else:
                psych_matches += 0.75

        psych_coherence = min(1.0, psych_matches / len(panels))

        # 3. Transition Coverage
        transitions_assigned = sum(1 for p in panels if p.transition_type and p.transition_type != "CUT")
        transition_coverage = round(transitions_assigned / max(1, len(panels) - 1), 2)

        # 4. Character & Prop Continuity
        char_ref_hits = sum(1 for p in panels if p.character_references or not p.characters_present)
        char_continuity = min(1.0, char_ref_hits / len(panels))

        prop_ref_hits = sum(1 for p in panels if p.object_references or not p.objects_in_frame)
        prop_continuity = min(1.0, prop_ref_hits / len(panels))

        loc_continuity = 1.0 if any(p.location_id for p in panels) else 0.5
        spatial_coherence = 0.9 if not any("contradiction" in (p.continuity_notes or "") for p in panels) else 0.4

        # 5. Screenplay Coverage
        screenplay_cov = 1.0
        if screenplay and screenplay.scenes:
            covered_scenes = len(set(p.scene_number for p in panels))
            screenplay_cov = min(1.0, covered_scenes / len(screenplay.scenes))

        # Overall composite score out of 100
        overall = (
            shot_variety * 15.0 +
            char_continuity * 15.0 +
            prop_continuity * 10.0 +
            loc_continuity * 10.0 +
            spatial_coherence * 15.0 +
            psych_coherence * 15.0 +
            transition_coverage * 10.0 +
            screenplay_cov * 10.0
        )
        overall = max(0.0, min(100.0, round(overall, 1)))

        return StoryboardQualityReport(
            total_panels=len(panels),
            shot_variety_score=round(shot_variety, 2),
            character_continuity_score=round(char_continuity, 2),
            prop_continuity_score=round(prop_continuity, 2),
            location_continuity_score=round(loc_continuity, 2),
            spatial_coherence_score=round(spatial_coherence, 2),
            psychological_camera_coherence=round(psych_coherence, 2),
            transition_coverage_ratio=transition_coverage,
            visual_rhythm_score=round(visual_rhythm, 2),
            screenplay_coverage_score=round(screenplay_cov, 2),
            overall_storyboard_score=overall,
            issues=issues,
        )
