"""Storyboard Planner for translating Screenplays into Shot Plans with Visual Continuity."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
import math
import re

from src.narrative.fountain import ScreenplayDocument, ScreenplayBlockType
from src.domain.world import WorldState
from src.storyboard.models import (
    ShotPlan,
    StoryboardPanel,
    StoryboardPage,
    ShotType,
    CameraAngle,
    ShotPurpose,
    PageLayoutTemplate,
)
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler
from src.storyboard.prop_resolver import PropResolver
from src.storyboard.psychological_camera import PsychologicalCameraPlanner, PsychologicalState
from src.storyboard.lighting_profile import resolve_lighting_profile, LightingProfileType
from src.storyboard.transitions import TransitionPlanner
from src.storyboard.focal_depth import FocalDepthPlane


SFX_PATTERNS = [
    (r"\b(click|clicks|clicked)\b", "CLICK!"),
    (r"\b(slam|slams|slamming)\b", "SLAM!"),
    (r"\b(thud|thuds|thump)\b", "THUD!"),
    (r"\b(knock|knocks|knocking)\b", "KNOCK KNOCK!"),
    (r"\b(rattle|rattles)\b", "RATTLE!"),
    (r"\b(creak|creaks)\b", "CREEEAK..."),
    (r"\b(shatter|shatters|glass)\b", "CRASH!"),
    (r"\b(ring|rings|phone)\b", "BRRRING!"),
    (r"\b(buzz|buzzes|static)\b", "BZZZZT!"),
    (r"\b(whisper|whispers)\b", "WHISPER..."),
    (r"\b(gasp|gasps)\b", "GASP!"),
]


class StoryboardPlanner:
    """Translates Fountain screenplays into cinematic storyboard panels with continuity."""

    def __init__(self, panels_per_page: int = 4, density_mode: str = "standard"):
        self.panels_per_page = panels_per_page
        self.density_mode = density_mode  # "quick", "standard", "detailed"
        self.compiler = StoryboardPromptCompiler()
        self.camera_planner = PsychologicalCameraPlanner()
        self.transition_planner = TransitionPlanner()

    def plan_shots(
        self,
        screenplay: ScreenplayDocument,
        world: Optional[WorldState] = None,
        bible: Optional[VisualBible] = None,
        aspect_ratio: str = "16:9",
        project_id: str = "",
        keyframe_budget: Optional[int] = None,
    ) -> ShotPlan:
        """Create a complete sequence of storyboard panels organized into pages."""
        panels: List[StoryboardPanel] = []
        panel_counter = 0

        # Build visual bible if not supplied
        if not bible and world:
            bible = VisualBible.from_world(world)

        # Pre-build lookup maps for quick fallback
        char_profiles: Dict[str, str] = {}
        if world:
            for cid, c in world.characters.items():
                if hasattr(c, "visual_profile") and c.visual_profile:
                    char_profiles[cid] = c.visual_profile.summary_prompt()
                else:
                    char_profiles[cid] = f"{c.name} ({c.role}, guarded posture, dark cinematic styling)"

        obj_profiles: Dict[str, str] = {}
        if world:
            for oid, o in world.objects.items():
                if hasattr(o, "visual_profile") and o.visual_profile:
                    obj_profiles[oid] = o.visual_profile.summary_prompt()
                else:
                    obj_profiles[oid] = f"{o.name} ({o.description or 'noir prop'})"

        loc_profiles: Dict[str, str] = {}
        if world:
            for lid, l in world.locations.items():
                if hasattr(l, "visual_profile") and l.visual_profile:
                    loc_profiles[lid] = l.visual_profile.summary_prompt()
                else:
                    loc_profiles[lid] = f"{l.name} ({l.description or 'high-contrast noir interior'})"

        introduced_characters: set = set()

        for scene in screenplay.scenes:
            loc = world.locations.get(scene.location_id) if world else None
            loc_name = loc.name if loc else scene.heading.replace("INT. ", "").replace("EXT. ", "").split(" - ")[0]
            loc_vis = loc_profiles.get(scene.location_id, f"{loc_name} (cinematic noir architecture, low-key lighting)")

            # Extract Core Emotional Objective for the scene if available
            ceo_data: Optional[Dict[str, Any]] = scene.metadata.get("core_emotional_objective") if scene.metadata else None
            focal_char_id = ceo_data.get("focal_character_id") if ceo_data else None
            focal_char_name = ceo_data.get("focal_character_name") if ceo_data else None

            # Resolve canonical objects for establishing shot
            est_text = f"{scene.heading} {loc_name}"
            est_obj_ids = PropResolver.resolve_canonical_object_ids(
                text_pool=est_text,
                world=world,
                location_id=scene.location_id,
            )
            if not est_obj_ids and world:
                est_obj_ids = [
                    oid for oid, o in world.objects.items()
                    if o.location_id == scene.location_id
                ][:2]

            est_obj_refs: Dict[str, str] = {}
            for oid in est_obj_ids:
                if bible and oid in bible.objects:
                    est_obj_refs[oid] = bible.objects[oid].prompt_snippet()
                elif oid in obj_profiles:
                    est_obj_refs[oid] = obj_profiles[oid]

            # 1. Establishing Shot for the scene
            panel_counter += 1
            page_num = ((panel_counter - 1) // self.panels_per_page) + 1
            est_action = f"Establishing shot: {scene.heading}"
            est_vis_desc = f"Atmospheric view of {loc_name}. Heavy shadows, cold rain reflections, architectural depth."
            est_prompt_text = (
                f"Graphic novel storyboard, Frank Miller high-contrast noir ink style. "
                f"Wide establishing shot of {loc_vis}. Low-key chiaroscuro lighting, deep black shadows."
            )

            est_rationale = f"Atmospheric environmental establish for {scene.heading}; sets spatial grounding and mood."
            if ceo_data and ceo_data.get("immediate_desire"):
                est_rationale += f" Prepares arena for focal pursuit: '{ceo_data.get('immediate_desire')}'."

            est_panel = StoryboardPanel(
                id=f"pnl_{scene.scene_number:02d}_est_{panel_counter:03d}",
                panel_id=f"pnl_{scene.scene_number:02d}_est_{panel_counter:03d}",
                project_id=project_id,
                scene_id=f"scn_{scene.scene_number}",
                scene_number=scene.scene_number,
                panel_number=panel_counter,
                shot_number=panel_counter,
                page_number=page_num,
                shot_type=ShotType.WIDE,
                camera_angle=CameraAngle.EYE_LEVEL,
                narrative_purpose=ShotPurpose.ESTABLISH,
                lens_feel="24mm anamorphic wide, expansive environment depth",
                composition="Rule of thirds, low architectural horizon, deep shadows framing entrance",
                psychological_rationale=est_rationale,
                location_id=scene.location_id,
                location_name=loc_name,
                characters_present=[],
                character_names=[],
                objects_in_frame=est_obj_ids,
                action=est_action,
                action_description=est_action,
                visual_description=est_vis_desc,
                lighting="Low-key ambient chiaroscuro, stark deep shadows",
                mood="Atmospheric, ominous, and tense",
                prompt=est_prompt_text,
                image_prompt=est_prompt_text,
                visual_prompt=est_prompt_text,
                compiled_prompt=est_prompt_text,
                location_reference=loc_vis,
                object_references=est_obj_refs,
                continuity_notes=f"Maintains {loc_name} environmental layout and lighting palette.",
                caption=est_action,
                dialogue_bubble_type="caption",
                camera_movement="STATIC",
                focal_depth_plane="background",
                lighting_profile_id="MOONLIT_INDUSTRIAL" if "dock" in loc_name.lower() or "night" in loc_name.lower() else "NOIR_HARD",
                aspect_ratio=aspect_ratio,
                camera_axis_side="NEUTRAL",
                axis_crossing_flag=False,
                screen_direction="NEUTRAL",
                source_event_ids=list(scene.source_event_ids[:2]),
                source_screenplay_block_ids=[scene.blocks[0].id] if scene.blocks else [],
                metadata={
                    "shot_role": "establishing",
                    "psychological_rationale": est_rationale,
                    **({"core_emotional_objective": ceo_data} if ceo_data else {}),
                },
            )
            # Compile full structured prompt
            compiled_est = self.compiler.compile_panel_prompt(est_panel, bible)
            est_panel.compiled_prompt = compiled_est
            est_panel.image_prompt = compiled_est
            est_panel.visual_prompt = compiled_est
            panels.append(est_panel)

            # 2. Filter / Iterate blocks based on density mode
            blocks = scene.blocks
            if self.density_mode == "quick":
                # Only primary action and first dialogue
                action_blocks = [b for b in blocks if b.block_type == ScreenplayBlockType.ACTION][:1]
                char_blocks = [b for b in blocks if b.block_type == ScreenplayBlockType.CHARACTER][:1]
                selected_block_indices = set()
                for b in action_blocks + char_blocks:
                    selected_block_indices.add(blocks.index(b))
            else:
                selected_block_indices = set(range(len(blocks)))

            i = 0
            last_shot_type = ShotType.WIDE

            while i < len(blocks):
                if i not in selected_block_indices and self.density_mode == "quick":
                    i += 1
                    continue

                block = blocks[i]

                if block.block_type == ScreenplayBlockType.ACTION:
                    panel_counter += 1
                    page_num = ((panel_counter - 1) // self.panels_per_page) + 1
                    desc = block.text.lower()

                    # Determine narrative purpose
                    purpose = ShotPurpose.ACTION
                    if any(w in desc for w in ["open", "unlock", "examine", "clue", "seal", "key", "dossier", "ledger", "transceiver", "drive", "safe", "drawer"]):
                        purpose = ShotPurpose.CLUE
                    elif any(w in desc for w in ["gasps", "freezes", "spotted", "discovered", "stares", "shock", "alarm", "hears"]):
                        purpose = ShotPurpose.REACTION
                    elif any(w in desc for w in ["knock", "gun", "threat", "intimidate", "standoff", "shadow"]):
                        purpose = ShotPurpose.THREAT
                    elif any(w in desc for w in ["enter", "walk", "retreat", "leaves", "moved", "steps", "flee", "escapes", "runs"]):
                        purpose = ShotPurpose.TRANSITION
                    elif any(w in desc for w in ["face", "eyes", "whisper", "glance", "secret", "truth"]):
                        purpose = ShotPurpose.REVELATION

                    char_id = block.character_id
                    char = world.characters.get(char_id) if (world and char_id) else None
                    char_name = char.name if char else "Protagonist"
                    char_names = [char_name] if char else []
                    char_ref = {char_name: char_profiles.get(char_id, char_name)} if char_id else {}

                    # Check if focal character is framed in this action
                    is_focal = False
                    if ceo_data:
                        if char_id and char_id == focal_char_id:
                            is_focal = True
                        elif focal_char_name and (char_name.lower() == str(focal_char_name).lower() or str(focal_char_name).lower() in block.text.lower()):
                            is_focal = True

                    # Psychological Camera Planning
                    psych_state = self.camera_planner.derive_psychological_state(char)
                    cam_rec = self.camera_planner.plan_camera(
                        psych_state=psych_state,
                        action_text=block.text,
                        shot_purpose=purpose,
                        last_shot_type=last_shot_type,
                        core_emotional_objective=ceo_data if is_focal else None,
                    )
                    lighting_prof = resolve_lighting_profile(mood=scene.heading, action=block.text)

                    shot_type = cam_rec.shot_type
                    camera_angle = cam_rec.camera_angle
                    camera_movement = cam_rec.camera_movement
                    lens = cam_rec.lens_feel
                    comp = cam_rec.composition_guide
                    lighting_desc = lighting_prof.description
                    lighting_id = lighting_prof.id.value

                    # Visual rhythm pacing: prevent consecutive identical framing
                    if shot_type == last_shot_type:
                        if shot_type == ShotType.MEDIUM:
                            shot_type = ShotType.CLOSE_UP
                        elif shot_type == ShotType.WIDE:
                            shot_type = ShotType.MEDIUM
                    last_shot_type = shot_type

                    # Detect character introduction
                    if char_id and char_id not in introduced_characters:
                        introduced_characters.add(char_id)
                        purpose = ShotPurpose.INTRODUCE_CHARACTER

                    # Detect any other world characters mentioned in action
                    if world:
                        for other_id, other_c in world.characters.items():
                            if other_id != char_id and other_c.name.lower() in desc:
                                if other_c.name not in char_names:
                                    char_names.append(other_c.name)
                                    char_ref[other_c.name] = char_profiles.get(other_id, other_c.name)

                    # Identify canonical objects in this action via PropResolver
                    act_event_texts = []
                    direct_obj_ids = []
                    if world and block.source_event_ids:
                        for eid in block.source_event_ids:
                            ev = world.events.get(eid)
                            if ev:
                                if ev.description:
                                    act_event_texts.append(ev.description)
                                if getattr(ev, "target_object_id", None):
                                    direct_obj_ids.append(ev.target_object_id)
                                if hasattr(ev, "details") and isinstance(ev.details, dict):
                                    for k, v in ev.details.items():
                                        if any(sub in k for sub in ("object", "item", "prop", "target")) and isinstance(v, str):
                                            direct_obj_ids.append(v)

                    act_text_pool = " ".join([block.text, desc, purpose.value, scene.heading] + act_event_texts)
                    matched_obj_ids = PropResolver.resolve_canonical_object_ids(
                        text_pool=act_text_pool,
                        world=world,
                        location_id=scene.location_id,
                        characters_present=char_names,
                        direct_object_ids=direct_obj_ids,
                    )
                    obj_refs = {}
                    for oid in matched_obj_ids:
                        if bible and oid in bible.objects:
                            obj_refs[oid] = bible.objects[oid].prompt_snippet()
                        elif oid in obj_profiles:
                            obj_refs[oid] = obj_profiles[oid]

                    primary_prop_focus = ""
                    if matched_obj_ids:
                        p_oid = matched_obj_ids[0]
                        if bible and p_oid in bible.objects:
                            primary_prop_focus = bible.objects[p_oid].name
                        elif world and p_oid in world.objects:
                            primary_prop_focus = world.objects[p_oid].name
                        else:
                            primary_prop_focus = p_oid

                    # Detect comic SFX
                    detected_sfx = None
                    for pat, sfx_text in SFX_PATTERNS:
                        if re.search(pat, desc):
                            detected_sfx = sfx_text
                            break

                    act_prompt_text = (
                        f"Graphic novel storyboard, noir ink style. "
                        f"{shot_type.value.title()} shot of {char_name} in {loc_vis}. Action: {block.text}."
                    )

                    act_panel = StoryboardPanel(
                        id=f"pnl_{scene.scene_number:02d}_act_{panel_counter:03d}",
                        panel_id=f"pnl_{scene.scene_number:02d}_act_{panel_counter:03d}",
                        project_id=project_id,
                        scene_id=f"scn_{scene.scene_number}",
                        scene_number=scene.scene_number,
                        panel_number=panel_counter,
                        shot_number=panel_counter,
                        page_number=page_num,
                        shot_type=shot_type,
                        camera_angle=camera_angle,
                        narrative_purpose=purpose,
                        lens_feel=lens,
                        composition=comp,
                        psychological_rationale=cam_rec.psychological_rationale,
                        subject_focus=f"{char_name} {primary_prop_focus}".strip(),
                        location_id=scene.location_id,
                        location_name=loc_name,
                        characters_present=[char_id] if char_id else [],
                        character_names=char_names,
                        objects_in_frame=matched_obj_ids,
                        action=block.text,
                        action_description=block.text,
                        visual_description=f"{char_name} in {loc_name}. Chiaroscuro key illumination.",
                        lighting=lighting_desc,
                        lighting_profile_id=lighting_id,
                        camera_movement=camera_movement,
                        mood="Suspenseful and deliberate",
                        prompt=act_prompt_text,
                        image_prompt=act_prompt_text,
                        visual_prompt=act_prompt_text,
                        compiled_prompt=act_prompt_text,
                        character_references=char_ref,
                        object_references=obj_refs,
                        location_reference=loc_vis,
                        caption=block.text,
                        dialogue_bubble_type="caption",
                        sfx_label=detected_sfx,
                        continuity_notes=f"Preserves {char_name} attire and visual identity traits.",
                        aspect_ratio=aspect_ratio,
                        camera_axis_side="LEFT",
                        axis_crossing_flag=False,
                        screen_direction="LEFT_TO_RIGHT",
                        source_event_ids=list(block.source_event_ids),
                        source_screenplay_block_ids=[block.id],
                        metadata={
                            "shot_role": "action",
                            "purpose": purpose.value,
                            "psychological_rationale": cam_rec.psychological_rationale,
                            "is_focal_character": is_focal,
                            **({"core_emotional_objective": ceo_data} if is_focal else {}),
                        },
                    )
                    compiled_act = self.compiler.compile_panel_prompt(act_panel, bible)
                    act_panel.compiled_prompt = compiled_act
                    act_panel.image_prompt = compiled_act
                    act_panel.visual_prompt = compiled_act
                    panels.append(act_panel)
                    i += 1

                elif block.block_type == ScreenplayBlockType.CHARACTER:
                    speaker_name = block.text
                    dialogue_text = ""
                    source_ids = list(block.source_event_ids)
                    block_ids = [block.id]
                    char_id = block.character_id

                    j = i + 1
                    while j < len(blocks) and blocks[j].block_type in (
                        ScreenplayBlockType.PARENTHETICAL,
                        ScreenplayBlockType.DIALOGUE,
                    ):
                        if blocks[j].block_type == ScreenplayBlockType.DIALOGUE:
                            dialogue_text = blocks[j].text
                            source_ids.extend(blocks[j].source_event_ids)
                            block_ids.append(blocks[j].id)
                        j += 1

                    panel_counter += 1
                    page_num = ((panel_counter - 1) // self.panels_per_page) + 1

                    dia_lower = dialogue_text.lower()
                    bubble_type = "speech"
                    purpose = ShotPurpose.DIALOGUE
                    if any(w in dia_lower for w in ["listen", "warn", "threat", "kill", "die", "watch out"]):

                        purpose = ShotPurpose.THREAT
                    elif any(w in dia_lower for w in ["know", "secret", "truth", "confess", "evidence", "lying"]):
                        purpose = ShotPurpose.REVELATION

                    elif any(w in dia_lower for w in ["shh", "quiet", "whisper", "softly"]):
                        bubble_type = "whisper"
                    elif any(w in dia_lower for w in ["stop!", "freeze!", "no!", "get back!"]):
                        bubble_type = "shout"

                    speaker_char = world.characters.get(char_id) if (world and char_id) else None
                    is_focal = False
                    if ceo_data:
                        if char_id and char_id == focal_char_id:
                            is_focal = True
                        elif focal_char_name and (speaker_name.lower() == str(focal_char_name).lower() or (speaker_char and speaker_char.name.lower() == str(focal_char_name).lower())):
                            is_focal = True

                    psych_state = self.camera_planner.derive_psychological_state(speaker_char)
                    cam_rec = self.camera_planner.plan_camera(
                        psych_state=psych_state,
                        action_text=dialogue_text,
                        shot_purpose=purpose,
                        last_shot_type=last_shot_type,
                        core_emotional_objective=ceo_data if is_focal else None,
                    )
                    lighting_prof = resolve_lighting_profile(mood="Tense", action=dialogue_text)

                    shot_type = cam_rec.shot_type
                    camera_angle = cam_rec.camera_angle
                    camera_movement = cam_rec.camera_movement
                    lens = cam_rec.lens_feel
                    comp = cam_rec.composition_guide
                    lighting_desc = lighting_prof.description
                    lighting_id = lighting_prof.id.value

                    # Rhythm check
                    if shot_type == last_shot_type and shot_type == ShotType.MEDIUM:
                        shot_type = ShotType.CLOSE_UP
                    last_shot_type = shot_type

                    char_desc = char_profiles.get(char_id, speaker_name) if char_id else speaker_name
                    char_ref = {speaker_name: char_desc}

                    # Resolve canonical objects mentioned in dialogue or source events
                    dia_event_texts = []
                    dia_direct_obj_ids = []
                    if world and source_ids:
                        for eid in source_ids:
                            ev = world.events.get(eid)
                            if ev:
                                if ev.description:
                                    dia_event_texts.append(ev.description)
                                if getattr(ev, "target_object_id", None):
                                    dia_direct_obj_ids.append(ev.target_object_id)
                                if hasattr(ev, "details") and isinstance(ev.details, dict):
                                    for k, v in ev.details.items():
                                        if any(sub in k for sub in ("object", "item", "prop", "target")) and isinstance(v, str):
                                            dia_direct_obj_ids.append(v)

                    dia_text_pool = " ".join([speaker_name, dialogue_text, dia_lower, purpose.value, scene.heading] + dia_event_texts)
                    dia_obj_ids = PropResolver.resolve_canonical_object_ids(
                        text_pool=dia_text_pool,
                        world=world,
                        location_id=scene.location_id,
                        characters_present=[char_id] if char_id else [],
                        direct_object_ids=dia_direct_obj_ids,
                    )
                    dia_obj_refs = {}
                    for oid in dia_obj_ids:
                        if bible and oid in bible.objects:
                            dia_obj_refs[oid] = bible.objects[oid].prompt_snippet()
                        elif oid in obj_profiles:
                            dia_obj_refs[oid] = obj_profiles[oid]

                    # Detect SFX
                    detected_sfx = None
                    for pat, sfx_text in SFX_PATTERNS:
                        if re.search(pat, dia_lower):
                            detected_sfx = sfx_text
                            break

                    dia_prompt_text = (
                        f"Graphic novel storyboard, noir comic art. "
                        f"{speaker_name.upper()}: delivering dialogue '{dialogue_text}' in {loc_vis}."
                    )

                    dia_panel = StoryboardPanel(
                        id=f"pnl_{scene.scene_number:02d}_dia_{panel_counter:03d}",
                        panel_id=f"pnl_{scene.scene_number:02d}_dia_{panel_counter:03d}",
                        project_id=project_id,
                        scene_id=f"scn_{scene.scene_number}",
                        scene_number=scene.scene_number,
                        panel_number=panel_counter,
                        shot_number=panel_counter,
                        page_number=page_num,
                        shot_type=shot_type,
                        camera_angle=camera_angle,
                        narrative_purpose=purpose,
                        lens_feel=lens,
                        composition=comp,
                        psychological_rationale=cam_rec.psychological_rationale,
                        subject_focus=f"{speaker_name} speaking",
                        location_id=scene.location_id,
                        location_name=loc_name,
                        characters_present=[char_id] if char_id else [],
                        character_names=[speaker_name],
                        objects_in_frame=dia_obj_ids,
                        action=f"{speaker_name}: \"{dialogue_text}\"",
                        action_description=f"{speaker_name} delivering dialogue with calculated intensity.",
                        visual_description=f"{speaker_name} speaking. Razor-sharp lighting across features.",
                        lighting=lighting_desc,
                        lighting_profile_id=lighting_id,
                        camera_movement=camera_movement,
                        mood="Emotionally charged, guarded confrontation",
                        prompt=dia_prompt_text,
                        image_prompt=dia_prompt_text,
                        visual_prompt=dia_prompt_text,
                        compiled_prompt=dia_prompt_text,
                        dialogue_excerpt=dialogue_text,
                        dialogue_bubble_type=bubble_type,
                        sfx_label=detected_sfx,
                        character_references=char_ref,
                        object_references=dia_obj_refs,
                        location_reference=loc_vis,
                        caption=f"{speaker_name}: \"{dialogue_text}\"",
                        continuity_notes=f"Matches {speaker_name} facial features, hairstyle, and wardrobe.",
                        aspect_ratio=aspect_ratio,
                        camera_axis_side="LEFT",
                        axis_crossing_flag=False,
                        screen_direction="LEFT_TO_RIGHT",
                        source_event_ids=list(dict.fromkeys(source_ids)),
                        source_screenplay_block_ids=block_ids,
                        metadata={
                            "shot_role": "dialogue",
                            "purpose": purpose.value,
                            "psychological_rationale": cam_rec.psychological_rationale,
                            "is_focal_character": is_focal,
                            **({"core_emotional_objective": ceo_data} if is_focal else {}),
                        },
                    )
                    compiled_dia = self.compiler.compile_panel_prompt(dia_panel, bible)
                    dia_panel.compiled_prompt = compiled_dia
                    dia_panel.image_prompt = compiled_dia
                    dia_panel.visual_prompt = compiled_dia
                    panels.append(dia_panel)
                    i = j
                else:
                    i += 1

        # Apply Transition Planning across panels
        self.transition_planner.plan_transitions(panels)

        # Apply Keyframe Beat Selection
        from src.storyboard.open_model_provider import select_keyframe_indices
        keyframe_indices = select_keyframe_indices(panels, budget=keyframe_budget)
        for idx, pnl in enumerate(panels):
            pnl.is_keyframe = idx in keyframe_indices
            if idx in keyframe_indices:
                pnl.keyframe_reason = f"Keyframe dramatic beat ({pnl.narrative_purpose.value})"

        # Organize into Storyboard Pages with Layout Templates and Slot Assignments
        total_pages = max(1, math.ceil(len(panels) / self.panels_per_page)) if panels else 1
        pages: List[StoryboardPage] = []

        layout_templates_cycle = [
            PageLayoutTemplate.TEMPLATE_A,  # Large wide, two small, large footer
            PageLayoutTemplate.TEMPLATE_B,  # Three horizontal strips
            PageLayoutTemplate.TEMPLATE_C,  # One vertical + two stacked
            PageLayoutTemplate.TEMPLATE_D,  # Six-frame sequence
            PageLayoutTemplate.TEMPLATE_E,  # Large climax splash
        ]

        slot_mapping_by_template = {
            PageLayoutTemplate.TEMPLATE_A: ["top_hero", "mid_left", "mid_right", "bottom_hero"],
            PageLayoutTemplate.TEMPLATE_B: ["strip_1", "strip_2", "strip_3", "strip_4"],
            PageLayoutTemplate.TEMPLATE_C: ["hero_left", "stack_top_right", "stack_bot_right", "bottom_wide"],
            PageLayoutTemplate.TEMPLATE_D: ["frame_1", "frame_2", "frame_3", "frame_4", "frame_5", "frame_6"],
            PageLayoutTemplate.TEMPLATE_E: ["climax_splash", "reaction_inset", "detail_inset_1", "detail_inset_2"],
        }

        for p in range(1, total_pages + 1):
            page_panels = [pnl for pnl in panels if pnl.page_number == p]
            # Check for climax or revelation in page
            has_climax = any(pnl.narrative_purpose in (ShotPurpose.CLIMAX, ShotPurpose.REVELATION) for pnl in page_panels)
            if has_climax and len(page_panels) <= 4:
                template = PageLayoutTemplate.TEMPLATE_E
            else:
                template = layout_templates_cycle[(p - 1) % len(layout_templates_cycle)]
            slots = slot_mapping_by_template.get(template, ["slot_1", "slot_2", "slot_3", "slot_4"])

            for idx, pnl in enumerate(page_panels):
                slot_name = slots[idx] if idx < len(slots) else f"slot_{idx+1}"
                pnl.layout_slot = slot_name

            pages.append(
                StoryboardPage(
                    page_number=p,
                    total_pages=total_pages,
                    title=f"Page {p} of {total_pages}",
                    layout_template=template,
                    panels=page_panels,
                )
            )

        # Coverage Analytics
        shot_type_dist: Dict[str, int] = {}
        purpose_dist: Dict[str, int] = {}
        all_chars = set()
        for p in panels:
            shot_type_dist[p.shot_type.value] = shot_type_dist.get(p.shot_type.value, 0) + 1
            purpose_dist[p.narrative_purpose.value] = purpose_dist.get(p.narrative_purpose.value, 0) + 1
            all_chars.update(p.character_names)

        trans_types: Dict[str, int] = {}
        for p in panels:
            if p.transition_type:
                trans_types[p.transition_type] = trans_types.get(p.transition_type, 0) + 1

        coverage_data = {
            "density_mode": self.density_mode,
            "total_scenes": len(screenplay.scenes),
            "scenes_covered": len(set(p.scene_number for p in panels)),
            "total_characters_depicted": len(all_chars),
            "characters_depicted": sorted(list(all_chars)),
            "shot_type_distribution": shot_type_dist,
            "purpose_distribution": purpose_dist,
            "transition_distribution": trans_types,
            "total_transitions_planned": sum(trans_types.values()),
        }

        return ShotPlan(
            project_title=screenplay.title,
            total_panels=len(panels),
            total_pages=total_pages,
            panels_per_page=self.panels_per_page,
            panels=panels,
            pages=pages,
            aspect_ratio=aspect_ratio,
            density_mode=self.density_mode,
            render_mode="KEYFRAMES",
            keyframe_panel_indices=keyframe_indices,
            storyboard_coverage=coverage_data,
        )
