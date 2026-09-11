"""Storyboard Planner for translating Screenplays into Shot Plans."""

from __future__ import annotations
from typing import List, Optional

from src.narrative.fountain import ScreenplayDocument, ScreenplayBlockType
from src.domain.world import WorldState
from src.storyboard.models import ShotPlan, StoryboardPanel, ShotType, CameraAngle


class StoryboardPlanner:
    """Translates Fountain screenplays into cinematic storyboard panels."""

    def plan_shots(
        self,
        screenplay: ScreenplayDocument,
        world: Optional[WorldState] = None,
        aspect_ratio: str = "16:9",
    ) -> ShotPlan:
        panels: List[StoryboardPanel] = []
        panel_counter = 0

        for scene in screenplay.scenes:
            loc = world.locations.get(scene.location_id) if world else None
            loc_name = loc.name if loc else scene.heading.replace("INT. ", "").replace("EXT. ", "").split(" - ")[0]
            loc_desc = loc.description if loc else "Atmospheric interior"

            # 1. Establishing Shot for the scene
            panel_counter += 1
            est_action = f"Establishing shot: {scene.heading}"
            est_vis_desc = f"Atmospheric view of {loc_name}. Low-key light. Cinematic framing."
            est_prompt = (
                f"Wide shot, eye level. "
                f"Establishing view of {loc_name}. "
                f"{est_vis_desc}. "
                f"Low-key lighting, tense mood, cinematic composition."
            )

            est_panel = StoryboardPanel(
                scene_number=scene.scene_number,
                panel_number=panel_counter,
                shot_number=panel_counter,
                shot_type=ShotType.WIDE,
                camera_angle=CameraAngle.EYE_LEVEL,
                location_id=scene.location_id,
                location_name=loc_name,
                characters_present=[],
                character_names=[],
                action=est_action,
                action_description=est_action,
                visual_description=est_vis_desc,
                lighting="Low-key ambient lighting",
                mood="Atmospheric and tense",
                prompt=est_prompt,
                visual_prompt=est_prompt,
                aspect_ratio=aspect_ratio,
                source_event_ids=list(scene.source_event_ids[:2]),
                source_screenplay_block_ids=[scene.blocks[0].id] if scene.blocks else [],
                metadata={"shot_role": "establishing"},
            )
            panels.append(est_panel)

            # 2. Iterate blocks to generate narrative panels
            i = 0
            while i < len(scene.blocks):
                block = scene.blocks[i]

                if block.block_type == ScreenplayBlockType.ACTION:
                    panel_counter += 1
                    shot_type = ShotType.MEDIUM
                    camera_angle = CameraAngle.EYE_LEVEL

                    desc = block.text.lower()
                    if any(w in desc for w in ["knock", "gun", "document", "ledger", "open", "grab"]):
                        shot_type = ShotType.CLOSE_UP
                    elif any(w in desc for w in ["enter", "walk", "retreat", "leaves", "moved", "steps"]):
                        shot_type = ShotType.WIDE

                    if "knock" in desc or "threat" in desc:
                        camera_angle = CameraAngle.LOW_ANGLE

                    char_id = block.character_id
                    char = world.characters.get(char_id) if (world and char_id) else None
                    char_name = char.name if char else "Figure"
                    char_names = [char_name] if char else []

                    act_text = block.text
                    vis_desc = f"{loc_name}. Low-key illumination, focused shadows."
                    shot_str = shot_type.value.replace('_', ' ').capitalize()
                    angle_str = camera_angle.value.replace('_', ' ')

                    action_prompt = (
                        f"{shot_str} shot, {angle_str}. "
                        f"{char_name} in {loc_name}. "
                        f"{act_text}. "
                        f"Low-key lighting, tense mood, cinematic composition."
                    )

                    panels.append(
                        StoryboardPanel(
                            scene_number=scene.scene_number,
                            panel_number=panel_counter,
                            shot_number=panel_counter,
                            shot_type=shot_type,
                            camera_angle=camera_angle,
                            location_id=scene.location_id,
                            location_name=loc_name,
                            characters_present=[char_id] if char_id else [],
                            character_names=char_names,
                            action=act_text,
                            action_description=act_text,
                            visual_description=vis_desc,
                            lighting="Low-key lighting, high-contrast shadows",
                            mood="Suspenseful and deliberate",
                            prompt=action_prompt,
                            visual_prompt=action_prompt,
                            aspect_ratio=aspect_ratio,
                            source_event_ids=list(block.source_event_ids),
                            source_screenplay_block_ids=[block.id],
                            metadata={"shot_role": "action"},
                        )
                    )
                    i += 1

                elif block.block_type == ScreenplayBlockType.CHARACTER:
                    speaker_name = block.text
                    dialogue_text = ""
                    source_ids = list(block.source_event_ids)
                    block_ids = [block.id]
                    char_id = block.character_id

                    j = i + 1
                    while j < len(scene.blocks) and scene.blocks[j].block_type in (
                        ScreenplayBlockType.PARENTHETICAL,
                        ScreenplayBlockType.DIALOGUE,
                    ):
                        if scene.blocks[j].block_type == ScreenplayBlockType.DIALOGUE:
                            dialogue_text = scene.blocks[j].text
                            source_ids.extend(scene.blocks[j].source_event_ids)
                            block_ids.append(scene.blocks[j].id)
                        j += 1

                    panel_counter += 1
                    shot_type = ShotType.CLOSE_UP if len(dialogue_text) < 40 else ShotType.MEDIUM
                    shot_str = shot_type.value.replace('_', ' ').capitalize()
                    angle_str = "eye level"

                    act_text = f"{speaker_name} speaks: \"{dialogue_text}\"" if dialogue_text else f"{speaker_name} speaks."
                    vis_desc = f"{speaker_name} in {loc_name}. Key light on eyes, shadowed background."

                    dial_prompt = (
                        f"{shot_str} shot, {angle_str}. "
                        f"{speaker_name} in {loc_name}. "
                        f"{act_text}. "
                        f"Low-key lighting, tense mood, cinematic composition."
                    )

                    panels.append(
                        StoryboardPanel(
                            scene_number=scene.scene_number,
                            panel_number=panel_counter,
                            shot_number=panel_counter,
                            shot_type=shot_type,
                            camera_angle=CameraAngle.EYE_LEVEL,
                            location_id=scene.location_id,
                            location_name=loc_name,
                            characters_present=[char_id] if char_id else [],
                            character_names=[speaker_name],
                            action=act_text,
                            action_description=act_text,
                            visual_description=vis_desc,
                            lighting="Dramatic key light with deep shadows",
                            mood="Tense and emotionally focused",
                            prompt=dial_prompt,
                            visual_prompt=dial_prompt,
                            dialogue_excerpt=dialogue_text,
                            aspect_ratio=aspect_ratio,
                            source_event_ids=list(dict.fromkeys(source_ids)),
                            source_screenplay_block_ids=block_ids,
                            metadata={"shot_role": "dialogue"},
                        )
                    )
                    i = j
                else:
                    i += 1

        return ShotPlan(
            project_title=screenplay.title,
            total_panels=len(panels),
            panels=panels,
            aspect_ratio=aspect_ratio,
        )
