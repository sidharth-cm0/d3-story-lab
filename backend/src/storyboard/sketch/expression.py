"""Facial expression system for storyboard character acting.

Controls eyebrows, eye shapes, pupil directions, mouth curvature,
and jaw tension for readable visual emotions.
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, Any, Tuple
from pydantic import BaseModel, ConfigDict
from src.storyboard.sketch.stroke import SketchStroke, SketchEllipse, get_rng


class ExpressionType(str, Enum):
    """Supported emotional acting states for storyboard sketch characters."""
    NEUTRAL = "NEUTRAL"
    SUSPICIOUS = "SUSPICIOUS"
    AFRAID = "AFRAID"
    ANGRY = "ANGRY"
    SHOCKED = "SHOCKED"
    SAD = "SAD"
    CONFIDENT = "CONFIDENT"
    CONFUSED = "CONFUSED"
    DETERMINED = "DETERMINED"


class FacialFeatures(BaseModel):
    """Geometric parameters for facial features."""
    model_config = ConfigDict(extra="ignore")

    eyebrow_angle_deg: float = 0.0  # Positive = inner brow down (angry), negative = inner brow up (worried/sad)
    eyebrow_raise: float = 0.0      # Vertical shift
    eye_openness: float = 1.0       # 0.4 squint, 1.0 normal, 1.4 wide shock
    pupil_offset_x: float = 0.0     # Look direction (-1.0 to 1.0)
    pupil_offset_y: float = 0.0
    mouth_curve: float = 0.0        # Negative = frown, 0 = neutral, positive = smirk/smile
    mouth_openness: float = 0.0     # 0 = closed line, 1.0 = open gasp/yell
    mouth_width_factor: float = 1.0
    jaw_tension_lines: bool = False
    sweat_drop: bool = False


EXPRESSION_PROFILES: Dict[ExpressionType, FacialFeatures] = {
    ExpressionType.NEUTRAL: FacialFeatures(
        eyebrow_angle_deg=0.0,
        eye_openness=1.0,
        mouth_curve=0.0,
    ),
    ExpressionType.SUSPICIOUS: FacialFeatures(
        eyebrow_angle_deg=12.0,  # One brow down, one cocked
        eye_openness=0.65,       # Narrowed, guarded squint
        pupil_offset_x=-0.5,     # Side-eye glance
        mouth_curve=-0.1,
        jaw_tension_lines=True,
    ),
    ExpressionType.AFRAID: FacialFeatures(
        eyebrow_angle_deg=-16.0, # Brows arched high with worry
        eyebrow_raise=-2.5,
        eye_openness=1.35,       # Wide dilated eyes
        mouth_curve=-0.4,
        mouth_openness=0.35,
        sweat_drop=True,
    ),
    ExpressionType.ANGRY: FacialFeatures(
        eyebrow_angle_deg=22.0,  # Deep fierce furrow
        eyebrow_raise=1.5,
        eye_openness=0.85,
        mouth_curve=-0.5,
        mouth_openness=0.4,      # Gritted teeth / shout
        jaw_tension_lines=True,
    ),
    ExpressionType.SHOCKED: FacialFeatures(
        eyebrow_angle_deg=-8.0,  # High raised brows
        eyebrow_raise=-4.0,
        eye_openness=1.5,        # Maximum aperture
        mouth_openness=0.8,      # Dropped jaw / gasp
        mouth_width_factor=0.8,
    ),
    ExpressionType.SAD: FacialFeatures(
        eyebrow_angle_deg=-18.0,
        eyebrow_raise=-1.0,
        eye_openness=0.8,
        pupil_offset_y=0.4,      # Looking down
        mouth_curve=-0.6,
        mouth_openness=0.0,
    ),
    ExpressionType.CONFIDENT: FacialFeatures(
        eyebrow_angle_deg=4.0,
        eye_openness=0.95,
        mouth_curve=0.45,        # Slight knowing smirk
        mouth_width_factor=1.1,
    ),
    ExpressionType.CONFUSED: FacialFeatures(
        eyebrow_angle_deg=-10.0, # Asymmetric brows
        eye_openness=0.9,
        pupil_offset_x=0.4,
        mouth_curve=-0.2,
    ),
    ExpressionType.DETERMINED: FacialFeatures(
        eyebrow_angle_deg=16.0,  # Strong focused brow
        eye_openness=0.9,
        pupil_offset_x=0.0,
        mouth_curve=0.0,
        mouth_width_factor=1.15,
        jaw_tension_lines=True,
    ),
}


class ExpressionRenderer:
    """Renders sketch facial features (eyes, brows, nose, mouth) inside a head."""

    @staticmethod
    def render(
        cx: float,
        cy: float,
        head_w: float,
        head_h: float,
        expression: ExpressionType,
        facing_dir: float,  # -1 (left), 0 (front), 1 (right)
        seed: str,
        stroke_color: str = "#e2e8f0",
    ) -> str:
        prof = EXPRESSION_PROFILES.get(expression, EXPRESSION_PROFILES[ExpressionType.NEUTRAL])
        rng = get_rng(seed)
        elements = []

        # Perspective shift according to facing direction
        face_center_x = cx + (facing_dir * head_w * 0.18)

        # 1. Eyebrows
        brow_y = cy - head_h * 0.12 + prof.eyebrow_raise
        brow_span = head_w * 0.22
        brow_rad = math.radians(prof.eyebrow_angle_deg)

        # Left eyebrow
        lb_x1 = face_center_x - brow_span - (head_w * 0.05)
        lb_x2 = face_center_x - (head_w * 0.04)
        lb_y1 = brow_y - (math.sin(brow_rad) * (brow_span / 2) if facing_dir >= 0 else 0)
        lb_y2 = brow_y + (math.sin(brow_rad) * (brow_span / 2))
        elements.append(
            SketchStroke.render_line(
                lb_x1, lb_y1, lb_x2, lb_y2,
                seed=f"{seed}_lbrow",
                stroke_color=stroke_color,
                stroke_width=2.2,
                opacity=0.9,
                passes=2,
                jitter_amount=0.8,
            )
        )

        # Right eyebrow
        rb_x1 = face_center_x + (head_w * 0.04)
        rb_x2 = face_center_x + brow_span + (head_w * 0.05)
        rb_y1 = brow_y + (math.sin(brow_rad) * (brow_span / 2))
        rb_y2 = brow_y - (math.sin(brow_rad) * (brow_span / 2) if facing_dir <= 0 else 0)
        elements.append(
            SketchStroke.render_line(
                rb_x1, rb_y1, rb_x2, rb_y2,
                seed=f"{seed}_rbrow",
                stroke_color=stroke_color,
                stroke_width=2.2,
                opacity=0.9,
                passes=2,
                jitter_amount=0.8,
            )
        )

        # 2. Eyes
        eye_y = cy - head_h * 0.02
        eye_rx = head_w * 0.09 * (1.1 if prof.eye_openness > 1.2 else 1.0)
        eye_ry = head_h * 0.06 * prof.eye_openness

        # Left eye
        le_cx = face_center_x - brow_span * 0.65
        elements.append(
            SketchEllipse.render(
                le_cx, eye_y, eye_rx, eye_ry,
                seed=f"{seed}_leye",
                stroke_color=stroke_color,
                stroke_width=1.5,
                opacity=0.85,
                fill_color="#0f172a",
                fill_opacity=0.5,
                loops=2,
            )
        )
        # Left pupil
        pupil_r = max(1.5, eye_ry * 0.55)
        lp_x = le_cx + prof.pupil_offset_x * eye_rx * 0.5
        lp_y = eye_y + prof.pupil_offset_y * eye_ry * 0.5
        elements.append(
            f'<circle cx="{lp_x:.1f}" cy="{lp_y:.1f}" r="{pupil_r:.1f}" fill="#f8fafc" opacity="0.95"/>'
        )

        # Right eye
        re_cx = face_center_x + brow_span * 0.65
        elements.append(
            SketchEllipse.render(
                re_cx, eye_y, eye_rx, eye_ry,
                seed=f"{seed}_reye",
                stroke_color=stroke_color,
                stroke_width=1.5,
                opacity=0.85,
                fill_color="#0f172a",
                fill_opacity=0.5,
                loops=2,
            )
        )
        # Right pupil
        rp_x = re_cx + prof.pupil_offset_x * eye_rx * 0.5
        rp_y = eye_y + prof.pupil_offset_y * eye_ry * 0.5
        elements.append(
            f'<circle cx="{rp_x:.1f}" cy="{rp_y:.1f}" r="{pupil_r:.1f}" fill="#f8fafc" opacity="0.95"/>'
        )

        # 3. Nose indication (storyboard quick angle)
        nose_top_y = eye_y + eye_ry * 0.6
        nose_bot_y = nose_top_y + head_h * 0.14
        nose_x = face_center_x + (facing_dir * head_w * 0.08)
        elements.append(
            SketchStroke.render_line(
                face_center_x, nose_top_y, nose_x, nose_bot_y,
                seed=f"{seed}_nose1",
                stroke_color=stroke_color,
                stroke_width=1.4,
                opacity=0.8,
                passes=1,
            )
        )
        elements.append(
            SketchStroke.render_line(
                nose_x, nose_bot_y, face_center_x, nose_bot_y + 1.5,
                seed=f"{seed}_nose2",
                stroke_color=stroke_color,
                stroke_width=1.4,
                opacity=0.8,
                passes=1,
            )
        )

        # 4. Mouth
        mouth_y = cy + head_h * 0.22
        mouth_w = head_w * 0.20 * prof.mouth_width_factor
        m_x1 = face_center_x - mouth_w / 2
        m_x2 = face_center_x + mouth_w / 2

        if prof.mouth_openness > 0.2:
            # Open mouth (shout/gasp)
            open_h = head_h * 0.12 * prof.mouth_openness
            elements.append(
                SketchEllipse.render(
                    face_center_x, mouth_y + open_h / 2, mouth_w / 2, open_h / 2,
                    seed=f"{seed}_mouth_open",
                    stroke_color=stroke_color,
                    stroke_width=1.6,
                    opacity=0.9,
                    fill_color="#020617",
                    fill_opacity=0.7,
                )
            )
        else:
            # Closed or smirking line
            curve_dy = -prof.mouth_curve * 5.0
            mid_x = face_center_x
            mid_y = mouth_y + curve_dy
            d = f"M {m_x1:.1f} {mouth_y:.1f} Q {mid_x:.1f} {mid_y:.1f}, {m_x2:.1f} {mouth_y + (0.5 if prof.mouth_curve > 0 else 0):.1f}"
            elements.append(
                f'<path d="{d}" fill="none" stroke="{stroke_color}" stroke-width="1.8" stroke-linecap="round" opacity="0.9"/>'
            )

        # 5. Jaw tension lines
        if prof.jaw_tension_lines:
            elements.append(
                SketchStroke.render_line(
                    m_x1 - 4, mouth_y - 2, m_x1 - 6, mouth_y + 5,
                    seed=f"{seed}_jaw_l",
                    stroke_color="#94a3b8",
                    stroke_width=1.0,
                    opacity=0.6,
                    passes=1,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    m_x2 + 4, mouth_y - 2, m_x2 + 6, mouth_y + 5,
                    seed=f"{seed}_jaw_r",
                    stroke_color="#94a3b8",
                    stroke_width=1.0,
                    opacity=0.6,
                    passes=1,
                )
            )

        # 6. Sweat drop for fear/shock
        if prof.sweat_drop:
            sx = face_center_x + head_w * 0.42
            sy = brow_y - 4
            elements.append(
                f'<path d="M {sx:.1f} {sy:.1f} C {sx-3:.1f} {sy+5:.1f}, {sx+3:.1f} {sy+5:.1f}, {sx:.1f} {sy:.1f}" '
                f'fill="#38bdf8" opacity="0.75"/>'
            )

        return "\n  ".join(elements)


def map_emotion_to_expression(
    emotion_or_mood: str = "",
    action: str = "",
    dialogue: str = "",
) -> ExpressionType:
    """Map narrative emotion or text tone into a supported storyboard expression."""
    text = (emotion_or_mood + " " + action + " " + dialogue).lower()

    if any(w in text for w in ["shock", "disbelief", "gasp", "astonish", "stunned"]):
        return ExpressionType.SHOCKED
    if any(w in text for w in ["fear", "afraid", "panic", "terror", "dread", "terrified", "threat"]):
        return ExpressionType.AFRAID
    if any(w in text for w in ["angry", "rage", "furious", "glare", "yells", "screams", "hostile"]):
        return ExpressionType.ANGRY
    if any(w in text for w in ["suspicious", "distrust", "wary", "skeptical", "narrow", "doubt"]):
        return ExpressionType.SUSPICIOUS
    if any(w in text for w in ["determined", "focused", "resolute", "steely", "grit", "hunting"]):
        return ExpressionType.DETERMINED
    if any(w in text for w in ["confident", "smug", "smirk", "calm", "collected", "in control"]):
        return ExpressionType.CONFIDENT
    if any(w in text for w in ["confused", "puzzled", "baffled", "perplexed"]):
        return ExpressionType.CONFUSED
    if any(w in text for w in ["sad", "grief", "despair", "sorrow", "regret", "depressed"]):
        return ExpressionType.SAD

    return ExpressionType.NEUTRAL
