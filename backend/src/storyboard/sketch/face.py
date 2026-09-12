"""Face construction and facial acting renderer for cinematic storyboards.

Implements anatomical facial construction:
- Cranial ellipse and jaw/chin polygon
- Vertical facial center line, brow line, eye line, and cheek planes
- Face orientations: FRONT, THREE_QUARTER_LEFT, THREE_QUARTER_RIGHT, PROFILE_LEFT, PROFILE_RIGHT, LOOKING_DOWN, LOOKING_UP
- Realistic anatomical eyes with upper/lower lids, iris, pupil, and catchlight (NEVER dot eyes)
- Nose bridge, ball, nostril wing, and drop shadow
- Mouth with upper bow, center line, and lower lip shadow
- Emotional expressions (intensity 0.0 - 1.0) for genuine character acting
- Dynamic LOD for close-up portrait shots vs wide shots
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List

from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchEllipse,
    SketchPolyline,
    SketchPolygon,
    InkWashPolygon,
    CrossHatch,
    get_rng,
    LINE_WEIGHT_CONSTRUCTION,
    LINE_WEIGHT_INTERIOR,
    LINE_WEIGHT_CHARACTER,
    VALUE_0,
    VALUE_1,
    VALUE_3,
    VALUE_4,
)
from src.storyboard.sketch.expression import ExpressionType, EXPRESSION_PROFILES, FacialFeatures


class FaceOrientation(str, Enum):
    """Supported 3D face orientations in camera perspective."""
    FRONT = "FRONT"
    THREE_QUARTER_LEFT = "THREE_QUARTER_LEFT"
    THREE_QUARTER_RIGHT = "THREE_QUARTER_RIGHT"
    PROFILE_LEFT = "PROFILE_LEFT"
    PROFILE_RIGHT = "PROFILE_RIGHT"
    LOOKING_DOWN = "LOOKING_DOWN"
    LOOKING_UP = "LOOKING_UP"


class FaceSketchRenderer:
    """Renders semi-realistic graphic-novel storyboard faces with anatomical planes."""

    @staticmethod
    def render_face(
        cx: float,
        cy: float,
        head_w: float,
        head_h: float,
        expression: ExpressionType = ExpressionType.NEUTRAL,
        orientation: FaceOrientation = FaceOrientation.THREE_QUARTER_RIGHT,
        intensity: float = 0.85,
        is_close_up: bool = False,
        is_wide: bool = False,
        seed: str = "face",
        stroke_color: str = "#e2e8f0",
        wash_color: str = "#0f172a",
        jaw_shape: str = "square_jaw",
    ) -> str:
        """Render a complete anatomical face sketch with orientation, expression, and camera LOD."""
        # For wide shots or very small heads: silhouette only (Section 4)
        if is_wide or head_h < 36.0:
            return ""

        rng = get_rng(seed)
        elements: List[str] = []

        feat = EXPRESSION_PROFILES.get(expression, EXPRESSION_PROFILES[ExpressionType.NEUTRAL])
        line_w = LINE_WEIGHT_INTERIOR if not is_close_up else 1.4

        # 1. Perspective offsets based on orientation
        is_profile = orientation in (FaceOrientation.PROFILE_LEFT, FaceOrientation.PROFILE_RIGHT)
        is_left = orientation in (FaceOrientation.THREE_QUARTER_LEFT, FaceOrientation.PROFILE_LEFT)
        facing_dir = -1.0 if is_left else 1.0

        if is_profile:
            center_x_offset = facing_dir * head_w * 0.28
            far_eye_visible = False
        elif orientation in (FaceOrientation.THREE_QUARTER_LEFT, FaceOrientation.THREE_QUARTER_RIGHT):
            center_x_offset = facing_dir * head_w * 0.16
            far_eye_visible = True
        else:
            center_x_offset = 0.0
            far_eye_visible = True

        v_shift = 0.0
        if orientation == FaceOrientation.LOOKING_DOWN:
            v_shift = head_h * 0.12
        elif orientation == FaceOrientation.LOOKING_UP:
            v_shift = -head_h * 0.12

        # 2. Facial Key Planes & Guidelines
        brow_y = cy - (head_h * 0.08) + v_shift + (feat.eyebrow_raise * 1.2 * intensity)
        eye_y = brow_y + (head_h * 0.11)
        nose_base_y = cy + (head_h * 0.18) + (v_shift * 0.8)
        mouth_y = cy + (head_h * 0.32) + (v_shift * 0.6)
        chin_y = cy + (head_h * 0.48) + (v_shift * 0.4)

        face_cx = cx + center_x_offset

        # Forehead Plane & Temple Contours for Close-ups (Section 4)
        if is_close_up:
            forehead_y = cy - (head_h * 0.32) + v_shift
            elements.append(
                SketchStroke.render_line(
                    face_cx - head_w * 0.32, forehead_y,
                    face_cx + head_w * 0.32, forehead_y,
                    seed=f"{seed}_forehead_plane",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.45,
                    passes=1,
                )
            )
            # Temple ridge line
            temple_x = face_cx - (facing_dir * head_w * 0.40)
            elements.append(
                SketchStroke.render_line(
                    temple_x, forehead_y - 4,
                    temple_x + (facing_dir * 4), brow_y - 2,
                    seed=f"{seed}_temple",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.55,
                    passes=1,
                )
            )

        # 3. Eye Socket Shadow Wash (Anatomical depth under the brow shelf)
        left_eye_cx = cx - (head_w * 0.24) if not is_profile else (cx - head_w * 0.08 if is_left else cx + head_w * 0.20)
        right_eye_cx = cx + (head_w * 0.24) if not is_profile else (cx - head_w * 0.20 if is_left else cx + head_w * 0.08)

        if not is_profile:
            elements.append(
                InkWashPolygon.render(
                    [
                        (left_eye_cx - 10, brow_y - 2),
                        (left_eye_cx + 10, brow_y - 2),
                        (left_eye_cx + 8, eye_y + 8),
                        (left_eye_cx - 8, eye_y + 8),
                    ],
                    seed=f"{seed}_lsocket",
                    fill_color=wash_color,
                    opacity=0.35,
                )
            )
            elements.append(
                InkWashPolygon.render(
                    [
                        (right_eye_cx - 10, brow_y - 2),
                        (right_eye_cx + 10, brow_y - 2),
                        (right_eye_cx + 8, eye_y + 8),
                        (right_eye_cx - 8, eye_y + 8),
                    ],
                    seed=f"{seed}_rsocket",
                    fill_color=wash_color,
                    opacity=0.35,
                )
            )

        # 4. Eyebrows (Confidently stroked architectural arches with hair texture)
        eyebrow_w = head_w * 0.24
        brow_slant = feat.eyebrow_angle_deg * intensity

        # Left Brow
        lb_in_x = face_cx - (head_w * 0.06)
        lb_in_y = brow_y + (brow_slant * 0.2)
        lb_out_x = left_eye_cx - (eyebrow_w * 0.5)
        lb_out_y = brow_y - (brow_slant * 0.3)

        if not (is_profile and not is_left):
            elements.append(
                SketchStroke.render_line(
                    lb_in_x, lb_in_y, lb_out_x, lb_out_y,
                    seed=f"{seed}_lbrow",
                    stroke_color=stroke_color,
                    stroke_width=line_w * 1.4,
                    passes=2,
                )
            )
            if is_close_up:
                elements.append(
                    SketchStroke.render_line(
                        lb_in_x - 2, lb_in_y - 2, lb_out_x + 3, lb_out_y - 1,
                        seed=f"{seed}_lbrow_h",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        passes=1,
                    )
                )

        # Right Brow (supports asymmetry for suspicious/confused acting)
        asym_shift = feat.brow_asymmetry * intensity * 0.8
        rb_in_x = face_cx + (head_w * 0.06)
        rb_in_y = brow_y + (brow_slant * 0.2) - asym_shift
        rb_out_x = right_eye_cx + (eyebrow_w * 0.5)
        rb_out_y = brow_y - (brow_slant * 0.3) - (asym_shift * 1.2)

        if not (is_profile and is_left):
            elements.append(
                SketchStroke.render_line(
                    rb_in_x, rb_in_y, rb_out_x, rb_out_y,
                    seed=f"{seed}_rbrow",
                    stroke_color=stroke_color,
                    stroke_width=line_w * 1.4,
                    passes=2,
                )
            )
            if is_close_up:
                elements.append(
                    SketchStroke.render_line(
                        rb_in_x + 2, rb_in_y - 2, rb_out_x - 3, rb_out_y - 1,
                        seed=f"{seed}_rbrow_h",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        passes=1,
                    )
                )

        # 5. Glabella / Frown Creases
        if feat.jaw_tension_lines or expression in (ExpressionType.ANGRY, ExpressionType.DETERMINED, ExpressionType.SUSPICIOUS):
            elements.append(
                SketchStroke.render_line(
                    face_cx - 2, brow_y - 5, face_cx - 2, brow_y + 4,
                    seed=f"{seed}_frown_l",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.7,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    face_cx + 2, brow_y - 6, face_cx + 2, brow_y + 3,
                    seed=f"{seed}_frown_r",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.7,
                )
            )

        # 6. Eyes (Anatomical Eyelids, Iris, Pupil, Highlight Catchlight)
        eye_w = head_w * 0.18
        eye_open = max(0.35, feat.eye_openness * (1.0 + (feat.eye_openness - 1.0) * intensity))
        eye_h = eye_w * 0.50 * eye_open

        def render_eye(eye_center_x: float, eye_center_y: float, eye_seed: str, foreshorten: float = 1.0) -> List[str]:
            e_elements = []
            ew = eye_w * foreshorten
            eh = eye_h

            # Upper eyelid (strong dark contour with gentle almond curve)
            c_y1 = eye_center_y - eh * 0.8
            p_ul = [
                (eye_center_x - ew * 0.5, eye_center_y),
                (eye_center_x - ew * 0.1, c_y1),
                (eye_center_x + ew * 0.5, eye_center_y + 0.5),
            ]
            e_elements.append(
                SketchPolyline.render(
                    p_ul,
                    seed=f"{eye_seed}_ulid",
                    stroke_color=stroke_color,
                    stroke_width=line_w * 1.3,
                    passes=2,
                )
            )

            # Lower eyelid (subtle thin contour)
            p_ll = [
                (eye_center_x - ew * 0.45, eye_center_y + 1),
                (eye_center_x, eye_center_y + eh * 0.7),
                (eye_center_x + ew * 0.45, eye_center_y + 1),
            ]
            e_elements.append(
                SketchPolyline.render(
                    p_ll,
                    seed=f"{eye_seed}_llid",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.2,
                    passes=1,
                )
            )

            # Iris (Round disc clipped inside eyelid boundary)
            iris_r = min(ew * 0.35, eh * 0.75)
            pupil_x = eye_center_x + (feat.pupil_offset_x * ew * 0.25)
            pupil_y = eye_center_y + (feat.pupil_offset_y * eh * 0.20)

            # Iris dark ring
            e_elements.append(
                SketchEllipse.render(
                    pupil_x, pupil_y, iris_r, iris_r * 0.95,
                    seed=f"{eye_seed}_iris",
                    stroke_color="#1e293b",
                    stroke_width=1.0,
                    fill_color="#090d16",
                    fill_opacity=0.92,
                )
            )

            # Specular catchlight (white reflection dot on upper-left iris edge)
            e_elements.append(
                f'<circle cx="{pupil_x - (iris_r * 0.3):.1f}" cy="{pupil_y - (iris_r * 0.3):.1f}" '
                f'r="1.2" fill="{VALUE_0}" opacity="0.95"/>'
            )

            # Upper eyelid crease (fold of skin above eye)
            if is_close_up:
                e_elements.append(
                    SketchStroke.render_line(
                        eye_center_x - ew * 0.45, eye_center_y - eh - 1.5,
                        eye_center_x + ew * 0.40, eye_center_y - eh - 1.0,
                        seed=f"{eye_seed}_crease",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        opacity=0.6,
                    )
                )

            return e_elements

        # Render Left Eye
        if not (is_profile and not is_left):
            foreshorten = 0.75 if (is_left and not is_profile) else 1.0
            elements.extend(render_eye(left_eye_cx, eye_y, f"{seed}_leye", foreshorten))

        # Render Right Eye
        if not (is_profile and is_left):
            foreshorten = 0.75 if (not is_left and not is_profile and orientation != FaceOrientation.FRONT) else 1.0
            elements.extend(render_eye(right_eye_cx, eye_y, f"{seed}_reye", foreshorten))

        # 7. Nose Construction
        nose_bridge_top_x = face_cx
        nose_tip_x = face_cx + (facing_dir * 5.0 if not is_profile else facing_dir * head_w * 0.18)
        nose_tip_y = nose_base_y - 2.0

        # Bridge line from brow down to tip
        elements.append(
            SketchStroke.render_line(
                nose_bridge_top_x, brow_y + 4,
                nose_tip_x, nose_tip_y,
                seed=f"{seed}_nose_bridge",
                stroke_color=stroke_color,
                stroke_width=line_w * 0.95,
                passes=1,
            )
        )

        # Nose tip ball / septum
        elements.append(
            SketchStroke.render_line(
                nose_tip_x, nose_tip_y,
                face_cx, nose_base_y,
                seed=f"{seed}_nose_base",
                stroke_color=stroke_color,
                stroke_width=line_w * 1.1,
                passes=1,
            )
        )

        # Nostril wing curve on far side
        nostril_x = face_cx + (facing_dir * 7.0)
        elements.append(
            SketchStroke.render_line(
                nostril_x, nose_base_y - 3,
                nostril_x + (facing_dir * 2), nose_base_y,
                seed=f"{seed}_nostril",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.4,
                passes=1,
            )
        )

        # Cast shadow under nose
        elements.append(
            InkWashPolygon.render(
                [
                    (face_cx - 4, nose_base_y),
                    (face_cx + 4, nose_base_y),
                    (face_cx + 2, nose_base_y + 3),
                    (face_cx - 2, nose_base_y + 3),
                ],
                seed=f"{seed}_nose_sh",
                fill_color=wash_color,
                opacity=0.45,
            )
        )

        # Philtrum & Nasolabial Fold (Section 4)
        if is_close_up:
            elements.append(
                SketchStroke.render_line(
                    face_cx - 1.5, nose_base_y + 1,
                    face_cx - 1.5, mouth_y - 2,
                    seed=f"{seed}_philtrum_l",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.5,
                    passes=1,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    face_cx + 1.5, nose_base_y + 1,
                    face_cx + 1.5, mouth_y - 2,
                    seed=f"{seed}_philtrum_r",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.5,
                    passes=1,
                )
            )
            nl_x1 = face_cx + (facing_dir * 9.0)
            elements.append(
                SketchStroke.render_line(
                    nl_x1, nose_base_y + 1,
                    nl_x1 + (facing_dir * 4.0), mouth_y + 4,
                    seed=f"{seed}_nasolabial",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.1,
                    opacity=0.6,
                    passes=1,
                )
            )

        # 8. Mouth Construction
        mouth_w = head_w * 0.28 * feat.mouth_width_factor
        m_curve = feat.mouth_curve * 6.0 * intensity
        m_open = feat.mouth_openness * 10.0 * intensity

        mx_l = face_cx - (mouth_w * 0.5)
        mx_r = face_cx + (mouth_w * 0.5)

        if m_open < 1.5:
            # Closed mouth line with corner depression dots
            m_mid_y = mouth_y - m_curve
            elements.append(
                SketchPolyline.render(
                    [(mx_l, mouth_y), (face_cx, m_mid_y), (mx_r, mouth_y)],
                    seed=f"{seed}_mouth_c",
                    stroke_color=stroke_color,
                    stroke_width=line_w * 1.25,
                    passes=2,
                )
            )
            elements.append(f'<circle cx="{mx_l:.1f}" cy="{mouth_y:.1f}" r="0.9" fill="{stroke_color}"/>')
            elements.append(f'<circle cx="{mx_r:.1f}" cy="{mouth_y:.1f}" r="0.9" fill="{stroke_color}"/>')
        else:
            elements.append(
                SketchPolygon.render(
                    [
                        (mx_l, mouth_y),
                        (face_cx, mouth_y - m_curve),
                        (mx_r, mouth_y),
                        (face_cx + 2, mouth_y + m_open),
                        (face_cx - 2, mouth_y + m_open),
                    ],
                    seed=f"{seed}_mouth_open",
                    stroke_color=stroke_color,
                    stroke_width=line_w * 1.2,
                    fill_color="#090d16",
                    fill_opacity=0.95,
                )
            )

        # Lower lip underside shadow stroke
        elements.append(
            SketchStroke.render_line(
                face_cx - (mouth_w * 0.28), mouth_y + (m_open * 0.5) + 4.5,
                face_cx + (mouth_w * 0.28), mouth_y + (m_open * 0.5) + 4.5,
                seed=f"{seed}_lower_lip",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_INTERIOR,
                passes=1,
            )
        )

        # 9. Jaw & Chin Contour
        chin_w = head_w * (0.35 if jaw_shape == "square_jaw" else 0.24)
        elements.append(
            SketchStroke.render_line(
                face_cx - chin_w * 0.5, chin_y,
                face_cx + chin_w * 0.5, chin_y,
                seed=f"{seed}_chin_base",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER * 0.9,
                passes=1,
            )
        )

        # Chin indent
        elements.append(
            SketchStroke.render_line(
                face_cx - chin_w * 0.25, mouth_y + 9,
                face_cx + chin_w * 0.25, mouth_y + 9,
                seed=f"{seed}_chin_crease",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CONSTRUCTION,
                opacity=0.6,
            )
        )

        # 10. Ear Construction
        ear_x = cx - (head_w * 0.48) if facing_dir > 0 else cx + (head_w * 0.48)
        ear_top_y = brow_y
        ear_bot_y = nose_base_y
        elements.append(
            SketchPolyline.render(
                [
                    (ear_x, ear_top_y),
                    (ear_x - (facing_dir * 8), ear_top_y + 4),
                    (ear_x - (facing_dir * 8), ear_bot_y - 4),
                    (ear_x, ear_bot_y),
                ],
                seed=f"{seed}_ear",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_INTERIOR,
                passes=1,
            )
        )
        if is_close_up:
            elements.append(
                SketchStroke.render_line(
                    ear_x - (facing_dir * 4), ear_top_y + 5,
                    ear_x - (facing_dir * 3), ear_bot_y - 5,
                    seed=f"{seed}_ear_antihelix",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.6,
                    passes=1,
                )
            )

        # 11. Cheek Shadow & Neck Drop Shadow (Section 5: Anatomical planes for close-ups)
        if is_close_up:
            # Zygomatic arch / cheek plane shadow on shadow side
            sh_side = -facing_dir
            cheek_x = face_cx + (sh_side * head_w * 0.28)
            elements.append(
                InkWashPolygon.render(
                    [
                        (cheek_x - 12, eye_y + 6),
                        (cheek_x + 8, eye_y + 6),
                        (cheek_x + 4, mouth_y + 4),
                        (cheek_x - 8, mouth_y + 4),
                    ],
                    seed=f"{seed}_cheek_sh",
                    fill_color=wash_color,
                    opacity=0.32,
                )
            )
            # Cheek plane crosshatch shading
            elements.append(
                CrossHatch.render(
                    x=cheek_x - 10, y=eye_y + 4,
                    width=20, height=22,
                    seed=f"{seed}_cheek_hatch",
                    spacing=5.0,
                    angle_deg=45.0,
                    double_hatch=False,
                    stroke_color=stroke_color,
                    stroke_width=0.6,
                    opacity=0.40,
                )
            )
            # Neck cast shadow under the jawline
            neck_sh_pts = [
                (face_cx - chin_w * 0.7, chin_y + 2),
                (face_cx + chin_w * 0.7, chin_y + 2),
                (face_cx + chin_w * 0.8, chin_y + 14),
                (face_cx - chin_w * 0.8, chin_y + 14),
            ]
            elements.append(
                InkWashPolygon.render(
                    neck_sh_pts,
                    seed=f"{seed}_neck_drop_sh",
                    fill_color=wash_color,
                    opacity=0.45,
                )
            )

        # 12. Emotional Acting Accents
        if feat.sweat_drop or expression == ExpressionType.AFRAID:
            sd_x = left_eye_cx - 14 if is_left else right_eye_cx + 14
            sd_y = brow_y + 6
            elements.append(
                f'<path d="M {sd_x:.1f} {sd_y:.1f} C {sd_x-2:.1f} {sd_y+6:.1f}, {sd_x+2:.1f} {sd_y+6:.1f}, {sd_x:.1f} {sd_y:.1f}" '
                f'fill="{VALUE_0}" stroke="{stroke_color}" stroke-width="0.8" opacity="0.85"/>'
            )

        return "\n  ".join(elements)
