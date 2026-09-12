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
    brow_asymmetry: float = 0.0     # One brow raised higher than the other (suspicious / confused)
    eye_openness: float = 1.0       # 0.4 squint, 1.0 normal, 1.5 wide shock
    pupil_offset_x: float = 0.0     # Look direction (-1.0 to 1.0)
    pupil_offset_y: float = 0.0
    mouth_curve: float = 0.0        # Negative = frown, 0 = neutral, positive = smirk/smile
    mouth_openness: float = 0.0     # 0 = closed line, 1.0 = open gasp/yell
    mouth_width_factor: float = 1.0
    jaw_tension_lines: bool = False
    sweat_drop: bool = False
    head_tilt_deg: float = 0.0      # Expressive head tilt


EXPRESSION_PROFILES: Dict[ExpressionType, FacialFeatures] = {
    ExpressionType.NEUTRAL: FacialFeatures(
        eyebrow_angle_deg=0.0,
        eye_openness=1.0,
        mouth_curve=0.0,
    ),
    ExpressionType.SUSPICIOUS: FacialFeatures(
        eyebrow_angle_deg=14.0,  # One brow down, other cocked high
        eyebrow_raise=1.0,
        brow_asymmetry=9.0,      # Suspicious arched brow
        eye_openness=0.60,       # Narrowed, guarded squint
        pupil_offset_x=-0.55,    # Sharp side glance
        mouth_curve=-0.2,        # Compressed firm mouth
        mouth_width_factor=0.92,
        jaw_tension_lines=True,
        head_tilt_deg=3.5,       # Suspicious slight tilt
    ),
    ExpressionType.AFRAID: FacialFeatures(
        eyebrow_angle_deg=-18.0, # High worried brow arch
        eyebrow_raise=-3.5,
        brow_asymmetry=0.0,
        eye_openness=1.42,       # Wide dilated eyes
        pupil_offset_y=-0.2,
        mouth_curve=-0.45,
        mouth_openness=0.40,     # Trembling parted mouth
        sweat_drop=True,
        head_tilt_deg=-3.0,      # Head pulled back defensively
    ),
    ExpressionType.ANGRY: FacialFeatures(
        eyebrow_angle_deg=24.0,  # Deep fierce furrow
        eyebrow_raise=2.2,
        brow_asymmetry=0.0,
        eye_openness=0.80,       # Glaring tense eyelids
        mouth_curve=-0.55,
        mouth_openness=0.45,     # Gritted teeth / aggressive yell
        mouth_width_factor=1.10,
        jaw_tension_lines=True,
        head_tilt_deg=2.0,       # Head jutting forward
    ),
    ExpressionType.SHOCKED: FacialFeatures(
        eyebrow_angle_deg=-10.0, # High raised brows
        eyebrow_raise=-5.2,
        eye_openness=1.55,       # Maximum shock aperture
        mouth_openness=0.85,     # Dropped open jaw
        mouth_width_factor=0.85,
        head_tilt_deg=-2.5,      # Recoiling head
    ),
    ExpressionType.SAD: FacialFeatures(
        eyebrow_angle_deg=-20.0,
        eyebrow_raise=-1.5,
        eye_openness=0.75,
        pupil_offset_y=0.45,     # Cast downward
        mouth_curve=-0.65,
        mouth_openness=0.0,
    ),
    ExpressionType.CONFIDENT: FacialFeatures(
        eyebrow_angle_deg=5.0,
        eye_openness=0.95,
        mouth_curve=0.48,        # Knowing smirk
        mouth_width_factor=1.12,
        head_tilt_deg=1.5,
    ),
    ExpressionType.CONFUSED: FacialFeatures(
        eyebrow_angle_deg=-10.0,
        brow_asymmetry=12.0,     # Strong asymmetric brow
        eye_openness=0.88,
        pupil_offset_x=0.45,
        mouth_curve=-0.25,
        head_tilt_deg=-4.5,      # Puzzled head cock
    ),
    ExpressionType.DETERMINED: FacialFeatures(
        eyebrow_angle_deg=18.0,  # Lowered focused brow
        eyebrow_raise=1.2,
        eye_openness=0.88,       # Sharp piercing gaze
        pupil_offset_x=0.0,
        mouth_curve=0.0,         # Set firm jaw
        mouth_width_factor=1.18,
        jaw_tension_lines=True,
        head_tilt_deg=1.0,       # Chin forward
    ),
}


class ExpressionRenderer:
    """Renders sketch facial features (eyes, brows, nose, mouth) with anatomical planes."""

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
        is_close_up: bool = False,
    ) -> str:
        from src.storyboard.sketch.face import FaceSketchRenderer, FaceOrientation
        if facing_dir < -0.3:
            orient = FaceOrientation.THREE_QUARTER_LEFT
        elif facing_dir > 0.3:
            orient = FaceOrientation.THREE_QUARTER_RIGHT
        else:
            orient = FaceOrientation.FRONT
        return FaceSketchRenderer.render_face(
            cx=cx,
            cy=cy,
            head_w=head_w,
            head_h=head_h,
            expression=expression,
            orientation=orient,
            intensity=0.85,
            is_close_up=is_close_up,
            seed=seed,
            stroke_color=stroke_color,
        )


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
