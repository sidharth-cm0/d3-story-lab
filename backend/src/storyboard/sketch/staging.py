"""Camera-aware composition and deterministic scene staging for storyboard panels.

Calculates screen-space placements, camera framing, z-depth, and actor orientations
to prevent bad overlaps and create cinematic storyboard compositions.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import ShotType, CameraAngle, StoryboardPanel
from src.storyboard.sketch.pose import PoseType, map_action_to_pose
from src.storyboard.sketch.expression import ExpressionType, map_emotion_to_expression
from src.storyboard.sketch.stroke import get_rng


class StagedActor(BaseModel):
    """Position, scale, pose, and framing for an actor in a panel."""
    model_config = ConfigDict(extra="ignore")

    actor_id: str
    name: str
    x: float
    y: float
    height: float
    facing_direction: float = 1.0  # 1.0 right, -1.0 left
    pose: PoseType = PoseType.NEUTRAL
    expression: ExpressionType = ExpressionType.NEUTRAL
    crop_to_waist: bool = False
    crop_to_bust: bool = False
    z_index: int = 1


class StagedProp(BaseModel):
    """Position, scale, and attachment for a prop in a panel."""
    model_config = ConfigDict(extra="ignore")

    prop_id: str
    name: str
    cx: float
    cy: float
    scale: float = 1.0
    rotation_deg: float = 0.0
    held_by_actor_id: Optional[str] = None
    z_index: int = 2


class StagedScene(BaseModel):
    """Full spatial layout for a storyboard panel."""
    model_config = ConfigDict(extra="ignore")

    shot_type: ShotType
    camera_angle: CameraAngle
    actors: List[StagedActor] = Field(default_factory=list)
    props: List[StagedProp] = Field(default_factory=list)
    environment_scale: float = 1.0
    environment_offset_y: float = 0.0
    motion_cue: Optional[str] = None


class SceneStager:
    """Computes screen-space layout based on shot framing and screenplay context."""

    CANVAS_WIDTH = 960.0
    CANVAS_HEIGHT = 540.0

    @classmethod
    def stage_panel(
        cls,
        panel: StoryboardPanel,
        version: int = 1,
        seed: str = "staging",
    ) -> StagedScene:
        shot_type = panel.shot_type
        cam_angle = panel.camera_angle
        action_text = panel.action_description or panel.action or ""
        dialogue_text = panel.dialogue_excerpt or ""
        char_names = panel.character_names or ["Protagonist"]
        char_ids = panel.characters_present or [f"char_{c.lower()}" for c in char_names]
        prop_ids = panel.objects_in_frame or []

        rng = get_rng(f"{seed}_v{version}")
        # Slight angle variation for regeneration
        v_offset_x = (version - 1) * 24.0 if version > 1 else 0.0

        staged_actors: List[StagedActor] = []
        staged_props: List[StagedProp] = []

        # Determine primary action pose & expression
        primary_pose = map_action_to_pose(action_text, dialogue_text, panel.narrative_purpose.value)
        primary_expr = map_emotion_to_expression(panel.mood, action_text, dialogue_text)

        # Base floor level
        floor_y = 440.0

        if shot_type == ShotType.EXTREME_WIDE:
            # Environment dominates, actors are small silhouettes (~120px height)
            actor_h = 130.0
            start_x = 360.0 + v_offset_x
            for idx, cid in enumerate(char_ids[:2]):
                ax = start_x + (idx * 160.0)
                ay = floor_y - actor_h
                staged_actors.append(
                    StagedActor(
                        actor_id=cid,
                        name=char_names[idx] if idx < len(char_names) else cid,
                        x=ax,
                        y=ay,
                        height=actor_h,
                        facing_direction=1.0 if idx == 0 else -1.0,
                        pose=primary_pose if idx == 0 else PoseType.NEUTRAL,
                        expression=primary_expr,
                        crop_to_waist=False,
                        crop_to_bust=False,
                    )
                )

        elif shot_type == ShotType.WIDE:
            # Full bodies visible with ground & architectural context (~220px height)
            actor_h = 240.0
            if len(char_ids) >= 2:
                # Two actors facing each other
                ax1 = 320.0 + v_offset_x
                ax2 = 640.0 - v_offset_x
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[0],
                        name=char_names[0],
                        x=ax1,
                        y=floor_y - actor_h,
                        height=actor_h,
                        facing_direction=1.0,
                        pose=primary_pose,
                        expression=primary_expr,
                    )
                )
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[1],
                        name=char_names[1] if len(char_names) > 1 else "Counterpart",
                        x=ax2,
                        y=floor_y - actor_h,
                        height=actor_h,
                        facing_direction=-1.0,
                        pose=PoseType.NEUTRAL if primary_pose != PoseType.WALKING else PoseType.LOOKING_BACK,
                        expression=primary_expr if primary_expr != ExpressionType.NEUTRAL else ExpressionType.SUSPICIOUS,
                    )
                )
            else:
                # Single actor on rule of thirds
                ax = 440.0 + v_offset_x
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[0],
                        name=char_names[0],
                        x=ax,
                        y=floor_y - actor_h,
                        height=actor_h,
                        facing_direction=1.0,
                        pose=primary_pose,
                        expression=primary_expr,
                    )
                )

        elif shot_type == ShotType.MEDIUM:
            # Waist-up framing (~350px height)
            actor_h = 360.0
            if len(char_ids) >= 2:
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[0],
                        name=char_names[0],
                        x=320.0 + v_offset_x,
                        y=150.0,
                        height=actor_h,
                        facing_direction=1.0,
                        pose=primary_pose,
                        expression=primary_expr,
                        crop_to_waist=True,
                    )
                )
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[1],
                        name=char_names[1] if len(char_names) > 1 else "Counterpart",
                        x=640.0 - v_offset_x,
                        y=150.0,
                        height=actor_h,
                        facing_direction=-1.0,
                        pose=PoseType.TALKING if primary_pose != PoseType.TALKING else PoseType.NEUTRAL,
                        expression=ExpressionType.SUSPICIOUS,
                        crop_to_waist=True,
                    )
                )
            else:
                staged_actors.append(
                    StagedActor(
                        actor_id=char_ids[0],
                        name=char_names[0],
                        x=480.0 + v_offset_x,
                        y=150.0,
                        height=actor_h,
                        facing_direction=1.0,
                        pose=primary_pose,
                        expression=primary_expr,
                        crop_to_waist=True,
                    )
                )

        elif shot_type in (ShotType.CLOSE_UP, ShotType.REACTION):
            # Head and shoulders dominate canvas (~480px height, bust crop)
            actor_h = 490.0
            staged_actors.append(
                StagedActor(
                    actor_id=char_ids[0],
                    name=char_names[0],
                    x=480.0 + v_offset_x,
                    y=70.0,
                    height=actor_h,
                    facing_direction=1.0,
                    pose=PoseType.NEUTRAL,
                    expression=primary_expr if primary_expr != ExpressionType.NEUTRAL else ExpressionType.DETERMINED,
                    crop_to_bust=True,
                )
            )

        elif shot_type == ShotType.OVER_SHOULDER:
            # Foreground shoulder silhouette on left third, subject framed on right third
            fg_h = 520.0
            bg_h = 320.0
            staged_actors.append(
                StagedActor(
                    actor_id=char_ids[0],
                    name=char_names[0],
                    x=160.0,
                    y=120.0,
                    height=fg_h,
                    facing_direction=1.0,
                    pose=PoseType.NEUTRAL,
                    expression=ExpressionType.NEUTRAL,
                    crop_to_bust=True,
                    z_index=3,
                )
            )
            target_id = char_ids[1] if len(char_ids) > 1 else "counterpart"
            target_name = char_names[1] if len(char_names) > 1 else "Counterpart"
            staged_actors.append(
                StagedActor(
                    actor_id=target_id,
                    name=target_name,
                    x=680.0 + v_offset_x,
                    y=170.0,
                    height=bg_h,
                    facing_direction=-1.0,
                    pose=PoseType.TALKING,
                    expression=primary_expr,
                    crop_to_waist=True,
                    z_index=1,
                )
            )

        elif shot_type == ShotType.INSERT or shot_type == ShotType.EXTREME_CLOSE_UP:
            # Important prop fills frame
            if prop_ids:
                staged_props.append(
                    StagedProp(
                        prop_id=prop_ids[0],
                        name=prop_ids[0].replace("obj_", "").title(),
                        cx=480.0 + v_offset_x,
                        cy=270.0,
                        scale=2.2,
                        rotation_deg=5.0,
                        z_index=2,
                    )
                )
            else:
                # Close up on hands or key item
                staged_props.append(
                    StagedProp(
                        prop_id="dossier",
                        name="Dossier",
                        cx=480.0 + v_offset_x,
                        cy=270.0,
                        scale=2.2,
                        rotation_deg=4.0,
                        z_index=2,
                    )
                )

        else:  # Default fallback framing
            actor_h = 300.0
            staged_actors.append(
                StagedActor(
                    actor_id=char_ids[0],
                    name=char_names[0],
                    x=480.0 + v_offset_x,
                    y=floor_y - actor_h,
                    height=actor_h,
                    facing_direction=1.0,
                    pose=primary_pose,
                    expression=primary_expr,
                    crop_to_waist=False,
                )
            )

        # Stage Props into hands or scene if not already staged
        if prop_ids and shot_type != ShotType.INSERT and shot_type != ShotType.EXTREME_CLOSE_UP:
            p_oid = prop_ids[0]
            # If actor is holding or examining object, place near actor hand
            if primary_pose in (PoseType.HOLDING_OBJECT, PoseType.EXAMINING_OBJECT, PoseType.AIMING_FLASHLIGHT):
                target_actor = staged_actors[0] if staged_actors else None
                if target_actor:
                    px = target_actor.x + (target_actor.facing_direction * 22.0)
                    py = target_actor.y + (target_actor.height * 0.35)
                    staged_props.append(
                        StagedProp(
                            prop_id=p_oid,
                            name=p_oid.replace("obj_", "").title(),
                            cx=px,
                            cy=py,
                            scale=0.9,
                            held_by_actor_id=target_actor.actor_id,
                            z_index=2,
                        )
                    )
            else:
                # Place in scene on floor or desk
                staged_props.append(
                    StagedProp(
                        prop_id=p_oid,
                        name=p_oid.replace("obj_", "").title(),
                        cx=520.0 + v_offset_x,
                        cy=floor_y - 20.0,
                        scale=0.85,
                        z_index=2,
                    )
                )

        return StagedScene(
            shot_type=shot_type,
            camera_angle=cam_angle,
            actors=staged_actors,
            props=staged_props,
        )
