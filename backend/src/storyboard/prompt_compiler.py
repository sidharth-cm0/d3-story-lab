"""Structured Storyboard Image Prompt Compiler.

Compiles highly structured, deterministic prompts for open-model image generators following:
1. STYLE (Professional cinematic storyboard, graphite pencil, charcoal wash, cross-hatching)
2. CAMERA (Lens feel, focal length, angle, elevation)
3. SHOT (Shot type, composition, rule of thirds, subject placement)
4. ACTION (Observable physical performance, gestures, motion)
5. CHARACTERS (Identifiable character physical traits from CharacterContinuityPack)
6. POSE (Physical staging and skeletal pose)
7. EXPRESSION (Observable facial micro-expressions and acting)
8. WARDROBE (Exact clothing continuity)
9. LOCATION (Architectural setting and landmarks from LocationContinuityPack)
10. PROPS (Prop shape, materials, markings, wear from PropContinuityPack)
11. LIGHTING (Volumetric lighting profile, key/rim directions, shadow masses)
12. DEPTH (Foreground / focal plane / background depth staging)
13. CONTINUITY (Sequence context and reference pack cross-links)
14. NEGATIVE (Strict negative constraints forbidding text, dialogue bubbles, CGI, etc.)
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle, ShotPurpose
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
)
from src.storyboard.control import StoryboardControlBundle
from src.storyboard.lighting_profile import LightingProfile, resolve_lighting_profile, LightingProfileType, LIGHTING_PROFILES
from src.narrative.performance_cues import PerformanceCue, PerformanceCueType


DEFAULT_STORYBOARD_STYLE = (
    "Professional cinematic storyboard, production-board sketch, graphite pencil, "
    "charcoal wash, rough cross-hatching, semi-realistic anatomy, cinematic perspective, "
    "expressive acting, grayscale, subtle paper texture, limited accent color, strong shadow masses"
)

DEFAULT_NEGATIVE_PROMPT = (
    "dialogue text, subtitles, captions, speech bubbles, word balloons, watermark, logo, signature, "
    "shot labels, frame numbers, letters, words, font, photorealism, 3d render, cgi, anime, cartoon, "
    "glossy digital painting, smooth plastic skin, deformed hands, extra fingers, missing fingers, "
    "distorted anatomy, broken perspective, blurry, low resolution"
)


class StructuredPromptResult(BaseModel):
    """Normalized structured breakdown of all 14 prompt sections."""
    model_config = ConfigDict(extra="ignore")

    style: str
    camera: str
    shot: str
    action: str
    characters: str
    pose: str
    expression: str
    wardrobe: str
    location: str
    props: str
    lighting: str
    depth: str
    continuity: str
    negative: str

    full_prompt: str
    prompt_hash: str

    def to_dict(self) -> Dict[str, str]:
        return self.model_dump(mode="json")


class StoryboardImagePromptCompiler:
    """Compiles multi-layer prompts with physical subtext acting and continuity guarantees."""

    def __init__(self, style_override: Optional[str] = None, negative_override: Optional[str] = None):
        self.style_prompt = style_override or DEFAULT_STORYBOARD_STYLE
        self.negative_prompt = negative_override or DEFAULT_NEGATIVE_PROMPT

    def _translate_performance_subtext(self, action_text: str, cue: Optional[PerformanceCue] = None) -> str:
        """Translate abstract internal states ('Evelyn is lying') into observable physical acting."""
        if cue and cue.action_text:
            return cue.action_text

        text_lower = action_text.lower()
        acting_cues = []

        # Detect lying / concealing / deception
        if any(w in text_lower for w in ["lying", "deceptive", "deceives", "concealing", "hides truth"]):
            acting_cues.append("jaw tense, eyes darting sideways, guarded shoulders, hand tightly gripping item, avoiding direct eye contact")
        # Detect interrogation / intimidation / threat
        elif any(w in text_lower for w in ["interrogates", "interrogation", "threatens", "cornering", "demands"]):
            acting_cues.append("leaning forward aggressively into personal space, piercing locked gaze, rigid posture, clenched knuckles")
        # Detect anxiety / nervousness / fear
        elif any(w in text_lower for w in ["nervous", "anxious", "panics", "fearful", "shivering", "cornered"]):
            acting_cues.append("shallow rapid breathing, defensive posture with arms drawn close, dilated watchful eyes, sweat sheen")
        # Detect stealth / vigilance
        elif any(w in text_lower for w in ["stealth", "covert", "cautious", "slips inside", "enters silently", "infiltrating"]):
            acting_cues.append("lowered center of gravity, slow measured footsteps, head turned listening for sound, flashlight held close to chest")
        # Detect revelation / shock
        elif any(w in text_lower for w in ["realizes", "discovers", "shock", "horrified", "stunned"]):
            acting_cues.append("frozen mid-movement, parted lips, widened stare fixed on discovery, slackened grip")

        if acting_cues:
            return f"{action_text}. Observable acting: {', '.join(acting_cues)}"
        return action_text

    def compile(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
        performance_cue: Optional[PerformanceCue] = None,
        lighting: Optional[LightingProfile] = None,
        control_bundle: Optional[StoryboardControlBundle] = None,
        sequence_context: Optional[StoryboardSequenceContext] = None,
    ) -> StructuredPromptResult:
        """Compile complete 14-section structured prompt."""
        # 1. STYLE
        style_sec = self.style_prompt

        # 2. CAMERA
        shot_str = panel.shot_type.value.replace("_", " ").title()
        angle_str = panel.camera_angle.value.replace("_", " ").title()
        lens = panel.lens_feel or "35mm cinematic lens, sharp focal depth"
        camera_sec = f"{angle_str} elevation, {lens}, cinematic film framing"

        # 3. SHOT
        comp = panel.composition or "Dynamic rule of thirds framing with strong diagonal shadow masses"
        shot_sec = f"{shot_str} shot. Framing: {comp}"

        # 4. ACTION (Physical performance acting)
        raw_action = panel.action_description or panel.action or "Scene unfolds"
        action_sec = self._translate_performance_subtext(raw_action, performance_cue)

        # 5. CHARACTERS & 7. EXPRESSION & 8. WARDROBE
        char_descriptions = []
        wardrobe_items = []
        expressions = []
        char_names = panel.character_names or panel.characters_present

        if char_packs and char_names:
            for name in char_names:
                matched_pack = None
                for cid, pack in char_packs.items():
                    if pack.name.lower() == name.lower() or pack.character_id.lower() == name.lower() or cid in panel.characters_present:
                        matched_pack = pack
                        break
                if matched_pack:
                    char_descriptions.append(
                        f"{matched_pack.name} ({matched_pack.age}, {matched_pack.build}, {matched_pack.face_shape}, {matched_pack.hair})"
                    )
                    wardrobe_items.append(f"{matched_pack.name} wearing {matched_pack.wardrobe}")
                    expressions.append(f"{matched_pack.name}: guarded calculating gaze, controlled micro-expressions")
                else:
                    char_descriptions.append(f"{name} (distinctive silhouette, sharp facial contours)")
                    wardrobe_items.append(f"{name} in tailored dark production attire")
        elif bible and bible.characters and char_names:
            for name in char_names:
                for cid, cref in bible.characters.items():
                    if cref.name.lower() == name.lower() or cid in panel.characters_present:
                        char_descriptions.append(cref.prompt_snippet())
                        wardrobe_items.append(f"{cref.name} wearing {cref.clothing}")
                        expressions.append(cref.expression_tendency)
                        break

        characters_sec = "; ".join(char_descriptions) if char_descriptions else "No actors in frame, pure environmental focus"
        wardrobe_sec = "; ".join(wardrobe_items) if wardrobe_items else "Standard dark cinematic clothing"
        expression_sec = "; ".join(expressions) if expressions else "Grounded, intense cinematic acting"

        # 6. POSE
        pose_sec = f"Staged blocking aligned with {panel.shot_type.value} framing, grounded human anatomy"
        if control_bundle and control_bundle.camera_details.get("actors_staged"):
            pose_sec += f", positions: {', '.join(control_bundle.camera_details['actors_staged'])}"

        # 9. LOCATION
        if loc_pack:
            location_sec = loc_pack.prompt_summary()
        elif panel.location_name:
            location_sec = f"{panel.location_name} ({panel.location_reference or 'Industrial architecture with concrete pillars and steel framing'})"
        else:
            location_sec = "Atmospheric film set interior with dark architectural elements"

        # 10. PROPS
        prop_descriptions = []
        if prop_packs and panel.objects_in_frame:
            for obj_key in panel.objects_in_frame:
                for pid, pack in prop_packs.items():
                    if pack.name.lower() == obj_key.lower() or pack.prop_id.lower() == obj_key.lower():
                        prop_descriptions.append(pack.prompt_summary())
                        break
        props_sec = "; ".join(prop_descriptions) if prop_descriptions else (", ".join(panel.objects_in_frame) if panel.objects_in_frame else "None")

        # 11. LIGHTING
        if lighting:
            resolved_lighting = lighting
        elif panel.lighting_profile_id:
            try:
                prof_type = LightingProfileType(panel.lighting_profile_id.lower())
                resolved_lighting = LIGHTING_PROFILES.get(prof_type)
            except Exception:
                resolved_lighting = None
            if not resolved_lighting:
                resolved_lighting = resolve_lighting_profile(
                    mood=panel.mood or "",
                    action=panel.action or panel.action_description or "",
                    scene_purpose=panel.narrative_purpose.value if hasattr(panel.narrative_purpose, "value") else str(panel.narrative_purpose or ""),
                )
        else:
            resolved_lighting = resolve_lighting_profile(
                mood=panel.mood or "",
                action=panel.action or panel.action_description or "",
                scene_purpose=panel.narrative_purpose.value if hasattr(panel.narrative_purpose, "value") else str(panel.narrative_purpose or ""),
            )
        lighting_sec = f"{resolved_lighting.name}: {resolved_lighting.description or 'High-contrast chiaroscuro with sharp rim highlights and deep shadow pools'}"

        # 12. DEPTH
        depth_plane = panel.focal_depth_plane or "focal_plane"
        depth_sec = f"Sharp focus on {depth_plane}, foreground and background layered with atmospheric depth"

        # 13. CONTINUITY
        continuity_parts = []
        if sequence_context:
            continuity_parts.append(f"Sequence seed family {sequence_context.shared_seed_family}")
            if sequence_context.previous_panel:
                continuity_parts.append(f"Visual continuity from shot {sequence_context.previous_panel}")
        continuity_parts.append(f"Preserve character facial identity and wardrobe across shots")
        continuity_sec = "; ".join(continuity_parts)

        # 14. NEGATIVE
        negative_sec = self.negative_prompt

        # Assemble unified prompt string
        full_sections = [
            f"[STYLE]: {style_sec}",
            f"[CAMERA]: {camera_sec}",
            f"[SHOT]: {shot_sec}",
            f"[ACTION]: {action_sec}",
            f"[CHARACTERS]: {characters_sec}",
            f"[POSE]: {pose_sec}",
            f"[EXPRESSION]: {expression_sec}",
            f"[WARDROBE]: {wardrobe_sec}",
            f"[LOCATION]: {location_sec}",
            f"[PROPS]: {props_sec}",
            f"[LIGHTING]: {lighting_sec}",
            f"[DEPTH]: {depth_sec}",
            f"[CONTINUITY]: {continuity_sec}",
        ]
        full_prompt_text = " | ".join(full_sections)
        import hashlib
        prompt_hash = hashlib.sha256(full_prompt_text.encode("utf-8")).hexdigest()[:16]

        return StructuredPromptResult(
            style=style_sec,
            camera=camera_sec,
            shot=shot_sec,
            action=action_sec,
            characters=characters_sec,
            pose=pose_sec,
            expression=expression_sec,
            wardrobe=wardrobe_sec,
            location=location_sec,
            props=props_sec,
            lighting=lighting_sec,
            depth=depth_sec,
            continuity=continuity_sec,
            negative=negative_sec,
            full_prompt=full_prompt_text,
            prompt_hash=prompt_hash,
        )
