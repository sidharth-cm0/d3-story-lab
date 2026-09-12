"""Storyboard Prompt Compiler and Continuity Validator.

Transforms high-level narrative actions and visual bibles into structured,
reproducible image generation prompts and validates visual continuity across panels.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle, ShotPurpose
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile


class ContinuityIssue(BaseModel):
    """A detected continuity anomaly or visual rhythm warning."""
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    severity: str  # "warning" | "info" | "error"
    category: str  # "shot_variety" | "character_wardrobe" | "prop_tracking" | "lighting"
    message: str
    suggestion: str


class ContinuityReport(BaseModel):
    """Comprehensive continuity and visual rhythm evaluation of a shot plan."""
    model_config = ConfigDict(extra="ignore")

    score: float = 1.0  # 0.0 to 1.0
    is_valid: bool = True
    total_panels: int = 0
    issues: List[ContinuityIssue] = Field(default_factory=list)
    shot_variety_score: float = 1.0
    character_consistency_score: float = 1.0
    prop_tracking_score: float = 1.0


class StoryboardPromptCompiler:
    """Compiles multi-layered, highly detailed prompts for graphic novel storyboard generation."""

    def __init__(self, style_profile: Optional[StoryboardStyleProfile] = None):
        self.style_profile = style_profile or StoryboardStyleProfile()

    def compile_panel_prompt(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
    ) -> str:
        """Construct a structured cinematic graphic novel illustration prompt."""
        profile = bible.style_profile if bible else self.style_profile

        # 1. Medium and Aesthetic Foundation
        style_header = profile.prompt_prefix()

        # 2. Camera Framing, Lens & Composition
        shot_str = panel.shot_type.value.replace("_", " ").title()
        angle_str = panel.camera_angle.value.replace("_", " ").title()
        lens = panel.lens_feel or "35mm cinematic lens"
        comp = panel.composition or "Dynamic graphic novel framing with dramatic chiaroscuro diagonals"
        camera_section = f"Camera framing: {shot_str} shot at {angle_str}, {lens}. Composition: {comp}."

        # 3. Environment & Setting
        loc_desc = panel.location_name
        if bible and panel.location_id in bible.locations:
            loc_ref = bible.locations[panel.location_id]
            loc_desc = loc_ref.prompt_snippet()
        elif panel.location_reference:
            loc_desc = panel.location_reference
        env_section = f"Setting: {loc_desc}."

        # 4. Characters & Continuity Wardrobe
        chars_desc: List[str] = []
        if panel.character_names:
            for name in panel.character_names:
                found_ref = None
                if bible:
                    for cid, cref in bible.characters.items():
                        if cref.name.lower() == name.lower() or cid in panel.characters_present:
                            found_ref = cref
                            break
                if found_ref:
                    chars_desc.append(found_ref.prompt_snippet())
                elif panel.character_references.get(name):
                    chars_desc.append(f"{name}: {panel.character_references[name]}")
                else:
                    chars_desc.append(f"{name} in sharp dark noir silhouette")
        characters_section = f"Characters in scene: {'; '.join(chars_desc)}." if chars_desc else "Environment shot, no characters visible."

        # 5. Prominent Props & Objects
        props_desc: List[str] = []
        if panel.objects_in_frame:
            for obj_name in panel.objects_in_frame:
                found_obj = None
                if bible:
                    for oid, oref in bible.objects.items():
                        if oref.name.lower() == obj_name.lower():
                            found_obj = oref
                            break
                if found_obj:
                    props_desc.append(found_obj.prompt_snippet())
                elif panel.object_references.get(obj_name):
                    props_desc.append(f"{obj_name}: {panel.object_references[obj_name]}")
                else:
                    props_desc.append(f"{obj_name} with defined graphic edges")
        props_section = f"Key objects visible: {', '.join(props_desc)}." if props_desc else ""

        # 6. Narrative Action & Expression
        action_text = panel.action_description or panel.action
        focus = f" Focus point: {panel.subject_focus}." if panel.subject_focus else ""
        action_section = f"Depicted Incident: {action_text}.{focus}"

        # 7. Lighting & Atmosphere
        lighting_desc = panel.lighting or "Low-key chiaroscuro with sharp rim highlights and deep velvety shadows"
        mood_desc = panel.mood or "Suspenseful, tense, dramatic"
        lighting_section = f"Lighting & Atmosphere: {lighting_desc}, mood is {mood_desc}."

        # 8. Render Constraints
        constraints_section = "Illustration only. Graphic novel inked panel art. Absolutely no speech text, no subtitles, no speech balloons inside artwork."

        parts = [
            style_header,
            camera_section,
            env_section,
            characters_section,
        ]
        if props_section:
            parts.append(props_section)
        parts.extend([
            action_section,
            lighting_section,
            constraints_section,
        ])

        return " ".join(parts)

    def compile_negative_prompt(
        self,
        panel: Optional[StoryboardPanel] = None,
        bible: Optional[VisualBible] = None,
    ) -> str:
        """Generate comprehensive negative constraints to prevent common artifacts."""
        profile = bible.style_profile if bible else self.style_profile
        base_negative = profile.negative_constraints
        if panel and panel.negative_prompt:
            return f"{base_negative}, {panel.negative_prompt}"
        return base_negative


class ContinuityValidator:
    """Validates visual and rhythm continuity across a sequence of storyboard panels."""

    @classmethod
    def validate_shot_plan(
        cls,
        panels: List[StoryboardPanel],
        bible: Optional[VisualBible] = None,
    ) -> ContinuityReport:
        """Examine panels for monotonous framing, sudden lighting shifts, or missing continuity."""
        issues: List[ContinuityIssue] = []
        if not panels:
            return ContinuityReport(score=1.0, is_valid=True, total_panels=0)

        # 1. Check Shot Framing Variety / Visual Rhythm
        # Avoid 3 or more consecutive panels with the identical shot_type
        consecutive_same_type = 1
        for i in range(1, len(panels)):
            if panels[i].shot_type == panels[i - 1].shot_type:
                consecutive_same_type += 1
                if consecutive_same_type >= 3:
                    issues.append(
                        ContinuityIssue(
                            panel_id=panels[i].panel_id or panels[i].id,
                            severity="warning",
                            category="shot_variety",
                            message=f"Monotonous framing: 3 consecutive {panels[i].shot_type.value} shots.",
                            suggestion="Vary camera framing (e.g. switch to CLOSE-UP, REACTION, or INSERT).",
                        )
                    )
            else:
                consecutive_same_type = 1

        # 2. Check Character Continuity
        # Ensure characters mentioned in panel have reference entries in the visual bible
        char_issues_count = 0
        if bible:
            bible_char_names = {c.name.lower() for c in bible.characters.values()}
            for panel in panels:
                for cname in panel.character_names:
                    if cname.lower() not in bible_char_names and cname.lower() not in ["protagonist", "counterpart"]:
                        char_issues_count += 1
                        issues.append(
                            ContinuityIssue(
                                panel_id=panel.panel_id or panel.id,
                                severity="info",
                                category="character_wardrobe",
                                message=f"Character '{cname}' does not have a formal Visual Bible turnaround reference.",
                                suggestion=f"Add visual profile for '{cname}' in Visual Bible to guarantee wardrobe continuity.",
                            )
                        )

        # 3. Check Prop Tracking
        # If an object was in action, check that it's tracked in objects_in_frame
        prop_issues_count = 0
        for panel in panels:
            action_lower = (panel.action + " " + (panel.dialogue_excerpt or "")).lower()
            for key_prop in ["dossier", "ledger", "transceiver", "safe", "key", "revolver", "phone"]:
                if key_prop in action_lower and not any(key_prop in obj.lower() for obj in panel.objects_in_frame):
                    prop_issues_count += 1
                    issues.append(
                        ContinuityIssue(
                            panel_id=panel.panel_id or panel.id,
                            severity="info",
                            category="prop_tracking",
                            message=f"Narrative action mentions '{key_prop}' but it is not formally tracked in objects_in_frame.",
                            suggestion=f"Include '{key_prop}' in panel.objects_in_frame for targeted visual prompt injection.",
                        )
                    )

        # Calculate scores
        total = len(panels)
        shot_variety_deduction = sum(0.1 for iss in issues if iss.category == "shot_variety")
        char_deduction = sum(0.05 for iss in issues if iss.category == "character_wardrobe")
        prop_deduction = sum(0.05 for iss in issues if iss.category == "prop_tracking")

        shot_score = max(0.0, 1.0 - shot_variety_deduction)
        char_score = max(0.0, 1.0 - char_deduction)
        prop_score = max(0.0, 1.0 - prop_deduction)

        final_score = round(max(0.1, (shot_score * 0.4 + char_score * 0.3 + prop_score * 0.3)), 2)
        is_valid = final_score >= 0.6 and not any(i.severity == "error" for i in issues)

        return ContinuityReport(
            score=final_score,
            is_valid=is_valid,
            total_panels=total,
            issues=issues,
            shot_variety_score=round(shot_score, 2),
            character_consistency_score=round(char_score, 2),
            prop_tracking_score=round(prop_score, 2),
        )
