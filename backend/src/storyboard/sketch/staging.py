"""Camera-aware composition and deterministic scene staging for storyboard panels.

Calculates screen-space placements, camera framing, z-depth, and actor orientations
to prevent bad overlaps and create cinematic storyboard compositions:
- Shot LOD scale: WIDE (20-35% canvas height), MEDIUM (55-80%), CLOSE_UP (head 50-75%), INSERT (prop 65-85%)
- OTS (Over-The-Shoulder) composition with foreground silhouette shoulder
- Real Dutch angle rotation
"""

from __future__ import annotations
import math
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
    z_index: int = 2


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
    z_index: int = 3


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
    dutch_rotation_deg: float = 0.0
    include_foreground: bool = True
    is_over_shoulder: bool = False


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
        v_offset_x = (version - 1) * 20.0 if version > 1 else 0.0

        staged_actors: List[StagedActor] = []
        staged_props: List[StagedProp] = []

        # Determine primary action pose & expression
        primary_pose = map_action_to_pose(action_text, dialogue_text, panel.narrative_purpose.value)
        primary_expr = map_emotion_to_expression(panel.mood, action_text, dialogue_text)

        floor_y = 425.0
        angle_scale_mult = 1.0
        if cam_angle == CameraAngle.LOW_ANGLE:
            floor_y = 455.0  # Horizon drops so character & architecture loom tall
            angle_scale_mult = 1.12
        elif cam_angle == CameraAngle.HIGH_ANGLE:
            floor_y = 395.0  # Camera looks down, subject feels smaller
            angle_scale_mult = 0.90

        dutch_deg = 0.0
        if cam_angle == CameraAngle.DUTCH_ANGLE:
            dutch_deg = -6.5 if (version % 2 == 1) else 6.5

        # =========================================================================
        # 1. EXTREME_WIDE: Architectural dominance, small silhouettes (~110px)
        # =========================================================================
        if shot_type == ShotType.EXTREME_WIDE:
            actor_h = 110.0
            start_x = 380.0 + v_offset_x
            for idx, cid in enumerate(char_ids[:2]):
                name = char_names[idx] if idx < len(char_names) else cid
                staged_actors.append(
                    StagedActor(
                        actor_id=cid,
                        name=name,
                        x=start_x + (idx * 55.0),
                        y=floor_y - actor_h,
                        height=actor_h,
                        facing_direction=1.0 if idx == 0 else -1.0,
                        pose=primary_pose if idx == 0 else PoseType.NEUTRAL,
                        expression=primary_expr,
                        crop_to_waist=False,
                        crop_to_bust=False,
                        z_index=2,
                    )
                )

        # =========================================================================
        # 2. WIDE: Full-body actor grounded on floor (~190px, ~35% height)
        # =========================================================================
        elif shot_type == ShotType.WIDE:
            actor_h = 240.0 * angle_scale_mult
            start_x = 340.0 + v_offset_x
            for idx, cid in enumerate(char_ids[:2]):
                name = char_names[idx] if idx < len(char_names) else cid
                facing = 1.0 if idx == 0 else -1.0
                staged_actors.append(
                    StagedActor(
                        actor_id=cid,
                        name=name,
                        x=start_x + (idx * 110.0),
                        y=floor_y - actor_h + 10,
                        height=actor_h,
                        facing_direction=facing,
                        pose=primary_pose if idx == 0 else PoseType.NEUTRAL,
                        expression=primary_expr,
                        crop_to_waist=False,
                        crop_to_bust=False,
                        z_index=2,
                    )
                )

        # =========================================================================
        # 3. MEDIUM: Waist-up framing (~360px, ~67% height)
        # =========================================================================
        elif shot_type == ShotType.MEDIUM:
            actor_h = 360.0 * angle_scale_mult
            mid_x = 420.0 + v_offset_x
            if char_ids:
                cid = char_ids[0]
                name = char_names[0] if char_names else cid
                staged_actors.append(
                    StagedActor(
                        actor_id=cid,
                        name=name,
                        x=mid_x,
                        y=150.0,
                        height=actor_h,
                        facing_direction=1.0,
                        pose=primary_pose,
                        expression=primary_expr,
                        crop_to_waist=True,
                        crop_to_bust=False,
                        z_index=3,
                    )
                )

        # =========================================================================
        # 4. CLOSE_UP & REACTION: Head fills ~60-75% panel height (~540px figure)
        # =========================================================================
        elif shot_type in (ShotType.CLOSE_UP, ShotType.REACTION, ShotType.EXTREME_CLOSE_UP):
            actor_h = 580.0
            mid_x = 480.0 + (v_offset_x * 0.5)
            if char_ids:
                cid = char_ids[0]
                name = char_names[0] if char_names else cid
                staged_actors.append(
                    StagedActor(
                        actor_id=cid,
                        name=name,
                        x=mid_x,
                        y=90.0,
                        height=actor_h,
                        facing_direction=1.0 if shot_type != ShotType.REACTION else -1.0,
                        pose=PoseType.NEUTRAL,
                        expression=primary_expr,
                        crop_to_waist=True,
                        crop_to_bust=True,
                        z_index=4,
                    )
                )

        # =========================================================================
        # 5. OVER_SHOULDER: Foreground shoulder silhouette looking at target
        # =========================================================================
        elif shot_type == ShotType.OVER_SHOULDER:
            # Foreground framing silhouette actor on left
            fg_cid = char_ids[0] if char_ids else "char_fg"
            fg_name = char_names[0] if char_names else "Detective"
            staged_actors.append(
                StagedActor(
                    actor_id=fg_cid,
                    name=fg_name,
                    x=230.0,
                    y=110.0,
                    height=520.0,
                    facing_direction=1.0,
                    pose=PoseType.NEUTRAL,
                    expression=primary_expr,
                    crop_to_waist=True,
                    crop_to_bust=True,
                    z_index=10,  # Foreground silhouette
                )
            )
            # Midground focal target actor on right
            if len(char_ids) > 1:
                bg_cid = char_ids[1]
                bg_name = char_names[1]
            else:
                bg_cid = "char_evelyn"
                bg_name = "Evelyn"
            staged_actors.append(
                StagedActor(
                    actor_id=bg_cid,
                    name=bg_name,
                    x=630.0,
                    y=170.0,
                    height=300.0,
                    facing_direction=-1.0,
                    pose=PoseType.DEFENSIVE if primary_expr == ExpressionType.AFRAID else PoseType.TALKING,
                    expression=primary_expr,
                    crop_to_waist=True,
                    crop_to_bust=False,
                    z_index=2,
                )
            )

        # =========================================================================
        # 6. INSERT: Prop fills 65-80% frame with hand interaction
        # =========================================================================
        elif shot_type == ShotType.INSERT:
            p_id = prop_ids[0] if prop_ids else "obj_dossier"
            staged_props.append(
                StagedProp(
                    prop_id=p_id,
                    name="Classified Dossier" if "dossier" in p_id else p_id,
                    cx=480.0,
                    cy=285.0,
                    scale=2.3,
                    rotation_deg=-4.0,
                    z_index=5,
                )
            )

        # Prop placement for non-insert shots
        if shot_type != ShotType.INSERT:
            for p_idx, pid in enumerate(prop_ids[:2]):
                p_name = "Dossier" if "dossier" in pid else ("Flashlight" if "flashlight" in pid else pid)
                if "flashlight" in pid.lower():
                    # Attached to primary actor hand
                    if staged_actors:
                        act = staged_actors[0]
                        hand_x = act.x + (act.facing_direction * 40.0)
                        hand_y = act.y + 160.0
                        staged_props.append(
                            StagedProp(
                                prop_id=pid,
                                name=p_name,
                                cx=hand_x,
                                cy=hand_y,
                                scale=1.1,
                                rotation_deg=act.facing_direction * 5.0,
                                held_by_actor_id=act.actor_id,
                                z_index=act.z_index + 1,
                            )
                        )
                else:
                    # Resting on table or surface in midground
                    staged_props.append(
                        StagedProp(
                            prop_id=pid,
                            name=p_name,
                            cx=560.0 + (p_idx * 60.0),
                            cy=floor_y - 25.0,
                            scale=1.15,
                            rotation_deg=-6.0,
                            z_index=3,
                        )
                    )

        return StagedScene(
            shot_type=shot_type,
            camera_angle=cam_angle,
            actors=staged_actors,
            props=staged_props,
            dutch_rotation_deg=dutch_deg,
            include_foreground=(shot_type != ShotType.INSERT and shot_type != ShotType.CLOSE_UP),
            is_over_shoulder=(shot_type == ShotType.OVER_SHOULDER),
        )
