"""Hand-drawn shading, lighting setups, and storyboard artistic styles.

Implements five cinematic styles:
- CINEMATIC_INK_WASH (default)
- GRAPHITE_REALISM
- NOIR_BRUSH
- COLOR_STORYBOARD
- TECHNICAL_BOARD
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict

from src.storyboard.sketch.stroke import (
    SketchStroke,
    CrossHatch,
    ScribbleShadow,
    InkWashPolygon,
    get_rng,
    VALUE_0,
    VALUE_1,
    VALUE_2,
    VALUE_3,
    VALUE_4,
    ACCENT_COOL_WASH,
    ACCENT_BLUE_HAZE,
    ACCENT_WARM_LAMP,
    ACCENT_STORY_RED,
    ACCENT_SEPIA,
)


class SketchStyle(str, Enum):
    """Storyboard rendering artistic styles."""
    GRAPHITE_PRODUCTION_BOARD = "GRAPHITE_PRODUCTION_BOARD"
    CINEMATIC_INK_WASH = "CINEMATIC_INK_WASH"
    GRAPHITE_REALISM = "GRAPHITE_REALISM"
    NOIR_BRUSH = "NOIR_BRUSH"
    COLOR_STORYBOARD = "COLOR_STORYBOARD"
    TECHNICAL_BOARD = "TECHNICAL_BOARD"

    # Compatibility & prompt aliases
    PENCIL_NOIR = "NOIR_BRUSH"
    INK_WASH = "CINEMATIC_INK_WASH"
    TECHNICAL = "TECHNICAL_BOARD"
    PENCIL = "GRAPHITE_PRODUCTION_BOARD"
    INK = "CINEMATIC_INK_WASH"
    NOIR = "NOIR_BRUSH"


class StylePalette(BaseModel):
    """Color and line settings for an artistic style."""
    model_config = ConfigDict(extra="ignore")

    name: str = "Graphite Production Board"
    stroke_color: str = "#202020"
    shadow_color: str = "#3A3833"
    hatch_color: str = "#5A5750"
    accent_color: str = "#A83232"
    bg_gradient_start: str = "#EDE8DF"
    bg_gradient_end: str = "#DFD9CD"
    stroke_width_multiplier: float = 1.0
    hatch_density_spacing: float = 10.0
    double_crosshatch: bool = True
    draw_construction_lines: bool = False
    draw_aspect_ratio_guides: bool = False
    mood_color_wash: Optional[str] = None


STYLE_PALETTES: Dict[SketchStyle, StylePalette] = {
    SketchStyle.GRAPHITE_PRODUCTION_BOARD: StylePalette(
        name="Graphite Production Board",
        stroke_color="#202020",
        shadow_color="#3A3833",
        hatch_color="#5A5750",
        accent_color="#A83232",
        bg_gradient_start="#EDE8DF",
        bg_gradient_end="#DFD9CD",
        stroke_width_multiplier=1.0,
        hatch_density_spacing=10.0,
        double_crosshatch=True,
        draw_construction_lines=False,
    ),
    SketchStyle.CINEMATIC_INK_WASH: StylePalette(
        name="Cinematic Ink & Wash",
        stroke_color="#f8fafc",
        shadow_color="#020617",
        hatch_color="#475569",
        accent_color="#38bdf8",
        bg_gradient_start="#0c121e",
        bg_gradient_end="#03060a",
        stroke_width_multiplier=1.1,
        hatch_density_spacing=13.0,
        double_crosshatch=True,
        draw_construction_lines=False,
    ),
    SketchStyle.GRAPHITE_REALISM: StylePalette(
        name="Graphite Realism",
        stroke_color="#262626",
        shadow_color="#3a3833",
        hatch_color="#6b665d",
        accent_color="#a83232",
        bg_gradient_start="#eae5db",
        bg_gradient_end="#dcd5c9",
        stroke_width_multiplier=0.9,
        hatch_density_spacing=10.0,
        double_crosshatch=True,
        draw_construction_lines=False,
    ),
    SketchStyle.NOIR_BRUSH: StylePalette(
        name="Noir Brush",
        stroke_color="#ffffff",
        shadow_color="#000000",
        hatch_color="#334155",
        accent_color="#ef4444",
        bg_gradient_start="#05070a",
        bg_gradient_end="#010203",
        stroke_width_multiplier=1.35,
        hatch_density_spacing=10.0,
        double_crosshatch=True,
    ),
    SketchStyle.COLOR_STORYBOARD: StylePalette(
        name="Color Storyboard",
        stroke_color="#1e293b",
        shadow_color="#0f172a",
        hatch_color="#334155",
        accent_color="#d97706",
        bg_gradient_start="#f1ede4",
        bg_gradient_end="#e2dbcf",
        stroke_width_multiplier=1.05,
        hatch_density_spacing=12.0,
        double_crosshatch=True,
        mood_color_wash="rgba(180, 83, 9, 0.06)",
    ),
    SketchStyle.TECHNICAL_BOARD: StylePalette(
        name="Technical Production Board",
        stroke_color="#93c5fd",
        shadow_color="#081022",
        hatch_color="#1e3a8a",
        accent_color="#38bdf8",
        bg_gradient_start="#091428",
        bg_gradient_end="#030814",
        stroke_width_multiplier=0.9,
        hatch_density_spacing=18.0,
        double_crosshatch=False,
        draw_aspect_ratio_guides=True,
    ),
}


class LightingSketchRenderer:
    """Renders chiaroscuro lighting, volumetric beams, and shadow pools."""

    @staticmethod
    def render_lighting(
        width: float = 960.0,
        height: float = 540.0,
        lighting_description: str = "",
        seed: str = "light",
        style: SketchStyle = SketchStyle.CINEMATIC_INK_WASH,
    ) -> str:
        palette = STYLE_PALETTES.get(style, STYLE_PALETTES[SketchStyle.CINEMATIC_INK_WASH])
        elements = []
        desc = lighting_description.lower()

        # 1. Volumetric Overhead / Spotlight Cone
        if any(w in desc for w in ["overhead", "spotlight", "lamp", "cone", "key", "torch", "flashlight"]):
            cone_top_x = 480.0
            cone_top_y = 0.0
            cone_bot_w = 440.0
            cone_bot_y = height
            elements.append(
                f'<polygon points="{cone_top_x - 30:.1f},{cone_top_y:.1f} '
                f'{cone_top_x + 30:.1f},{cone_top_y:.1f} '
                f'{cone_top_x + cone_bot_w / 2:.1f},{cone_bot_y:.1f} '
                f'{cone_top_x - cone_bot_w / 2:.1f},{cone_bot_y:.1f}" '
                f'fill="{palette.accent_color}" fill-opacity="0.08"/>'
            )
            # Rim lines along light boundary
            elements.append(
                SketchStroke.render_line(
                    cone_top_x - 30, cone_top_y,
                    cone_top_x - cone_bot_w / 2, cone_bot_y,
                    seed=f"{seed}_cone_l",
                    stroke_color=palette.accent_color,
                    stroke_width=1.0,
                    opacity=0.35,
                    passes=1,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cone_top_x + 30, cone_top_y,
                    cone_top_x + cone_bot_w / 2, cone_bot_y,
                    seed=f"{seed}_cone_r",
                    stroke_color=palette.accent_color,
                    stroke_width=1.0,
                    opacity=0.35,
                    passes=1,
                )
            )

        # 2. Tonal Value Masses (Section 12 & 13)
        if style in (SketchStyle.GRAPHITE_PRODUCTION_BOARD, SketchStyle.GRAPHITE_REALISM):
            # Graphite Production Board: Warm paper, midtone charcoal washes, deep shadow pools
            # Top corner ambient falloff (light charcoal midtone)
            elements.append(
                InkWashPolygon.render(
                    points=[(0, 0), (280, 0), (0, 300)],
                    seed=f"{seed}_graphite_topl",
                    wash_color="#77736A",
                    opacity=0.18,
                )
            )
            elements.append(
                InkWashPolygon.render(
                    points=[(width, 0), (width - 280, 0), (width, 300)],
                    seed=f"{seed}_graphite_topr",
                    wash_color="#77736A",
                    opacity=0.18,
                )
            )
            # Ground/floor shadow mass (deep charcoal)
            elements.append(
                InkWashPolygon.render(
                    points=[(0, height * 0.72), (width, height * 0.72), (width, height), (0, height)],
                    seed=f"{seed}_graphite_floor",
                    wash_color="#3A3833",
                    opacity=0.30,
                )
            )
        elif style == SketchStyle.CINEMATIC_INK_WASH:
            # 3 levels of grayscale ink wash (30%, 55%, 80%)
            # Deep vignette corner wash
            elements.append(
                InkWashPolygon.render(
                    points=[(0, 0), (280, 0), (0, 320)],
                    seed=f"{seed}_wash_topl",
                    wash_color=VALUE_3,
                    opacity=0.6,
                )
            )
            elements.append(
                InkWashPolygon.render(
                    points=[(width, 0), (width - 280, 0), (width, 320)],
                    seed=f"{seed}_wash_topr",
                    wash_color=VALUE_3,
                    opacity=0.6,
                )
            )
            # Floor shadow pool wash
            elements.append(
                InkWashPolygon.render(
                    points=[(0, height * 0.72), (width, height * 0.72), (width, height), (0, height)],
                    seed=f"{seed}_wash_floor",
                    wash_color=VALUE_4,
                    opacity=0.45,
                )
            )
            # Subtle cool blue accent wash
            elements.append(
                f'<rect width="{width:.1f}" height="{height:.1f}" fill="{ACCENT_COOL_WASH}" pointer-events="none"/>'
            )

        # 3. Chiaroscuro Side Shadow Crosshatching
        # Left corner shadow
        elements.append(
            CrossHatch.render(
                x=0, y=height * 0.42,
                width=260, height=height * 0.58,
                seed=f"{seed}_l_hatch",
                spacing=palette.hatch_density_spacing,
                angle_deg=45.0,
                double_hatch=palette.double_crosshatch,
                stroke_color=palette.hatch_color,
                opacity=0.45,
            )
        )
        # Right corner shadow
        elements.append(
            CrossHatch.render(
                x=width - 260, y=height * 0.42,
                width=260, height=height * 0.58,
                seed=f"{seed}_r_hatch",
                spacing=palette.hatch_density_spacing,
                angle_deg=-45.0,
                double_hatch=palette.double_crosshatch,
                stroke_color=palette.hatch_color,
                opacity=0.45,
            )
        )

        # 4. Noir Stark Contrast Blocks
        if style == SketchStyle.NOIR_BRUSH:
            # Stark deep black shadow polygons
            elements.append(
                f'<polygon points="0,{height*0.5:.1f} 200,{height:.1f} 0,{height:.1f}" fill="#000000" opacity="0.85"/>'
            )
            elements.append(
                f'<polygon points="{width},{height*0.5:.1f} {width-200},{height:.1f} {width},{height:.1f}" fill="#000000" opacity="0.85"/>'
            )

        # 5. Optional construction framing marks if graphite realism
        if palette.draw_construction_lines:
            # Rule-of-thirds pencil tick lines
            for t_x in [320.0, 640.0]:
                elements.append(
                    SketchStroke.render_line(
                        t_x, 8, t_x, 28,
                        seed=f"{seed}_tick_x_{t_x}",
                        stroke_color="#64748b",
                        stroke_width=0.8,
                        opacity=0.55,
                        passes=1,
                    )
                )
            for t_y in [180.0, 360.0]:
                elements.append(
                    SketchStroke.render_line(
                        8, t_y, 28, t_y,
                        seed=f"{seed}_tick_y_{t_y}",
                        stroke_color="#64748b",
                        stroke_width=0.8,
                        opacity=0.55,
                        passes=1,
                    )
                )

        # 6. Technical Production Board Aspect Ratio Guides
        if palette.draw_aspect_ratio_guides:
            # 2.39:1 Anamorphic crop lines (top & bottom mattes)
            # For 960 width, 2.39 height = 960 / 2.39 = ~401.6px -> matte top/bottom = (540 - 402) / 2 = 69px
            matte_h = 69.0
            elements.append(
                f'<line x1="0" y1="{matte_h:.1f}" x2="{width:.1f}" y2="{matte_h:.1f}" '
                f'stroke="{palette.accent_color}" stroke-width="1.0" stroke-dasharray="8,4" opacity="0.5"/>'
            )
            elements.append(
                f'<line x1="0" y1="{height - matte_h:.1f}" x2="{width:.1f}" y2="{height - matte_h:.1f}" '
                f'stroke="{palette.accent_color}" stroke-width="1.0" stroke-dasharray="8,4" opacity="0.5"/>'
            )
            elements.append(
                f'<text x="{width - 70:.1f}" y="{matte_h - 6:.1f}" fill="{palette.accent_color}" '
                f'font-family="monospace" font-size="9" opacity="0.7">2.39:1 CROP</text>'
            )

            # Center optical crosshair
            elements.append(
                f'<line x1="{width/2 - 12:.1f}" y1="{height/2:.1f}" x2="{width/2 + 12:.1f}" y2="{height/2:.1f}" '
                f'stroke="{palette.accent_color}" stroke-width="0.8" opacity="0.4"/>'
            )
            elements.append(
                f'<line x1="{width/2:.1f}" y1="{height/2 - 12:.1f}" x2="{width/2:.1f}" y2="{height/2 + 12:.1f}" '
                f'stroke="{palette.accent_color}" stroke-width="0.8" opacity="0.4"/>'
            )

        # 7. Color Storyboard Wash
        if palette.mood_color_wash:
            elements.append(
                f'<rect width="{width:.1f}" height="{height:.1f}" fill="{palette.mood_color_wash}" pointer-events="none"/>'
            )

        return "\n  ".join(elements)
