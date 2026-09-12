"""Architectural environment sketch renderer with physical mass and depth layering.

Implements architectural solids over perspective guide lines:
- Columns with actual 3D width, flanges, rivets, and side drop shadows
- Wall planes, masonry courses, and plaster cracks
- Roof rafters, cross-braces, and industrial trusses
- Windows with paned mullions, broken glass shards, and masonry sills
- Stacked wooden cargo crates, industrial shelving, and floor puddle washes
- 3 depth planes: FOREGROUND (silhouette framing), MIDGROUND (action plane), BACKGROUND (receding architecture)
"""

from __future__ import annotations
import math
import random
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.visual_bible import LocationVisualReference
from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchEllipse,
    SketchPolyline,
    SketchPolygon,
    InkWashPolygon,
    CrossHatch,
    ScribbleShadow,
    TextureRenderer,
    get_rng,
    get_seed_hash,
    LINE_WEIGHT_CONSTRUCTION,
    LINE_WEIGHT_BACKGROUND,
    LINE_WEIGHT_INTERIOR,
    LINE_WEIGHT_CHARACTER,
    LINE_WEIGHT_FOREGROUND,
    LINE_WEIGHT_SHADOW,
    VALUE_0,
    VALUE_1,
    VALUE_2,
    VALUE_3,
    VALUE_4,
    ACCENT_COOL_WASH,
    ACCENT_BLUE_HAZE,
    ACCENT_WARM_LAMP,
)


class EnvironmentType(str, Enum):
    """Supported distinct architectural environments."""
    WAREHOUSE = "WAREHOUSE"
    OFFICE = "OFFICE"
    CORRIDOR = "CORRIDOR"
    VAULT = "VAULT"
    ROOFTOP = "ROOFTOP"
    STREET = "STREET"
    APARTMENT = "APARTMENT"
    INTERROGATION_ROOM = "INTERROGATION_ROOM"
    STAIRCASE = "STAIRCASE"
    INDUSTRIAL_ROOM = "INDUSTRIAL_ROOM"
    FOREST = "FOREST"
    VEHICLE_INTERIOR = "VEHICLE_INTERIOR"


class LocationSketchIdentity(BaseModel):
    """Deterministic visual architectural identity for a location."""
    model_config = ConfigDict(extra="ignore")

    location_id: str
    name: str
    env_type: EnvironmentType = EnvironmentType.WAREHOUSE
    vanishing_point: Tuple[float, float] = (480.0, 260.0)
    pillar_spacing: float = 140.0
    window_count: int = 4
    door_position_x: float = 240.0
    accent_fixture: str = "hanging_lamp"
    floor_level_y: float = 430.0

    @classmethod
    def from_reference(cls, ref: LocationVisualReference) -> LocationSketchIdentity:
        desc = (ref.name + " " + ref.environment_type + " " + ref.architecture).lower()
        seed_int = get_seed_hash(f"env_{ref.location_id}_{ref.name}")
        rng = random.Random(seed_int)

        if "warehouse" in desc or "abandoned" in desc or "depot" in desc:
            env_t = EnvironmentType.WAREHOUSE
            vp = (480.0, 250.0)
        elif "corridor" in desc or "hall" in desc:
            env_t = EnvironmentType.CORRIDOR
            vp = (480.0, 260.0)
        elif "office" in desc or "penthouse" in desc or "executive" in desc:
            env_t = EnvironmentType.OFFICE
            vp = (520.0, 270.0)
        elif "vault" in desc or "safe" in desc:
            env_t = EnvironmentType.VAULT
            vp = (480.0, 270.0)
        elif "rooftop" in desc or "roof" in desc:
            env_t = EnvironmentType.ROOFTOP
            vp = (480.0, 310.0)
        elif "street" in desc or "alley" in desc or "exterior" in desc:
            env_t = EnvironmentType.STREET
            vp = (420.0, 280.0)
        elif "interrogation" in desc:
            env_t = EnvironmentType.INTERROGATION_ROOM
            vp = (480.0, 250.0)
        else:
            env_t = EnvironmentType.WAREHOUSE
            vp = (480.0, 260.0)

        return cls(
            location_id=ref.location_id,
            name=ref.name,
            env_type=env_t,
            vanishing_point=vp,
            pillar_spacing=140.0 + (rng.random() * 20.0),
            window_count=4,
            door_position_x=220.0,
            floor_level_y=420.0,
        )


class EnvironmentSketchRenderer:
    """Renders architectural environment masses, structural columns, and 3-depth separation."""

    def __init__(self):
        self._identities: Dict[str, LocationSketchIdentity] = {}

    def get_or_create_identity(
        self,
        location_id: str,
        name: str = "",
        ref: Optional[LocationVisualReference] = None,
    ) -> LocationSketchIdentity:
        if location_id in self._identities:
            return self._identities[location_id]

        if ref:
            ident = LocationSketchIdentity.from_reference(ref)
        else:
            dummy_ref = LocationVisualReference(
                location_id=location_id,
                name=name or location_id,
            )
            ident = LocationSketchIdentity.from_reference(dummy_ref)

        self._identities[location_id] = ident
        return ident

    def render_environment(
        self,
        identity: LocationSketchIdentity,
        width: float = 960.0,
        height: float = 540.0,
        seed: str = "env",
        stroke_color: str = "#64748b",
        include_foreground: bool = True,
    ) -> str:
        """Render complete architectural environment with depth layering and solid mass."""
        env_t = identity.env_type
        vp_x, vp_y = identity.vanishing_point
        floor_y = identity.floor_level_y
        elements: List[str] = []

        # =========================================================================
        # 1. BACKGROUND LAYER (WALL PLANES, ROOF RAFTERS, MULLION WINDOWS)
        # =========================================================================
        # Distant back wall fill & tone
        elements.append(
            f'<rect x="0" y="0" width="{width:.1f}" height="{floor_y:.1f}" '
            f'fill="#050811" fill-opacity="0.94"/>'
        )

        # Distant horizontal mortar seams / wall courses
        for seam_idx in range(1, 9):
            sy = seam_idx * (floor_y / 9.0)
            elements.append(
                SketchStroke.render_line(
                    0, sy, width, sy,
                    seed=f"{seed}_wall_seam_{seam_idx}",
                    stroke_color="#1e293b",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.40,
                    passes=1,
                )
            )

        # Concrete floor plane with cool wash
        floor_poly = [(0, floor_y), (width, floor_y), (width, height), (0, height)]
        elements.append(
            InkWashPolygon.render(
                floor_poly,
                seed=f"{seed}_floor_wash",
                fill_color="#090d16",
                opacity=0.95,
            )
        )

        # Subtle expansion lines on floor (opacity < 0.10, NOT raw wireframes!)
        for rad_x in [80.0, 240.0, 480.0, 720.0, 880.0]:
            elements.append(
                SketchStroke.render_line(
                    vp_x, vp_y + 80, rad_x, height,
                    seed=f"{seed}_exp_line_{rad_x}",
                    stroke_color="#334155",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    opacity=0.08,
                    passes=1,
                )
            )

        if env_t == EnvironmentType.WAREHOUSE or env_t == EnvironmentType.INDUSTRIAL_ROOM:
            # Roof rafters / triangular truss girder across ceiling
            elements.append('<g id="roof_truss_beam">')
            truss_y = 55.0
            elements.append(
                SketchStroke.render_line(
                    0, truss_y, width, truss_y,
                    seed=f"{seed}_truss_main",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_BACKGROUND * 1.4,
                    passes=2,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    0, truss_y + 16, width, truss_y + 16,
                    seed=f"{seed}_truss_sub",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_BACKGROUND,
                    passes=1,
                )
            )
            # Diagonal cross-bracing in roof trusses
            for t_idx in range(0, int(width), 45):
                elements.append(
                    SketchStroke.render_line(
                        t_idx, truss_y, t_idx + 45, truss_y + 16,
                        seed=f"{seed}_truss_diag_{t_idx}",
                        stroke_color="#334155",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        passes=1,
                    )
                )
            elements.append('</g>')

            # High industrial multi-pane windows with broken glass shards & moonlight
            for w_idx in range(identity.window_count):
                elements.append(f'<g id="industrial_win_{w_idx}">')
                wx = 300.0 + (w_idx * 95.0)
                wy = 65.0
                ww = 72.0
                wh = 105.0

                # Window frame & arched lintel
                win_pts = [(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)]
                elements.append(
                    SketchPolygon.render(
                        win_pts,
                        seed=f"{seed}_win_frame_{w_idx}",
                        stroke_color="#475569",
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        fill_color="#0f172a",
                        fill_opacity=0.88,
                    )
                )
                # Cool moonlight window wash
                elements.append(
                    InkWashPolygon.render(
                        win_pts,
                        seed=f"{seed}_win_moon_{w_idx}",
                        fill_color=ACCENT_BLUE_HAZE,
                        opacity=0.18,
                    )
                )
                # Mullion grid
                elements.append(
                    SketchStroke.render_line(
                        wx + ww * 0.5, wy, wx + ww * 0.5, wy + wh,
                        seed=f"{seed}_wmul1_{w_idx}",
                        stroke_color="#334155",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    )
                )
                elements.append(
                    SketchStroke.render_line(
                        wx, wy + wh * 0.5, wx + ww, wy + wh * 0.5,
                        seed=f"{seed}_wmul2_{w_idx}",
                        stroke_color="#334155",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    )
                )
                # Broken pane jagged shard
                if w_idx == 1 or w_idx == 2:
                    elements.append(
                        SketchStroke.render_line(
                            wx + 4, wy + wh - 4, wx + ww * 0.45, wy + wh * 0.35,
                            seed=f"{seed}_shard1_{w_idx}",
                            stroke_color="#94a3b8",
                            stroke_width=0.8,
                        )
                    )
                    elements.append(
                        SketchStroke.render_line(
                            wx + ww * 0.45, wy + wh * 0.35, wx + ww - 6, wy + wh - 10,
                            seed=f"{seed}_shard2_{w_idx}",
                            stroke_color="#94a3b8",
                            stroke_width=0.8,
                        )
                    )
                elements.append('</g>')

            # Hanging Industrial Lamps with cables and warm glow pools
            for lamp_x in [380.0, 620.0]:
                elements.append(
                    SketchStroke.render_line(
                        lamp_x, 0, lamp_x, 130.0,
                        seed=f"{seed}_cord_{lamp_x}",
                        stroke_color="#475569",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION * 1.5,
                    )
                )
                # Bell shade
                shade_pts = [
                    (lamp_x - 18, 142), (lamp_x + 18, 142),
                    (lamp_x + 12, 130), (lamp_x - 12, 130)
                ]
                elements.append(
                    SketchPolygon.render(
                        shade_pts,
                        seed=f"{seed}_shade_{lamp_x}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        fill_color="#1e293b",
                        fill_opacity=0.9,
                    )
                )
                # Volumetric warm light pool on floor
                pool_pts = [
                    (lamp_x - 12, 143), (lamp_x + 12, 143),
                    (lamp_x + 90, floor_y + 35), (lamp_x - 90, floor_y + 35)
                ]
                elements.append(
                    InkWashPolygon.render(
                        pool_pts,
                        seed=f"{seed}_light_cone_{lamp_x}",
                        fill_color=ACCENT_WARM_LAMP,
                        opacity=0.08,
                    )
                )

            # Conduit Pipes & Sagging Cable Runs across back wall (Section 11)
            elements.append('<g id="industrial_conduits">')
            pipe_y = 175.0
            elements.append(
                SketchStroke.render_line(
                    0, pipe_y, width, pipe_y,
                    seed=f"{seed}_conduit_pipe_1",
                    stroke_color="#334155",
                    stroke_width=LINE_WEIGHT_BACKGROUND * 1.2,
                    passes=1,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    0, pipe_y + 8, width, pipe_y + 8,
                    seed=f"{seed}_conduit_pipe_2",
                    stroke_color="#1e293b",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    passes=1,
                )
            )
            # Pipe mounting bracket collars
            for b_x in [160.0, 340.0, 520.0, 700.0, 860.0]:
                elements.append(
                    SketchPolygon.render(
                        [(b_x - 3, pipe_y - 3), (b_x + 3, pipe_y - 3), (b_x + 3, pipe_y + 11), (b_x - 3, pipe_y + 11)],
                        seed=f"{seed}_bracket_{b_x}",
                        stroke_color="#475569",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        fill_color="#1e293b",
                    )
                )
            # Sagging heavy electrical cable loop
            d_cable = f"M 0 195 Q 240 225, 480 200 Q 720 228, {width:.1f} 198"
            elements.append(
                f'<path d="{d_cable}" fill="none" stroke="#1e293b" stroke-width="1.4" opacity="0.6"/>'
            )
            elements.append('</g>')

            # Industrial Steel Shelving Unit along right wall (Section 11)
            elements.append('<g id="industrial_shelving">')
            sh_x = 760.0
            sh_w = 110.0
            sh_top_y = floor_y - 140.0
            sh_bot_y = floor_y
            # Outer shelf frame uprights
            elements.append(
                SketchStroke.render_line(
                    sh_x, sh_top_y, sh_x, sh_bot_y,
                    seed=f"{seed}_shelf_up_l",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    sh_x + sh_w, sh_top_y, sh_x + sh_w, sh_bot_y,
                    seed=f"{seed}_shelf_up_r",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            # Horizontal shelf tiers with box masses
            for s_tier in range(4):
                sy_tier = sh_top_y + (s_tier * 35.0)
                elements.append(
                    SketchStroke.render_line(
                        sh_x, sy_tier, sh_x + sh_w, sy_tier,
                        seed=f"{seed}_shelf_tier_{s_tier}",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                    )
                )
                # Storage box silhouette on shelf
                if s_tier < 3:
                    box_w = 32.0 + (s_tier * 6.0)
                    box_h = 22.0
                    elements.append(
                        SketchPolygon.render(
                            [
                                (sh_x + 10, sy_tier - box_h), (sh_x + 10 + box_w, sy_tier - box_h),
                                (sh_x + 10 + box_w, sy_tier), (sh_x + 10, sy_tier)
                            ],
                            seed=f"{seed}_sh_box_{s_tier}",
                            stroke_color="#334155",
                            stroke_width=LINE_WEIGHT_CONSTRUCTION,
                            fill_color="#090d16",
                            fill_opacity=0.9,
                        )
                    )
            elements.append('</g>')

        elif env_t in (EnvironmentType.CORRIDOR, EnvironmentType.OFFICE, EnvironmentType.APARTMENT):
            # Linear perspective doors along corridor walls
            for side in [-1.0, 1.0]:
                for d_idx in range(1, 4):
                    d_x = vp_x + (side * (110.0 + d_idx * 115.0))
                    d_w = 40.0 + (d_idx * 16.0)
                    d_top_y = floor_y - 200.0 + (d_idx * 30.0)
                    d_bot_y = floor_y - 15.0 + (d_idx * 12.0)
                    elements.append(f'<g id="corridor_door_{d_idx}">')
                    elements.append(
                        SketchPolygon.render(
                            [
                                (d_x, d_top_y), (d_x + (side * d_w), d_top_y + 15),
                                (d_x + (side * d_w), d_bot_y), (d_x, d_bot_y - 5),
                            ],
                            seed=f"{seed}_door_{side}_{d_idx}",
                            stroke_color=stroke_color,
                            stroke_width=LINE_WEIGHT_INTERIOR,
                            fill_color="#0b1329",
                            fill_opacity=0.95,
                        )
                    )
                    elements.append('</g>')

        # =========================================================================
        # 2. MIDGROUND LAYER (3D STRUCTURAL COLUMNS WITH FLANGES, WORKBENCH, CRATES)
        # =========================================================================
        # Structural 3D Columns with real width and flanges (Section 10 & 11)
        # 4 heavy I-beam columns receding across the hall
        column_specs = [
            # (center_x, width, drop_shadow_side)
            (110.0, 32.0, "right"),
            (250.0, 26.0, "right"),
            (730.0, 26.0, "left"),
            (870.0, 34.0, "left"),
        ]
        for col_x, col_w, sh_side in column_specs:
            c_left = col_x - col_w * 0.5
            c_right = col_x + col_w * 0.5

            elements.append(f'<g id="structural_column_{int(col_x)}">')
            # Main column face plane
            elements.append(
                SketchPolygon.render(
                    [(c_left, 0), (c_right, 0), (c_right, floor_y + 10), (c_left, floor_y + 10)],
                    seed=f"{seed}_col_face_{col_x}",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#090d16",
                    fill_opacity=0.98,
                )
            )
            # Recessed central I-beam web channel
            ch_w = col_w * 0.45
            ch_left = col_x - ch_w * 0.5
            ch_right = col_x + ch_w * 0.5
            elements.append(
                SketchStroke.render_line(
                    ch_left, 0, ch_left, floor_y + 10,
                    seed=f"{seed}_col_flange_l_{col_x}",
                    stroke_color="#334155",
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    ch_right, 0, ch_right, floor_y + 10,
                    seed=f"{seed}_col_flange_r_{col_x}",
                    stroke_color="#334155",
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            # Rivet dots along flange
            for r_idx in range(1, 8):
                ry = r_idx * 55.0
                elements.append(f'<circle cx="{c_left + 3:.1f}" cy="{ry:.1f}" r="1.1" fill="#64748b"/>')
                elements.append(f'<circle cx="{c_right - 3:.1f}" cy="{ry:.1f}" r="1.1" fill="#64748b"/>')

            # Side drop shadow wash behind column
            sh_x = c_right if sh_side == "right" else c_left - 18.0
            elements.append(
                InkWashPolygon.render(
                    [(sh_x, 0), (sh_x + 18.0, 0), (sh_x + 18.0, floor_y + 12), (sh_x, floor_y + 12)],
                    seed=f"{seed}_col_sh_{col_x}",
                    fill_color="#020617",
                    opacity=0.45,
                )
            )
            elements.append('</g>')

        # Midground Stacked Cargo Crates (Section 11)
        crate_x = 145.0
        crate_y = floor_y - 85.0
        crate_w = 95.0
        crate_h = 85.0
        # Crate outer box
        elements.append(
            SketchPolygon.render(
                [
                    (crate_x, crate_y), (crate_x + crate_w, crate_y),
                    (crate_x + crate_w, crate_y + crate_h), (crate_x, crate_y + crate_h)
                ],
                seed=f"{seed}_crate1",
                stroke_color=stroke_color,
                stroke_width=LINE_WEIGHT_CHARACTER,
                fill_color="#0f172a",
                fill_opacity=0.96,
            )
        )
        # Crate wooden diagonal cross brace
        elements.append(
            SketchStroke.render_line(
                crate_x + 3, crate_y + 3, crate_x + crate_w - 3, crate_y + crate_h - 3,
                seed=f"{seed}_crate1_x1",
                stroke_color="#334155",
                stroke_width=LINE_WEIGHT_INTERIOR,
            )
        )
        elements.append(
            SketchStroke.render_line(
                crate_x + crate_w - 3, crate_y + 3, crate_x + 3, crate_y + crate_h - 3,
                seed=f"{seed}_crate1_x2",
                stroke_color="#334155",
                stroke_width=LINE_WEIGHT_INTERIOR,
            )
        )
        # Wood texture lines on crate
        elements.append(
            TextureRenderer.wood_grain(
                crate_x + 2, crate_y + 2, crate_w - 4, crate_h - 4,
                seed=f"{seed}_crate1_tex",
                stroke_color="#334155",
                num_planks=3,
            )
        )

        # Concrete Floor Cracks & Puddle Water Wash (Section 17)
        elements.append(
            TextureRenderer.concrete_cracks(
                x=280.0, y=floor_y + 10, w=350.0, h=80.0,
                seed=f"{seed}_floor_cracks",
                stroke_color="#334155",
                num_cracks=4,
            )
        )
        # Rain / moisture puddle reflection wash
        puddle_pts = [
            (320.0, floor_y + 40), (520.0, floor_y + 38),
            (560.0, floor_y + 70), (290.0, floor_y + 72)
        ]
        elements.append(
            InkWashPolygon.render(
                puddle_pts,
                seed=f"{seed}_puddle",
                fill_color=ACCENT_BLUE_HAZE,
                opacity=0.15,
            )
        )
        elements.append(
            SketchStroke.render_line(
                310.0, floor_y + 55, 540.0, floor_y + 55,
                seed=f"{seed}_puddle_shine",
                stroke_color="#ffffff",
                stroke_width=0.8,
                opacity=0.5,
            )
        )

        # Scattered Masonry Rubble & Debris on concrete floor (Section 11)
        elements.append('<g id="floor_debris">')
        debris_clusters = [
            (95.0, floor_y + 15.0, 14.0),
            (260.0, floor_y + 22.0, 18.0),
            (710.0, floor_y + 18.0, 12.0),
            (850.0, floor_y + 25.0, 16.0),
        ]
        for deb_idx, (deb_x, deb_y, deb_s) in enumerate(debris_clusters):
            deb_pts = [
                (deb_x, deb_y),
                (deb_x + deb_s * 0.7, deb_y - deb_s * 0.4),
                (deb_x + deb_s, deb_y + deb_s * 0.3),
                (deb_x + deb_s * 0.4, deb_y + deb_s * 0.6),
                (deb_x - deb_s * 0.2, deb_y + deb_s * 0.3),
            ]
            pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in deb_pts)
            elements.append(
                f'<polygon points="{pts_str}" fill="#090d16" stroke="#334155" stroke-width="0.8" opacity="0.85"/>'
            )
        elements.append('</g>')

        # =========================================================================
        # 3. FOREGROUND LAYER (DARK FRAMING SILHOUETTES: DOOR JAMB / OUT-OF-FOCUS CORNER)
        # =========================================================================
        if include_foreground:
            # Foreground silhouetted steel door jamb / raking pillar on screen left
            fg_pillar_w = 48.0
            fg_pillar = [
                (0, 0), (fg_pillar_w, 0),
                (fg_pillar_w + 10.0, height), (0, height)
            ]
            elements.append(
                SketchPolygon.render(
                    fg_pillar,
                    seed=f"{seed}_fg_jamb",
                    stroke_color="#1e293b",
                    stroke_width=LINE_WEIGHT_FOREGROUND,
                    fill_color="#020617",
                    fill_opacity=0.98,
                )
            )
            # Rivets on foreground door jamb
            for fg_r in range(1, 9):
                elements.append(f'<circle cx="{fg_pillar_w - 6:.1f}" cy="{fg_r * 62.0:.1f}" r="1.8" fill="#475569"/>')

            # Out-of-focus foreground crate corner silhouette on screen bottom right
            elements.append(
                f'<polygon points="{width - 90.0:.1f},{height:.1f} {width - 70.0:.1f},{height - 65.0:.1f} {width:.1f},{height - 75.0:.1f} {width:.1f},{height:.1f}" '
                f'fill="#020617" stroke="#1e293b" stroke-width="2.5" opacity="0.96"/>'
            )

        return "\n  ".join(elements)
