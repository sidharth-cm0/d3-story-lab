"""Character sketch renderer and visual identity persistence.

Generates recognizable, semi-realistic film storyboard character sketches:
- 7.5 heads tall human proportions
- Paired anatomical contour lines for upper arms, forearms, thighs, and calves
- Ribcage and pelvis body masses
- Palm wedge and grouped finger hand anatomy
- Realistic wardrobe silhouettes with lapels, popped collars, and fold structures
- Hair masses with primary silhouette, clumps, and directional strand strokes
- Stable visual identity (head shape, hair volume, build, clothing) across panels
"""

from __future__ import annotations
import math
import random
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.visual_bible import CharacterVisualReference
from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchCurve,
    SketchEllipse,
    SketchPolyline,
    SketchPolygon,
    InkWashPolygon,
    CrossHatch,
    get_rng,
    get_seed_hash,
    LINE_WEIGHT_CONSTRUCTION,
    LINE_WEIGHT_INTERIOR,
    LINE_WEIGHT_CHARACTER,
    LINE_WEIGHT_FOREGROUND,
    VALUE_0,
    VALUE_1,
    VALUE_2,
    VALUE_3,
    VALUE_4,
    ACCENT_WARM_LAMP,
)
from src.storyboard.sketch.pose import (
    PoseType,
    PoseDefinition,
    POSE_DEFINITIONS,
    calculate_gesture_dynamics,
)
from src.storyboard.sketch.expression import ExpressionType, ExpressionRenderer
from src.storyboard.sketch.face import FaceSketchRenderer, FaceOrientation


class CharacterSketchIdentity(BaseModel):
    """Canonical visual drawing parameters that remain stable across all panels."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    name: str
    head_shape: str = "square_jaw"  # "square_jaw", "angular", "oval", "round"
    jaw_width: float = 1.05
    hair_style: str = "short_parted"  # "short_parted", "slicked_back", "curly_volume", "messy_crop", "long_ponytail", "buzz"
    hair_volume: float = 1.0
    height_ratio: float = 1.0       # 0.94 to 1.08
    shoulder_width: float = 1.05    # 0.90 (slender) to 1.25 (broad athletic)
    clothing_shape: str = "trench_coat"  # "trench_coat", "tailored_suit", "field_jacket", "casual_jacket"
    coat_length: float = 0.58       # Relative to body height
    accessory: str = "none"         # "glasses", "tie", "wristwatch", "scarf"
    accent_color: str = "#cbd5e1"

    @classmethod
    def from_reference(cls, ref: CharacterVisualReference) -> CharacterSketchIdentity:
        seed_int = get_seed_hash(f"identity_{ref.character_id}_{ref.name}")
        rng = random.Random(seed_int)

        props_str = " ".join(ref.signature_props) if ref.signature_props else ""
        desc = (ref.face_features + " " + ref.build + " " + ref.hair + " " + ref.clothing + " " + props_str).lower()

        # Head shape
        if "square" in desc or "chiseled" in desc or "strong" in desc:
            head_shape = "square_jaw"
            jaw_w = 1.14
        elif "sharp" in desc or "angular" in desc or "lean" in desc:
            head_shape = "angular"
            jaw_w = 0.96
        elif "round" in desc:
            head_shape = "round"
            jaw_w = 1.08
        else:
            head_shape = "square_jaw" if (seed_int % 2 == 0) else "angular"
            jaw_w = 1.0 + (rng.random() - 0.5) * 0.12

        # Hair style
        if "slick" in desc:
            hair_style = "slicked_back"
        elif "curl" in desc or "wavy" in desc:
            hair_style = "curly_volume"
        elif "ponytail" in desc or "long" in desc:
            hair_style = "long_ponytail"
        elif "buzz" in desc or "bald" in desc:
            hair_style = "buzz"
        elif "part" in desc or "short parted" in desc:
            hair_style = "short_parted"
        else:
            styles = ["short_parted", "slicked_back", "messy_crop", "curly_volume"]
            hair_style = styles[(seed_int >> 2) % len(styles)]

        # Clothing shape
        if "trench" in desc or "coat" in desc:
            clothing_shape = "trench_coat"
        elif "suit" in desc or "tailored" in desc:
            clothing_shape = "tailored_suit"
        elif "field" in desc or "military" in desc or "tactical" in desc:
            clothing_shape = "field_jacket"
        else:
            clothing_shape = "trench_coat" if (seed_int % 2 == 0) else "casual_jacket"

        # Accessory
        if "glasses" in desc:
            accessory = "glasses"
        elif "tie" in desc:
            accessory = "tie"
        elif "watch" in desc:
            accessory = "wristwatch"
        else:
            accessory = "tie" if clothing_shape == "tailored_suit" else "none"

        # Build and shoulder width (prioritize lean before broad)
        if "lean" in desc or "slender" in desc:
            s_width = 0.92
            h_ratio = 1.04
        elif "broad" in desc or "athletic" in desc or "heavy" in desc:
            s_width = 1.18
            h_ratio = 1.02
        else:
            s_width = 1.05
            h_ratio = 1.0

        return cls(
            character_id=ref.character_id,
            name=ref.name,
            head_shape=head_shape,
            jaw_width=jaw_w,
            hair_style=hair_style,
            hair_volume=0.95 + rng.random() * 0.20,
            height_ratio=h_ratio,
            shoulder_width=s_width,
            clothing_shape=clothing_shape,
            coat_length=0.58 if clothing_shape == "trench_coat" else 0.42,
            accessory=accessory,
            accent_color="#cbd5e1",
        )


class CharacterSketchRenderer:
    """Semi-realistic storyboard figure renderer constructing anatomical masses and volumes."""

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

    @staticmethod
    def _render_limb_volume(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        w1: float,
        w2: float,
        seed: str,
        stroke_color: str,
        fill_color: str = "#090d16",
        stroke_width: float = LINE_WEIGHT_CHARACTER,
        foreshortening: float = 1.0,
    ) -> str:
        """Render a curved 3D anatomical limb volume with muscular contours and cylinder volume (Section 2)."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return ""

        nx = -dy / dist
        ny = dx / dist

        w1_eff = w1 * foreshortening
        w2_eff = w2 * foreshortening

        l1 = (p1[0] - nx * (w1_eff * 0.5), p1[1] - ny * (w1_eff * 0.5))
        r1 = (p1[0] + nx * (w1_eff * 0.5), p1[1] + ny * (w1_eff * 0.5))
        l2 = (p2[0] - nx * (w2_eff * 0.5), p2[1] - ny * (w2_eff * 0.5))
        r2 = (p2[0] + nx * (w2_eff * 0.5), p2[1] + ny * (w2_eff * 0.5))

        # Quad polygon fill with deep ink tone (Section 2 & backwards compatibility)
        poly = SketchPolygon.render(
            [l1, r1, r2, l2],
            seed=f"{seed}_poly",
            stroke_color="none",
            fill_color=fill_color,
            fill_opacity=0.94,
        )
        # Tonal core shadow along one side for cylinder volume
        shadow_poly = InkWashPolygon.render(
            [l1, (l1[0] * 0.5 + r1[0] * 0.5, l1[1] * 0.5 + r1[1] * 0.5),
             (l2[0] * 0.5 + r2[0] * 0.5, l2[1] * 0.5 + r2[1] * 0.5), l2],
            seed=f"{seed}_vol_sh",
            fill_color="#020617",
            opacity=0.50,
        )

        # Curved Bézier anatomical muscle contours (deltoid/bicep/gastrocnemius belly, Section 2)
        apex_t = 0.38
        bulge = dist * 0.075 * foreshortening
        ctrl_l = (
            l1[0] + (l2[0] - l1[0]) * apex_t - nx * bulge,
            l1[1] + (l2[1] - l1[1]) * apex_t - ny * bulge,
        )
        ctrl_r = (
            r1[0] + (r2[0] - r1[0]) * apex_t + nx * (bulge * 0.65),
            r1[1] + (r2[1] - r1[1]) * apex_t + ny * (bulge * 0.65),
        )

        c_left = SketchCurve.render_quad(
            l1[0], l1[1], ctrl_l[0], ctrl_l[1], l2[0], l2[1],
            seed=f"{seed}_cl",
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            passes=2,
        )
        c_right = SketchCurve.render_quad(
            r1[0], r1[1], ctrl_r[0], ctrl_r[1], r2[0], r2[1],
            seed=f"{seed}_cr",
            stroke_color=stroke_color,
            stroke_width=stroke_width * 0.9,
            passes=2,
        )
        return f"{poly}\n  {shadow_poly}\n  {c_left}\n  {c_right}"

    @staticmethod
    def _render_hand(
        cx: float,
        cy: float,
        facing_dir: float,
        state: str = "GRIPPING",
        scale: float = 1.0,
        seed: str = "hand",
        stroke_color: str = "#e2e8f0",
        foreshortening: float = 1.0,
    ) -> str:
        """Render realistic storyboard hand anatomy: palm wedge + thumb + grouped fingers + knuckle arc (Section 7)."""
        elements = []
        eff_scale = scale * foreshortening
        pw = 10.0 * eff_scale
        ph = 12.0 * eff_scale

        # 1. Palm wedge with thenar eminence
        palm_pts = [
            (cx - (facing_dir * pw * 0.45), cy - ph * 0.42),
            (cx + (facing_dir * pw * 0.52), cy - ph * 0.32),
            (cx + (facing_dir * pw * 0.42), cy + ph * 0.52),
            (cx - (facing_dir * pw * 0.42), cy + ph * 0.42),
        ]
        elements.append(
            f'<g id="{seed}_palm">\n'
            f'  {SketchPolygon.render(palm_pts, seed=f"{seed}_palm", stroke_color=stroke_color, stroke_width=LINE_WEIGHT_INTERIOR, fill_color="#0f172a", fill_opacity=0.92)}\n'
            f'</g>'
        )

        # 2. Knuckle arc across metacarpals (curved Bézier contour)
        knuckle_top = cy - ph * 0.35
        elements.append(
            f'<g id="{seed}_knuckle_arc">\n'
            f'  {SketchCurve.render_quad(cx - (facing_dir * pw * 0.4), knuckle_top, cx, knuckle_top - (ph * 0.15), cx + (facing_dir * pw * 0.45), knuckle_top, seed=f"{seed}_knuckle_arc", stroke_color=stroke_color, stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.3, passes=1)}\n'
            f'</g>'
        )

        # 3. Opposing Thumb with 2 articulated phalanges
        thumb_joint_x = cx - (facing_dir * pw * 0.25)
        thumb_joint_y = cy + (ph * 0.05)
        thumb_tip_x = cx + (facing_dir * pw * 0.55)
        thumb_tip_y = cy - (ph * 0.15)
        elements.append(
            SketchCurve.render_quad(
                thumb_joint_x, thumb_joint_y,
                thumb_joint_x + (facing_dir * pw * 0.3), thumb_joint_y - ph * 0.2,
                thumb_tip_x, thumb_tip_y,
                seed=f"{seed}_thumb_outer",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_INTERIOR * 1.2,
                passes=2,
            )
        )

        if state in ("GRIPPING", "HOLDING_PROP"):
            # Curled fingers wrapped around object: 3 distinct finger groups (index, middle, ring/pinky)
            for f_idx in range(3):
                fy = cy - ph * 0.20 + (f_idx * ph * 0.32)
                fx1 = cx + (facing_dir * pw * 0.28)
                fx2 = fx1 + (facing_dir * pw * 0.52)
                elements.append(
                    SketchCurve.render_quad(
                        fx1, fy,
                        fx1 + (facing_dir * pw * 0.35), fy + 4,
                        fx2, fy + 2,
                        seed=f"{seed}_curl_{f_idx}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR * 1.15,
                        passes=2,
                    )
                )
                # Knuckle crease
                elements.append(
                    SketchStroke.render_line(
                        fx1 + (facing_dir * pw * 0.2), fy - 1,
                        fx1 + (facing_dir * pw * 0.2), fy + 2,
                        seed=f"{seed}_kcrease_{f_idx}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    )
                )
        elif state == "POINTING":
            # Foreshortened extended index finger pointing forward/toward camera (Section 15)
            pt_scale = 1.35 if foreshortening > 1.0 else 1.15
            elements.append(
                SketchStroke.render_line(
                    cx + (facing_dir * pw * 0.25), cy - ph * 0.22,
                    cx + (facing_dir * pw * 1.45 * pt_scale), cy - ph * 0.25,
                    seed=f"{seed}_index",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR * 1.4,
                    passes=2,
                )
            )
            # Fingertip pad / nail curve
            elements.append(
                SketchCurve.render_quad(
                    cx + (facing_dir * pw * 1.45 * pt_scale), cy - ph * 0.32,
                    cx + (facing_dir * pw * 1.55 * pt_scale), cy - ph * 0.25,
                    cx + (facing_dir * pw * 1.45 * pt_scale), cy - ph * 0.18,
                    seed=f"{seed}_index_tip",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            # Curled other 3 fingers as compact anatomical mass
            elements.append(
                SketchEllipse.render(
                    cx + (facing_dir * pw * 0.22), cy + ph * 0.26, pw * 0.38, ph * 0.28,
                    seed=f"{seed}_curled",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color="#090d16",
                )
            )
        elif state in ("OPEN", "REACHING", "QUESTIONING"):
            # 4 splayed articulated fingers (index, middle, ring, pinky)
            for i in range(4):
                ang = (-30 + i * 18) * (math.pi / 180.0)
                flen = ph * (0.82 if i in (1, 2) else 0.70)
                fx2 = cx + (facing_dir * math.cos(ang) * flen)
                fy2 = cy + (math.sin(ang) * flen)
                elements.append(
                    f'<g id="{seed}_finger_{i}">\n'
                    f'  {SketchCurve.render_quad(cx + (facing_dir * pw * 0.22), cy + (i * 2.5 - 4), cx + (facing_dir * (pw * 0.22 + math.cos(ang) * flen * 0.5)), cy + (math.sin(ang) * flen * 0.5) - 2, fx2, fy2, seed=f"{seed}_finger_{i}", stroke_color=stroke_color, stroke_width=LINE_WEIGHT_INTERIOR, passes=1)}\n'
                    f'</g>'
                )
        elif state == "DEFENSIVE":
            # Defensive open palm raised to ward off threat
            for i in range(4):
                ang = (-45 + i * 22) * (math.pi / 180.0)
                flen = ph * 0.75
                fx2 = cx + (facing_dir * math.cos(ang) * flen)
                fy2 = cy + (math.sin(ang) * flen) - 4
                elements.append(
                    SketchCurve.render_quad(
                        cx + (facing_dir * pw * 0.2), cy + (i * 2 - 3),
                        cx + (facing_dir * pw * 0.5), cy - 6,
                        fx2, fy2,
                        seed=f"{seed}_def_fin_{i}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        passes=1,
                    )
                )
        else:  # RELAXED or FIST
            elements.append(
                SketchEllipse.render(
                    cx + (facing_dir * pw * 0.2), cy + ph * 0.2, pw * 0.45, ph * 0.4,
                    seed=f"{seed}_knuckles",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color="#0f172a",
                    fill_opacity=0.9,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cx - (facing_dir * pw * 0.2), cy - ph * 0.2,
                    cx + (facing_dir * pw * 0.3), cy + ph * 0.1,
                    seed=f"{seed}_thumb_relaxed",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    passes=1,
                )
            )

        return "\n  ".join(elements)

    def render_character(
        self,
        identity: CharacterSketchIdentity,
        x: float,
        y: float,
        height: float,
        pose_type: PoseType = PoseType.NEUTRAL,
        expression_type: ExpressionType = ExpressionType.NEUTRAL,
        facing_direction: float = 1.0,
        seed: str = "char",
        crop_to_waist: bool = False,
        crop_to_bust: bool = False,
        stroke_color: str = "#e2e8f0",
    ) -> Tuple[str, Dict[str, Any]]:
        """Render character constructing semi-realistic anatomical masses."""
        pose = POSE_DEFINITIONS.get(pose_type, POSE_DEFINITIONS[PoseType.NEUTRAL])
        rng = get_rng(seed)
        elements: List[str] = []

        total_h = height * identity.height_ratio

        # 7.5 heads realistic proportion standard
        head_h = total_h * (0.133 if not crop_to_bust else 0.38)
        head_w = head_h * 0.76 * identity.jaw_width
        shoulder_w = head_w * 2.35 * identity.shoulder_width
        effective_facing = facing_direction * (1.0 if pose.facing_direction >= 0 else -1.0)

        # 1. Torso Gesture Line, Anatomical Contrapposto & Anchors (Section 2, 3, 15)
        dynamics = calculate_gesture_dynamics(pose_type, effective_facing)
        shoulder_tilt_deg = dynamics["shoulder_tilt"]
        hip_tilt_deg = dynamics["hip_tilt"]
        spine_curve_val = dynamics["spine_curve"]
        arm_foreshorten = dynamics["arm_foreshortening"]
        leg_foreshorten = dynamics["leg_foreshortening"]

        head_cx = x + (effective_facing * 3.0) + (dynamics["balance_point"] * 8.0)
        head_cy = y + (head_h * 0.52)

        neck_top = head_cy + (head_h * 0.45)
        neck_bot = neck_top + (head_h * 0.22)
        shoulders_y = neck_bot + (head_h * 0.10)

        # Spine angle & contrapposto counter-tilt
        spine_tilt = math.radians(pose.torso_angle_deg * effective_facing)
        sh_dy = math.sin(math.radians(shoulder_tilt_deg)) * (shoulder_w * 0.45)
        sh_left_x = x - (shoulder_w * 0.5) - (spine_tilt * 10.0)
        sh_left_y = shoulders_y - sh_dy
        sh_right_x = x + (shoulder_w * 0.5) - (spine_tilt * 10.0)
        sh_right_y = shoulders_y + sh_dy

        ribcage_h = total_h * 0.18
        waist_y = shoulders_y + ribcage_h
        waist_w = shoulder_w * 0.72
        waist_cx = x + (spine_curve_val * 14.0)

        pelvis_h = total_h * 0.14
        pelvis_y = waist_y + pelvis_h
        pelvis_w = shoulder_w * 0.80
        pelv_dy = math.sin(math.radians(hip_tilt_deg)) * (pelvis_w * 0.45)
        pelvis_left_y = pelvis_y - pelv_dy
        pelvis_right_y = pelvis_y + pelv_dy

        # Hand positions for output metadata
        hand_points = {
            "left": (sh_left_x + pose.left_arm.hand[0] * total_h * effective_facing * (0.85 if arm_foreshorten > 1.0 else 1.0), sh_left_y + pose.left_arm.hand[1] * total_h),
            "right": (sh_right_x + pose.right_arm.hand[0] * total_h * effective_facing * (0.85 if arm_foreshorten > 1.0 else 1.0), sh_right_y + pose.right_arm.hand[1] * total_h),
        }

        # =========================================================================
        # 1. LEGS (PAIRED ANATOMICAL CONTOURS: THIGH -> KNEE -> CALF -> SHOE WEDGE)
        # =========================================================================
        if not crop_to_waist and not crop_to_bust:
            leg_scale = total_h
            for side, joint, leg_sign in [
                ("left", pose.left_leg, -1.0),
                ("right", pose.right_leg, 1.0),
            ]:
                hip_y_side = pelvis_left_y if leg_sign < 0 else pelvis_right_y
                hip_pt = (x + (leg_sign * pelvis_w * 0.26), hip_y_side)
                side_leg_fore = leg_foreshorten if (side == "right" and leg_sign > 0 and pose.pose_type == PoseType.RUNNING) else 1.0
                knee_pt = (
                    x + (leg_sign * pelvis_w * 0.26) + (joint.knee[0] * leg_scale * effective_facing),
                    hip_y_side + (joint.knee[1] * leg_scale),
                )
                foot_pt = (
                    x + (leg_sign * pelvis_w * 0.26) + (joint.foot[0] * leg_scale * effective_facing),
                    hip_y_side + (joint.foot[1] * leg_scale),
                )

                # Thigh volume (taper from hip ~22px down to knee ~15px, with curved muscle contours)
                thigh_svg = self._render_limb_volume(
                    hip_pt, knee_pt,
                    w1=22.0 * identity.shoulder_width,
                    w2=15.0 * identity.shoulder_width,
                    seed=f"{seed}_{side}_thigh",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    foreshortening=side_leg_fore,
                )
                elements.append(thigh_svg)

                # Patella / Knee cap indication
                elements.append(
                    SketchEllipse.render(
                        knee_pt[0], knee_pt[1], 5.0 * side_leg_fore, 4.5 * side_leg_fore,
                        seed=f"{seed}_{side}_knee",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        fill_color="#090d16",
                        fill_opacity=0.9,
                    )
                )

                # Calf volume (gastrocnemius taper from knee ~15px to ankle ~9px, with curved calf muscle)
                calf_svg = self._render_limb_volume(
                    knee_pt, foot_pt,
                    w1=16.0 * identity.shoulder_width,
                    w2=9.5 * identity.shoulder_width,
                    seed=f"{seed}_{side}_calf",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    foreshortening=side_leg_fore,
                )
                elements.append(calf_svg)

                # Shoe Wedge / Block (Section 3: perspective block with heel and sole)
                shoe_dir = effective_facing
                shoe_len = 24.0 * side_leg_fore
                shoe_pts = [
                    (foot_pt[0] - (shoe_dir * 5.0), foot_pt[1]),
                    (foot_pt[0] + (shoe_dir * shoe_len), foot_pt[1] + 4.0),
                    (foot_pt[0] + (shoe_dir * (shoe_len + 2)), foot_pt[1] + 10.0),
                    (foot_pt[0] - (shoe_dir * 6.0), foot_pt[1] + 10.0),
                ]
                elements.append(
                    SketchPolygon.render(
                        shoe_pts,
                        seed=f"{seed}_{side}_shoe",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CHARACTER,
                        fill_color="#020617",
                        fill_opacity=0.95,
                    )
                )
                # Sole line
                elements.append(
                    SketchStroke.render_line(
                        shoe_pts[3][0], shoe_pts[3][1],
                        shoe_pts[2][0], shoe_pts[2][1],
                        seed=f"{seed}_{side}_sole",
                        stroke_color="#94a3b8",
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        passes=1,
                    )
                )

        # =========================================================================
        # 2. TORSO & WARDROBE VOLUME (RIBCAGE + WAIST + COAT FOLDS)
        # =========================================================================
        torso_pts = [
            (sh_left_x, sh_left_y),
            (sh_right_x, sh_right_y),
            (waist_cx + waist_w * 0.5, waist_y),
            (x + pelvis_w * 0.5, pelvis_right_y),
            (x - pelvis_w * 0.5, pelvis_left_y),
            (waist_cx - waist_w * 0.5, waist_y),
        ]
        elements.append(
            SketchPolygon.render(
                torso_pts,
                seed=f"{seed}_torso",
                fill_color="#090d16",
                fill_opacity=0.96,
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
            )
        )

        # Wardrobe Silhouettes & Folds (Section 8)
        if identity.clothing_shape == "trench_coat":
            # Popped storm collar
            collar_pts = [
                (sh_left_x + 10, shoulders_y - 8),
                (head_cx - head_w * 0.40, neck_top + 4),
                (head_cx + head_w * 0.40, neck_top + 4),
                (sh_right_x - 10, shoulders_y - 8),
                (sh_right_x - 4, shoulders_y + 8),
                (sh_left_x + 4, shoulders_y + 8),
            ]
            elements.append(
                SketchPolygon.render(
                    collar_pts,
                    seed=f"{seed}_collar",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#0f172a",
                    fill_opacity=0.95,
                )
            )

            # Notched Lapels overlapping on chest
            lapel_left = [
                (sh_left_x + 12, shoulders_y + 4),
                (head_cx - 4, waist_y - 12),
                (sh_left_x + 22, shoulders_y + 24),
            ]
            elements.append(
                SketchPolyline.render(
                    lapel_left,
                    seed=f"{seed}_lapel_l",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR * 1.2,
                    passes=2,
                )
            )
            lapel_right = [
                (sh_right_x - 12, shoulders_y + 4),
                (head_cx + 4, waist_y - 12),
                (sh_right_x - 22, shoulders_y + 24),
            ]
            elements.append(
                SketchPolyline.render(
                    lapel_right,
                    seed=f"{seed}_lapel_r",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR * 1.2,
                    passes=2,
                )
            )

            # Trenchcoat Cinch Belt & Buckle
            elements.append(
                SketchStroke.render_line(
                    x - waist_w * 0.52, waist_y,
                    x + waist_w * 0.52, waist_y,
                    seed=f"{seed}_belt",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER * 1.5,
                    passes=2,
                )
            )
            # Buckle
            elements.append(
                SketchPolygon.render(
                    [(x - 6, waist_y - 4), (x + 6, waist_y - 4), (x + 6, waist_y + 4), (x - 6, waist_y + 4)],
                    seed=f"{seed}_buckle",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color="#334155",
                )
            )

            # Trenchcoat Hem / Skirt (responds dynamically to walk/run pose)
            if not crop_to_waist and not crop_to_bust:
                coat_bot_y = y + (total_h * identity.coat_length)
                flare_offset = (pose.torso_angle_deg * effective_facing * 1.8)
                coat_pts = [
                    (x - pelvis_w * 0.5, waist_y + 8),
                    (x + pelvis_w * 0.5, waist_y + 8),
                    (x + pelvis_w * 0.75 - flare_offset, coat_bot_y),
                    (x - pelvis_w * 0.75 - flare_offset, coat_bot_y),
                ]
                elements.append(
                    SketchPolygon.render(
                        coat_pts,
                        seed=f"{seed}_coat_skirt",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CHARACTER,
                        fill_color="#090d16",
                        fill_opacity=0.96,
                    )
                )
                # Dynamic fold creases
                for f_idx in range(3):
                    fx = x - pelvis_w * 0.3 + (f_idx * pelvis_w * 0.3)
                    elements.append(
                        SketchStroke.render_line(
                            fx, waist_y + 12,
                            fx - flare_offset * 0.6, coat_bot_y - 6,
                            seed=f"{seed}_coat_fold_{f_idx}",
                            stroke_color="#334155",
                            stroke_width=LINE_WEIGHT_INTERIOR,
                            passes=1,
                        )
                    )

        elif identity.clothing_shape == "tailored_suit":
            # Suit jacket lapel & shirt collar
            elements.append(
                SketchStroke.render_line(
                    head_cx - 6, neck_bot, head_cx, waist_y - 10,
                    seed=f"{seed}_suit_l",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR * 1.2,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    head_cx + 6, neck_bot, head_cx, waist_y - 10,
                    seed=f"{seed}_suit_r",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR * 1.2,
                )
            )
            # Necktie
            elements.append(
                SketchPolygon.render(
                    [
                        (head_cx - 3, neck_bot + 2),
                        (head_cx + 3, neck_bot + 2),
                        (head_cx + 4, waist_y - 8),
                        (head_cx, waist_y - 2),
                        (head_cx - 4, waist_y - 8),
                    ],
                    seed=f"{seed}_tie",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color=ACCENT_WARM_LAMP,
                    fill_opacity=0.85,
                )
            )

        # =========================================================================
        # 3. ARMS & HANDS (PAIRED VOLUMES: UPPER ARM -> ELBOW -> FOREARM -> HAND)
        # =========================================================================
        arm_scale = total_h
        for side, joint, sh_root, h_state in [
            ("left", pose.left_arm, (sh_left_x, shoulders_y), pose_type.name),
            ("right", pose.right_arm, (sh_right_x, shoulders_y), pose_type.name),
        ]:
            side_arm_fore = arm_foreshorten if (side == "right" and arm_foreshorten > 1.0) else 1.0
            el_pt = (
                sh_root[0] + (joint.elbow[0] * arm_scale * effective_facing * (0.85 if side_arm_fore > 1.0 else 1.0)),
                sh_root[1] + (joint.elbow[1] * arm_scale),
            )
            hd_pt = (
                sh_root[0] + (joint.hand[0] * arm_scale * effective_facing * (0.85 if side_arm_fore > 1.0 else 1.0)),
                sh_root[1] + (joint.hand[1] * arm_scale),
            )

            # Upper arm volume (taper shoulder ~16px to elbow ~12px)
            u_arm = self._render_limb_volume(
                sh_root, el_pt,
                w1=16.0 * identity.shoulder_width,
                w2=12.0 * identity.shoulder_width,
                seed=f"{seed}_{side}_uarm",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
                foreshortening=side_arm_fore,
            )
            elements.append(u_arm)

            # Elbow compression folds (fabric crumples on inside angle)
            elements.append(
                SketchStroke.render_line(
                    el_pt[0] - 4, el_pt[1] - 2,
                    el_pt[0] + 4, el_pt[1] + 2,
                    seed=f"{seed}_{side}_elbow_crease",
                    stroke_color="#334155",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.5,
                    passes=1,
                )
            )

            # Forearm volume (taper elbow ~12px to wrist ~8.5px)
            f_arm = self._render_limb_volume(
                el_pt, hd_pt,
                w1=13.0 * identity.shoulder_width,
                w2=8.5 * identity.shoulder_width,
                seed=f"{seed}_{side}_farm",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
                foreshortening=side_arm_fore,
            )
            elements.append(f_arm)

            # Storyboard Hand (Section 7, 9)
            hand_state = "HOLDING_PROP" if "FLASHLIGHT" in h_state or "OBJECT" in h_state else "RELAXED"
            if side == "right" and "FLASHLIGHT" in h_state:
                hand_state = "GRIPPING"
            elif pose.pose_type in (PoseType.RUNNING, PoseType.WALKING):
                hand_state = "FIST"
            elif pose.pose_type == PoseType.QUESTIONING:
                hand_state = "QUESTIONING"
            elif pose.pose_type == PoseType.EVASIVE:
                hand_state = "DEFENSIVE"
            hand_svg = self._render_hand(
                hd_pt[0], hd_pt[1],
                facing_dir=effective_facing,
                state=hand_state,
                scale=identity.height_ratio,
                seed=f"{seed}_{side}_hand",
                stroke_color=stroke_color,
                foreshortening=side_arm_fore,
            )
            elements.append(hand_svg)

        # =========================================================================
        # 4. NECK & JAW FOUNDATION
        # =========================================================================
        # Neck paired tapered lines
        elements.append(
            SketchStroke.render_line(
                head_cx - (head_w * 0.22), neck_top,
                head_cx - (head_w * 0.26), neck_bot,
                seed=f"{seed}_neck_l",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_INTERIOR,
                passes=1,
            )
        )
        elements.append(
            SketchStroke.render_line(
                head_cx + (head_w * 0.22), neck_top,
                head_cx + (head_w * 0.26), neck_bot,
                seed=f"{seed}_neck_r",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_INTERIOR,
                passes=1,
            )
        )

        # Cranial ellipse & jaw polygon base
        jaw_h = head_h * 0.48
        chin_w = head_w * (0.42 if identity.head_shape == "square_jaw" else 0.30)
        jaw_pts = [
            (head_cx - head_w * 0.46, head_cy - head_h * 0.15),
            (head_cx + head_w * 0.46, head_cy - head_h * 0.15),
            (head_cx + head_w * 0.42, head_cy + jaw_h * 0.5),
            (head_cx + chin_w * 0.5, head_cy + jaw_h),
            (head_cx - chin_w * 0.5, head_cy + jaw_h),
            (head_cx - head_w * 0.42, head_cy + jaw_h * 0.5),
        ]
        elements.append(
            SketchPolygon.render(
                jaw_pts,
                seed=f"{seed}_jaw_base",
                fill_color="#090d16",
                fill_opacity=0.96,
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
            )
        )

        # Cranial dome
        elements.append(
            SketchEllipse.render(
                head_cx, head_cy - (head_h * 0.12), head_w * 0.48, head_h * 0.44,
                seed=f"{seed}_cranium",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
                fill_color="#090d16",
                fill_opacity=0.96,
                loops=2,
            )
        )

        # =========================================================================
        # 5. FACIAL ACTING VIA FaceSketchRenderer (Section 5 & 6)
        # =========================================================================
        f_orient = (
            FaceOrientation.PROFILE_LEFT if effective_facing < -0.7
            else FaceOrientation.THREE_QUARTER_LEFT if effective_facing < -0.2
            else FaceOrientation.PROFILE_RIGHT if effective_facing > 0.7
            else FaceOrientation.THREE_QUARTER_RIGHT if effective_facing > 0.2
            else FaceOrientation.FRONT
        )
        is_wide_shot = (height < 160.0) and not (crop_to_bust or crop_to_waist)
        is_close = crop_to_bust or crop_to_waist or (head_h >= 45.0)

        face_svg = FaceSketchRenderer.render_face(
            cx=head_cx,
            cy=head_cy,
            head_w=head_w,
            head_h=head_h,
            expression=expression_type,
            orientation=f_orient,
            intensity=0.88,
            is_close_up=is_close,
            is_wide=is_wide_shot,
            seed=f"{seed}_face_features",
            stroke_color=stroke_color,
            jaw_shape=identity.head_shape,
        )
        elements.append(face_svg)

        # =========================================================================
        # 6. HAIR AS MASS (PRIMARY SILHOUETTE + 6-8 SECONDARY CLUMPS + STRANDS, Section 6)
        # =========================================================================
        hair_top_y = head_cy - (head_h * 0.52)
        hair_h = head_h * 0.42 * identity.hair_volume

        if identity.hair_style == "slicked_back":
            # Primary silhouette mass swept backwards
            hair_pts = [
                (head_cx - head_w * 0.52, head_cy - head_h * 0.12),
                (head_cx - head_w * 0.48, hair_top_y - 2),
                (head_cx, hair_top_y - 4),
                (head_cx + head_w * 0.50, hair_top_y - 1),
                (head_cx + head_w * 0.56, head_cy - head_h * 0.05),
                (head_cx + (effective_facing * head_w * 0.22), head_cy - head_h * 0.35),
            ]
            elements.append(
                SketchPolygon.render(
                    hair_pts,
                    seed=f"{seed}_hair_slick",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#020617",
                    fill_opacity=0.98,
                )
            )
            # 6 secondary swept clumps
            for s in range(6):
                sx = head_cx - head_w * 0.40 + (s * head_w * 0.16)
                sy = hair_top_y + (abs(s - 3) * 1.5)
                elements.append(
                    SketchCurve.render_quad(
                        sx, sy,
                        sx + (effective_facing * 8), sy + hair_h * 0.35,
                        sx + (effective_facing * 12), sy + hair_h * 0.65,
                        seed=f"{seed}_strand_{s}",
                        stroke_color="#94a3b8",
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        passes=1,
                    )
                )
            # Hair highlight gap
            elements.append(
                SketchStroke.render_line(
                    head_cx - head_w * 0.15, hair_top_y + 3,
                    head_cx + head_w * 0.20, hair_top_y + 2,
                    seed=f"{seed}_hair_hi",
                    stroke_color="#cbd5e1",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.6,
                    passes=1,
                )
            )

        elif identity.hair_style == "curly_volume":
            # Primary voluminous silhouette mass
            curly_base = [
                (head_cx - head_w * 0.58, head_cy - head_h * 0.05),
                (head_cx - head_w * 0.54, hair_top_y - 6),
                (head_cx - head_w * 0.20, hair_top_y - 10),
                (head_cx + head_w * 0.25, hair_top_y - 9),
                (head_cx + head_w * 0.58, hair_top_y - 4),
                (head_cx + head_w * 0.60, head_cy - head_h * 0.05),
                (head_cx + head_w * 0.35, head_cy - head_h * 0.30),
                (head_cx - head_w * 0.35, head_cy - head_h * 0.30),
            ]
            elements.append(
                SketchPolygon.render(
                    curly_base,
                    seed=f"{seed}_curly_mass",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#020617",
                    fill_opacity=0.98,
                )
            )
            # 7 distinct secondary faceted/curved clumps (no circular loops!)
            for c_idx in range(7):
                c_fx = head_cx - head_w * 0.48 + (c_idx * head_w * 0.16)
                c_fy = hair_top_y - 2 + ((c_idx % 3) * 3.5)
                # Curved curl crescent
                elements.append(
                    SketchCurve.render_quad(
                        c_fx - 6, c_fy + 2,
                        c_fx, c_fy - 6,
                        c_fx + 7, c_fy + 3,
                        seed=f"{seed}_curl_arc_{c_idx}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        passes=1,
                    )
                )
            # Directional curl tendrils
            for t_idx in range(4):
                tx = head_cx - head_w * 0.35 + (t_idx * head_w * 0.24)
                ty = head_cy - head_h * 0.28
                elements.append(
                    SketchCurve.render_quad(
                        tx, ty - 6,
                        tx + (effective_facing * 5), ty - 2,
                        tx + (effective_facing * 2), ty + 3,
                        seed=f"{seed}_curl_tendril_{t_idx}",
                        stroke_color="#94a3b8",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        passes=1,
                    )
                )

        elif identity.hair_style == "buzz":
            # Tight skull-clinging silhouette mass
            elements.append(
                SketchPolygon.render(
                    [
                        (head_cx - head_w * 0.48, head_cy - head_h * 0.15),
                        (head_cx - head_w * 0.44, hair_top_y + 2),
                        (head_cx + head_w * 0.44, hair_top_y + 2),
                        (head_cx + head_w * 0.48, head_cy - head_h * 0.15),
                        (head_cx, head_cy - head_h * 0.35),
                    ],
                    seed=f"{seed}_buzz_mass",
                    stroke_color="#475569",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    fill_color="#090d16",
                    fill_opacity=0.75,
                )
            )
            # Stippled graphite texture
            elements.append(
                SketchStroke.render_line(
                    head_cx - head_w * 0.35, hair_top_y + 3,
                    head_cx + head_w * 0.35, hair_top_y + 3,
                    seed=f"{seed}_buzz_stipple",
                    stroke_color="#64748b",
                    stroke_width=0.8,
                    passes=1,
                )
            )

        else:  # short_parted or messy_crop
            # Confident graphic novel clump clusters (primary mass)
            hair_pts = [
                (head_cx - head_w * 0.52, head_cy - head_h * 0.10),
                (head_cx - head_w * 0.48, hair_top_y - 4),
                (head_cx - head_w * 0.15, hair_top_y - 7),
                (head_cx + head_w * 0.20, hair_top_y - 6),
                (head_cx + head_w * 0.52, hair_top_y - 2),
                (head_cx + head_w * 0.54, head_cy - head_h * 0.08),
                (head_cx + (effective_facing * head_w * 0.25), head_cy - head_h * 0.28),
                (head_cx - (effective_facing * head_w * 0.15), head_cy - head_h * 0.28),
            ]
            elements.append(
                SketchPolygon.render(
                    hair_pts,
                    seed=f"{seed}_hair_clump",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#020617",
                    fill_opacity=0.98,
                )
            )
            # Distinct parting cut line
            part_x = head_cx - (head_w * 0.15)
            elements.append(
                SketchStroke.render_line(
                    part_x, hair_top_y - 2,
                    part_x + (effective_facing * 10), hair_top_y + hair_h * 0.75,
                    seed=f"{seed}_hair_part",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    passes=2,
                )
            )
            # 6 secondary clumps with directional flow
            for k in range(6):
                clump_x = head_cx - head_w * 0.38 + (k * head_w * 0.15)
                clump_y = hair_top_y + ((k % 2) * 3)
                elements.append(
                    SketchCurve.render_quad(
                        clump_x, clump_y,
                        clump_x + (effective_facing * 6), clump_y + hair_h * 0.4,
                        clump_x + (effective_facing * 3), clump_y + hair_h * 0.65,
                        seed=f"{seed}_sec_clump_{k}",
                        stroke_color="#94a3b8",
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        passes=1,
                    )
                )
            # Paper highlight gap along crest
            elements.append(
                SketchStroke.render_line(
                    part_x + 6, hair_top_y - 1,
                    part_x + 18, hair_top_y - 1,
                    seed=f"{seed}_part_hi",
                    stroke_color="#cbd5e1",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.7,
                    passes=1,
                )
            )

        meta = {
            "hand_points": hand_points,
            "hand_point": hand_points.get("right") or hand_points.get("left"),
            "head_center": (head_cx, head_cy),
        }
        return "\n  ".join(elements), meta
