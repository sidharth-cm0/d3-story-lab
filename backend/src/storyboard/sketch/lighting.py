"""Hand-drawn shading, lighting setups, and storyboard artistic styles.

Implements PENCIL, INK, NOIR, and TECHNICAL styles with chiaroscuro hatching,
volumetric light cones, shadow pools, and negative space blocks.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict

from src.storyboard.sketch.stroke import (
    SketchStroke,
    CrossHatch,
    ScribbleShadow,
    get_rng,
)


class SketchStyle(str, Enum):
    """Storyboard rendering artistic styles."""
    PENCIL = "PENCIL"
    INK = "INK"
    NOIR = "NOIR"
    PENCIL_NOIR = "PENCIL_NOIR"
    TECHNICAL = "TECHNICAL"


class StylePalette(BaseModel):
    """Color and line settings for an artistic style."""
    model_config = ConfigDict(extra="ignore")

    stroke_color: str = "#e2e8f0"
    shadow_color: str = "#020617"
    hatch_color: str = "#64748b"
    accent_color: str = "#f59e0b"
    bg_gradient_start: str = "#0a0e17"
    bg_gradient_end: str = "#04060a"
    stroke_width_multiplier: float = 1.0
    hatch_density_spacing: float = 9.0
    double_crosshatch: bool = True
    draw_construction_lines: bool = False


STYLE_PALETTES: Dict[SketchStyle, StylePalette] = {
    SketchStyle.PENCIL: StylePalette(
        stroke_color="#cbd5e1",
        shadow_color="#090d16",
        hatch_color="#64748b",
        accent_color="#94a3b8",
        bg_gradient_start="#111827",
        bg_gradient_end="#090d16",
        stroke_width_multiplier=0.85,
        hatch_density_spacing=18.0,
        double_crosshatch=False,
        draw_construction_lines=True,
    ),
    SketchStyle.INK: StylePalette(
        stroke_color="#f8fafc",
        shadow_color="#020617",
        hatch_color="#475569",
        accent_color="#fbbf24",
        bg_gradient_start="#070a10",
        bg_gradient_end="#020305",
        stroke_width_multiplier=1.2,
        hatch_density_spacing=15.0,
        double_crosshatch=True,
    ),
    SketchStyle.NOIR: StylePalette(
        stroke_color="#ffffff",
        shadow_color="#000000",
        hatch_color="#334155",
        accent_color="#e11d48",
        bg_gradient_start="#05070a",
        bg_gradient_end="#010203",
        stroke_width_multiplier=1.35,
        hatch_density_spacing=14.0,
        double_crosshatch=True,
    ),
    SketchStyle.PENCIL_NOIR: StylePalette(
        stroke_color="#e2e8f0",
        shadow_color="#020617",
        hatch_color="#475569",
        accent_color="#f59e0b",
        bg_gradient_start="#0a0f1d",
        bg_gradient_end="#03060c",
        stroke_width_multiplier=1.0,
        hatch_density_spacing=16.0,
        double_crosshatch=True,
        draw_construction_lines=True,
    ),
    SketchStyle.TECHNICAL: StylePalette(
        stroke_color="#93c5fd",
        shadow_color="#081022",
        hatch_color="#1e3a8a",
        accent_color="#38bdf8",
        bg_gradient_start="#091428",
        bg_gradient_end="#030814",
        stroke_width_multiplier=0.9,
        hatch_density_spacing=20.0,
        double_crosshatch=False,
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
        style: SketchStyle = SketchStyle.PENCIL_NOIR,
    ) -> str:
        palette = STYLE_PALETTES.get(style, STYLE_PALETTES[SketchStyle.PENCIL_NOIR])
        elements = []
        desc = lighting_description.lower()

        # 1. Volumetric Overhead / Spotlight Cone
        if any(w in desc for w in ["overhead", "spotlight", "lamp", "cone", "key"]):
            cone_top_x = 480.0
            cone_top_y = 0.0
            cone_bot_w = 420.0
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

        # 2. Chiaroscuro Side Shadow Crosshatching
        # Left corner shadow
        elements.append(
            CrossHatch.render(
                x=0, y=height * 0.45,
                width=240, height=height * 0.55,
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
                x=width - 240, y=height * 0.45,
                width=240, height=height * 0.55,
                seed=f"{seed}_r_hatch",
                spacing=palette.hatch_density_spacing,
                angle_deg=-45.0,
                double_hatch=palette.double_crosshatch,
                stroke_color=palette.hatch_color,
                opacity=0.45,
            )
        )

        # 3. Optional construction framing marks if pencil style
        if palette.draw_construction_lines:
            # Rule-of-thirds pencil tick lines
            for t_x in [320.0, 640.0]:
                elements.append(
                    SketchStroke.render_line(
                        t_x, 10, t_x, 30,
                        seed=f"{seed}_tick_x_{t_x}",
                        stroke_color="#64748b",
                        stroke_width=0.8,
                        opacity=0.5,
                        passes=1,
                    )
                )
            for t_y in [180.0, 360.0]:
                elements.append(
                    SketchStroke.render_line(
                        10, t_y, 30, t_y,
                        seed=f"{seed}_tick_y_{t_y}",
                        stroke_color="#64748b",
                        stroke_width=0.8,
                        opacity=0.5,
                        passes=1,
                    )
                )

        return "\n  ".join(elements)
