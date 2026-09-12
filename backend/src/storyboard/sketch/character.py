"""Character sketch renderer and visual identity persistence.

Generates recognizable, distinct hand-drawn storyboard character sketches
with stable visual proportions, hairstyles, wardrobe silhouettes, and accessories.
"""

from __future__ import annotations
import math
import random
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.visual_bible import CharacterVisualReference
from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchEllipse,
    SketchPolyline,
    SketchPolygon,
    CrossHatch,
    get_rng,
    get_seed_hash,
)
from src.storyboard.sketch.pose import PoseType, PoseDefinition, POSE_DEFINITIONS
from src.storyboard.sketch.expression import ExpressionType, ExpressionRenderer


class CharacterSketchIdentity(BaseModel):
    """Canonical visual drawing parameters that remain stable across all panels."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    name: str
    head_shape: str = "oval"       # "oval", "square_jaw", "angular", "round", "chiseled"
    jaw_width: float = 1.0         # Proportional multiplier
    hair_style: str = "messy_crop" # "slicked_back", "messy_crop", "long_ponytail", "side_part", "curly_volume", "buzz"
    hair_volume: float = 1.0
    height_ratio: float = 1.0      # 0.92 (compact) to 1.12 (tall)
    shoulder_width: float = 1.0    # 0.85 (slender) to 1.25 (broad)
    clothing_shape: str = "trench_coat" # "trench_coat", "tailored_suit", "casual_jacket", "hoodie"
    coat_length: float = 0.55      # Relative to body height
    accessory: str = "none"        # "glasses", "tie", "wristwatch", "scarf", "collar_pin"
    accent_color: str = "#94a3b8"

    @classmethod
    def from_reference(cls, ref: CharacterVisualReference) -> CharacterSketchIdentity:
        """Derive deterministic identity parameters from a CharacterVisualReference."""
        seed_int = get_seed_hash(f"identity_{ref.character_id}_{ref.name}")
        rng = random.Random(seed_int)

        # Parse text cues from visual reference
        props_str = " ".join(ref.signature_props) if ref.signature_props else ""
        desc = (ref.face_features + " " + ref.build + " " + ref.hair + " " + ref.clothing + " " + props_str).lower()

        # Head shape
        if "square" in desc or "chiseled" in desc:
            head_shape = "square_jaw"
            jaw_w = 1.15
        elif "sharp" in desc or "angular" in desc:
            head_shape = "angular"
            jaw_w = 0.92
        elif "round" in desc:
            head_shape = "round"
            jaw_w = 1.08
        else:
            shapes = ["oval", "square_jaw", "angular", "chiseled"]
            head_shape = shapes[seed_int % len(shapes)]
            jaw_w = 0.95 + (rng.random() * 0.2)

        # Hair style
        if "slick" in desc:
            hair_style = "slicked_back"
        elif "ponytail" in desc or "long" in desc:
            hair_style = "long_ponytail"
        elif "curl" in desc:
            hair_style = "curly_volume"
        elif "buzz" in desc or "bald" in desc:
            hair_style = "buzz"
        elif "part" in desc:
            hair_style = "side_part"
        else:
            styles = ["messy_crop", "slicked_back", "side_part", "curly_volume", "long_ponytail"]
            hair_style = styles[(seed_int >> 2) % len(styles)]

        # Clothing shape
        if "trench" in desc or "coat" in desc:
            clothing_shape = "trench_coat"
        elif "suit" in desc or "jacket" in desc or "tailored" in desc:
            clothing_shape = "tailored_suit"
        elif "hoodie" in desc:
            clothing_shape = "hoodie"
        else:
            clothing_shape = "casual_jacket"

        # Accessories
        if "glasses" in desc or "spectacles" in desc:
            accessory = "glasses"
        elif "watch" in desc or "silver watch" in desc:
            accessory = "wristwatch"
        elif "tie" in desc:
            accessory = "tie"
        elif "scarf" in desc:
            accessory = "scarf"
        else:
            accs = ["none", "glasses", "tie", "wristwatch"]
            accessory = accs[(seed_int >> 4) % len(accs)]

        # Height and build
        if "tall" in desc or "towering" in desc:
            h_ratio = 1.10
        elif "compact" in desc or "short" in desc:
            h_ratio = 0.92
        else:
            h_ratio = 0.98 + (rng.random() * 0.08)

        if "lean" in desc or "slender" in desc:
            s_width = 0.90
        elif "broad" in desc or "athletic" in desc or "heavy" in desc:
            s_width = 1.18
        else:
            s_width = 1.0

        return cls(
            character_id=ref.character_id,
            name=ref.name,
            head_shape=head_shape,
            jaw_width=jaw_w,
            hair_style=hair_style,
            hair_volume=0.9 + rng.random() * 0.25,
            height_ratio=h_ratio,
            shoulder_width=s_width,
            clothing_shape=clothing_shape,
            coat_length=0.55 if clothing_shape == "trench_coat" else 0.40,
            accessory=accessory,
            accent_color="#cbd5e1",
        )


class CharacterSketchRenderer:
    """Draws full-body or close-up character sketches with hand-drawn organic strokes."""

    def __init__(self):
        self._identities_cache: Dict[str, CharacterSketchIdentity] = {}

    def get_or_create_identity(
        self,
        char_id: str,
        name: str = "",
        ref: Optional[CharacterVisualReference] = None,
    ) -> CharacterSketchIdentity:
        if char_id in self._identities_cache:
            return self._identities_cache[char_id]

        if ref:
            ident = CharacterSketchIdentity.from_reference(ref)
        else:
            dummy_ref = CharacterVisualReference(
                character_id=char_id,
                name=name or char_id,
            )
            ident = CharacterSketchIdentity.from_reference(dummy_ref)

        self._identities_cache[char_id] = ident
        return ident

    def render_character(
        self,
        identity: CharacterSketchIdentity,
        x: float,
        y: float,
        height: float,
        pose_type: PoseType = PoseType.NEUTRAL,
        expression_type: ExpressionType = ExpressionType.NEUTRAL,
        facing_direction: float = 1.0,  # 1.0 right, -1.0 left
        seed: str = "char",
        crop_to_waist: bool = False,
        crop_to_bust: bool = False,
        stroke_color: str = "#e2e8f0",
    ) -> Tuple[str, Dict[str, Any]]:
        """Render character and return (svg_markup, metadata_dict)."""
        pose = POSE_DEFINITIONS.get(pose_type, POSE_DEFINITIONS[PoseType.NEUTRAL])
        rng = get_rng(seed)
        elements = []

        total_h = height * identity.height_ratio
        # Anatomical proportions
        # 8-head tall figure canon
        head_h = total_h * (0.16 if not crop_to_bust else 0.30)
        head_w = head_h * 0.78 * identity.jaw_width
        shoulder_w = head_w * 2.2 * identity.shoulder_width
        torso_h = total_h * 0.32

        # Joint positions
        head_cx = x + (pose.facing_direction * facing_direction * 4.0)
        head_cy = y + head_h * 0.55

        neck_top = head_cy + head_h * 0.45
        neck_bot = neck_top + head_h * 0.18
        shoulders_y = neck_bot + (head_h * 0.08)

        sh_left_x = x - (shoulder_w / 2)
        sh_right_x = x + (shoulder_w / 2)

        # 1. HEAD & HAIR
        head_seed = f"{seed}_head"
        # Face base contour
        if identity.head_shape == "square_jaw":
            # Angular jaw polygon
            jaw_pts = [
                (head_cx - head_w * 0.45, head_cy - head_h * 0.35),
                (head_cx + head_w * 0.45, head_cy - head_h * 0.35),
                (head_cx + head_w * 0.48, head_cy + head_h * 0.18),
                (head_cx + head_w * 0.32, head_cy + head_h * 0.48),
                (head_cx - head_w * 0.32, head_cy + head_h * 0.48),
                (head_cx - head_w * 0.48, head_cy + head_h * 0.18),
            ]
            elements.append(
                SketchPolygon.render(
                    jaw_pts,
                    seed=f"{head_seed}_jaw",
                    fill_color="#090d16",
                    fill_opacity=0.9,
                    stroke_color=stroke_color,
                    stroke_width=1.8,
                )
            )
        else:
            # Ellipse head base
            elements.append(
                SketchEllipse.render(
                    head_cx, head_cy, head_w * 0.5, head_h * 0.5,
                    seed=f"{head_seed}_shape",
                    stroke_color=stroke_color,
                    stroke_width=1.8,
                    fill_color="#090d16",
                    fill_opacity=0.9,
                    loops=2,
                )
            )

        # Facial Acting
        effective_facing = facing_direction * (1.0 if pose.facing_direction >= 0 else -1.0)
        face_svg = ExpressionRenderer.render(
            cx=head_cx,
            cy=head_cy,
            head_w=head_w,
            head_h=head_h,
            expression=expression_type,
            facing_dir=effective_facing,
            seed=f"{seed}_expr",
            stroke_color=stroke_color,
        )
        elements.append(face_svg)

        # Signature Glasses Accessory
        if identity.accessory == "glasses":
            gw = head_w * 0.22
            gh = head_h * 0.11
            gy = head_cy - head_h * 0.02
            gx_l = head_cx - head_w * 0.22 + (effective_facing * 4)
            gx_r = head_cx + head_w * 0.22 + (effective_facing * 4)
            elements.append(
                SketchEllipse.render(
                    gx_l, gy, gw / 2, gh / 2,
                    seed=f"{seed}_glass_l",
                    stroke_color="#f8fafc",
                    stroke_width=1.6,
                    fill_color="none",
                )
            )
            elements.append(
                SketchEllipse.render(
                    gx_r, gy, gw / 2, gh / 2,
                    seed=f"{seed}_glass_r",
                    stroke_color="#f8fafc",
                    stroke_width=1.6,
                    fill_color="none",
                )
            )
            # Bridge
            elements.append(
                SketchStroke.render_line(
                    gx_l + gw / 2, gy, gx_r - gw / 2, gy,
                    seed=f"{seed}_glass_br",
                    stroke_color="#f8fafc",
                    stroke_width=1.4,
                )
            )

        # Hair Silhouette
        hair_seed = f"{seed}_hair"
        hair_top_y = head_cy - head_h * 0.52
        if identity.hair_style == "slicked_back":
            # Swept back layered strokes
            for s in range(5):
                hy = hair_top_y + (s * 3.5)
                elements.append(
                    SketchStroke.render_line(
                        head_cx - head_w * 0.45, hy,
                        head_cx + head_w * 0.52 * effective_facing, hy - 4,
                        seed=f"{hair_seed}_{s}",
                        stroke_color="#94a3b8",
                        stroke_width=2.0,
                        passes=2,
                    )
                )
        elif identity.hair_style == "curly_volume":
            # Textured curly loops on crown
            for l in range(6):
                cx_l = head_cx - head_w * 0.45 + (l * (head_w * 0.18))
                cy_l = hair_top_y + (abs(l - 2.5) * 2.5)
                elements.append(
                    SketchEllipse.render(
                        cx_l, cy_l, head_w * 0.14, head_h * 0.14,
                        seed=f"{hair_seed}_curl_{l}",
                        stroke_color="#cbd5e1",
                        stroke_width=1.6,
                        fill_color="#1e293b",
                        fill_opacity=0.7,
                    )
                )
        elif identity.hair_style == "long_ponytail":
            # Crown stroke + trailing ponytail
            elements.append(
                SketchEllipse.render(
                    head_cx, hair_top_y + 4, head_w * 0.52, head_h * 0.28,
                    seed=f"{hair_seed}_crown",
                    stroke_color="#cbd5e1",
                    stroke_width=1.8,
                    fill_color="#0f172a",
                    fill_opacity=0.8,
                )
            )
            pt_x = head_cx - (effective_facing * head_w * 0.5)
            elements.append(
                SketchStroke.render_line(
                    pt_x, hair_top_y + 10,
                    pt_x - (effective_facing * 18), head_cy + head_h * 0.4,
                    seed=f"{hair_seed}_tail",
                    stroke_color="#cbd5e1",
                    stroke_width=3.5,
                    passes=2,
                )
            )
        else:  # messy_crop or side_part
            # Sharp angular bangs
            for b in range(5):
                bx1 = head_cx - head_w * 0.45 + (b * head_w * 0.2)
                bx2 = bx1 + (effective_facing * 8)
                elements.append(
                    SketchStroke.render_line(
                        bx1, hair_top_y, bx2, hair_top_y + head_h * 0.32,
                        seed=f"{hair_seed}_bang_{b}",
                        stroke_color="#cbd5e1",
                        stroke_width=2.2,
                        passes=2,
                    )
                )

        if crop_to_bust:
            # Render collar and quit early
            elements.append(
                SketchStroke.render_line(
                    head_cx - head_w * 0.3, neck_bot,
                    sh_left_x, shoulders_y + 15,
                    seed=f"{seed}_bust_l",
                    stroke_color=stroke_color,
                    stroke_width=2.2,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    head_cx + head_w * 0.3, neck_bot,
                    sh_right_x, shoulders_y + 15,
                    seed=f"{seed}_bust_r",
                    stroke_color=stroke_color,
                    stroke_width=2.2,
                )
            )
            return "\n  ".join(elements), {"hand_point": (head_cx, shoulders_y)}

        # 2. NECK & SHOULDERS
        elements.append(
            SketchStroke.render_line(
                head_cx - head_w * 0.2, neck_top,
                head_cx - head_w * 0.25, neck_bot,
                seed=f"{seed}_neck_l",
                stroke_color=stroke_color,
                stroke_width=1.8,
            )
        )
        elements.append(
            SketchStroke.render_line(
                head_cx + head_w * 0.2, neck_top,
                head_cx + head_w * 0.25, neck_bot,
                seed=f"{seed}_neck_r",
                stroke_color=stroke_color,
                stroke_width=1.8,
            )
        )

        # 3. TORSO & WARDROBE SILHOUETTE
        waist_y = shoulders_y + torso_h
        waist_w = shoulder_w * 0.75
        hips_y = waist_y + (total_h * 0.12)
        hips_w = shoulder_w * 0.82

        torso_pts = [
            (sh_left_x, shoulders_y),
            (sh_right_x, shoulders_y),
            (x + waist_w / 2, waist_y),
            (x + hips_w / 2, hips_y),
            (x - hips_w / 2, hips_y),
            (x - waist_w / 2, waist_y),
        ]
        elements.append(
            SketchPolygon.render(
                torso_pts,
                seed=f"{seed}_torso",
                fill_color="#090d16",
                fill_opacity=0.95,
                stroke_color=stroke_color,
                stroke_width=2.0,
            )
        )

        # Coat / Lapels / Tie
        if identity.clothing_shape == "trench_coat":
            # Lapel V-neck
            elements.append(
                SketchStroke.render_line(
                    sh_left_x + 10, shoulders_y,
                    x, waist_y - 10,
                    seed=f"{seed}_lapel_l",
                    stroke_color="#cbd5e1",
                    stroke_width=2.0,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    sh_right_x - 10, shoulders_y,
                    x, waist_y - 10,
                    seed=f"{seed}_lapel_r",
                    stroke_color="#cbd5e1",
                    stroke_width=2.0,
                )
            )
            # Belt across waist
            elements.append(
                SketchStroke.render_line(
                    x - waist_w / 2 - 2, waist_y,
                    x + waist_w / 2 + 2, waist_y,
                    seed=f"{seed}_belt",
                    stroke_color="#94a3b8",
                    stroke_width=3.2,
                )
            )
            # Coat tails extending down
            coat_bot_y = y + total_h * identity.coat_length
            if not crop_to_waist:
                elements.append(
                    SketchStroke.render_line(
                        x - hips_w / 2, hips_y,
                        x - hips_w * 0.7, coat_bot_y,
                        seed=f"{seed}_coat_l",
                        stroke_color=stroke_color,
                        stroke_width=2.2,
                    )
                )
                elements.append(
                    SketchStroke.render_line(
                        x + hips_w / 2, hips_y,
                        x + hips_w * 0.7, coat_bot_y,
                        seed=f"{seed}_coat_r",
                        stroke_color=stroke_color,
                        stroke_width=2.2,
                    )
                )
                elements.append(
                    SketchStroke.render_line(
                        x - hips_w * 0.7, coat_bot_y,
                        x + hips_w * 0.7, coat_bot_y,
                        seed=f"{seed}_coat_hem",
                        stroke_color=stroke_color,
                        stroke_width=1.8,
                    )
                )

        if identity.accessory == "tie":
            elements.append(
                SketchStroke.render_line(
                    x, neck_bot + 4,
                    x, waist_y - 8,
                    seed=f"{seed}_tie",
                    stroke_color="#f59e0b",
                    stroke_width=2.6,
                )
            )

        # 4. ARMS & HANDS
        arm_scale = total_h
        # Left Arm
        la_sh = (sh_left_x, shoulders_y)
        la_el = (
            sh_left_x + pose.left_arm.elbow[0] * arm_scale * effective_facing,
            shoulders_y + pose.left_arm.elbow[1] * arm_scale,
        )
        la_hd = (
            sh_left_x + pose.left_arm.hand[0] * arm_scale * effective_facing,
            shoulders_y + pose.left_arm.hand[1] * arm_scale,
        )

        elements.append(
            SketchStroke.render_line(
                la_sh[0], la_sh[1], la_el[0], la_el[1],
                seed=f"{seed}_larm1",
                stroke_color=stroke_color,
                stroke_width=2.4,
            )
        )
        elements.append(
            SketchStroke.render_line(
                la_el[0], la_el[1], la_hd[0], la_hd[1],
                seed=f"{seed}_larm2",
                stroke_color=stroke_color,
                stroke_width=2.2,
            )
        )
        # Left Hand (fist or grip ellipse)
        elements.append(
            SketchEllipse.render(
                la_hd[0], la_hd[1], 5.0, 5.0,
                seed=f"{seed}_lhand",
                stroke_color=stroke_color,
                stroke_width=1.5,
                fill_color="#cbd5e1",
                fill_opacity=0.6,
            )
        )

        # Right Arm
        ra_sh = (sh_right_x, shoulders_y)
        ra_el = (
            sh_right_x + pose.right_arm.elbow[0] * arm_scale * effective_facing,
            shoulders_y + pose.right_arm.elbow[1] * arm_scale,
        )
        ra_hd = (
            sh_right_x + pose.right_arm.hand[0] * arm_scale * effective_facing,
            shoulders_y + pose.right_arm.hand[1] * arm_scale,
        )

        elements.append(
            SketchStroke.render_line(
                ra_sh[0], ra_sh[1], ra_el[0], ra_el[1],
                seed=f"{seed}_rarm1",
                stroke_color=stroke_color,
                stroke_width=2.4,
            )
        )
        elements.append(
            SketchStroke.render_line(
                ra_el[0], ra_el[1], ra_hd[0], ra_hd[1],
                seed=f"{seed}_rarm2",
                stroke_color=stroke_color,
                stroke_width=2.2,
            )
        )
        # Right Hand
        elements.append(
            SketchEllipse.render(
                ra_hd[0], ra_hd[1], 5.0, 5.0,
                seed=f"{seed}_rhand",
                stroke_color=stroke_color,
                stroke_width=1.5,
                fill_color="#cbd5e1",
                fill_opacity=0.6,
            )
        )

        # Primary hand interaction point
        primary_hand = ra_hd if pose.hand_interaction_point else la_hd

        if crop_to_waist:
            return "\n  ".join(elements), {"hand_point": primary_hand}

        # 5. LEGS & FEET (if full body)
        leg_scale = total_h
        # Left Leg
        ll_hip = (x - hips_w * 0.35, hips_y)
        ll_kn = (
            ll_hip[0] + pose.left_leg.knee[0] * leg_scale * effective_facing,
            hips_y + pose.left_leg.knee[1] * leg_scale,
        )
        ll_ft = (
            ll_hip[0] + pose.left_leg.foot[0] * leg_scale * effective_facing,
            hips_y + pose.left_leg.foot[1] * leg_scale,
        )

        elements.append(
            SketchStroke.render_line(
                ll_hip[0], ll_hip[1], ll_kn[0], ll_kn[1],
                seed=f"{seed}_lleg1",
                stroke_color=stroke_color,
                stroke_width=2.4,
            )
        )
        elements.append(
            SketchStroke.render_line(
                ll_kn[0], ll_kn[1], ll_ft[0], ll_ft[1],
                seed=f"{seed}_lleg2",
                stroke_color=stroke_color,
                stroke_width=2.2,
            )
        )
        # Left Shoe
        elements.append(
            SketchStroke.render_line(
                ll_ft[0], ll_ft[1], ll_ft[0] + (effective_facing * 12), ll_ft[1] + 2,
                seed=f"{seed}_lshoe",
                stroke_color=stroke_color,
                stroke_width=3.0,
            )
        )

        # Right Leg
        rl_hip = (x + hips_w * 0.35, hips_y)
        rl_kn = (
            rl_hip[0] + pose.right_leg.knee[0] * leg_scale * effective_facing,
            hips_y + pose.right_leg.knee[1] * leg_scale,
        )
        rl_ft = (
            rl_hip[0] + pose.right_leg.foot[0] * leg_scale * effective_facing,
            hips_y + pose.right_leg.foot[1] * leg_scale,
        )

        elements.append(
            SketchStroke.render_line(
                rl_hip[0], rl_hip[1], rl_kn[0], rl_kn[1],
                seed=f"{seed}_rleg1",
                stroke_color=stroke_color,
                stroke_width=2.4,
            )
        )
        elements.append(
            SketchStroke.render_line(
                rl_kn[0], rl_kn[1], rl_ft[0], rl_ft[1],
                seed=f"{seed}_rleg2",
                stroke_color=stroke_color,
                stroke_width=2.2,
            )
        )
        # Right Shoe
        elements.append(
            SketchStroke.render_line(
                rl_ft[0], rl_ft[1], rl_ft[0] + (effective_facing * 12), rl_ft[1] + 2,
                seed=f"{seed}_rshoe",
                stroke_color=stroke_color,
                stroke_width=3.0,
            )
        )

        return "\n  ".join(elements), {"hand_point": primary_hand}
