"""Architectural environment sketch renderer and location continuity.

Renders distinct, recognizable storyboard environments (warehouse, corridor,
office, vault, rooftop, etc.) with stable perspective geometry and landmarks.
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
    PerspectiveGrid,
    CrossHatch,
    ScribbleShadow,
    get_rng,
    get_seed_hash,
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

        if "corridor" in desc or "hall" in desc or "hallway" in desc:
            env_t = EnvironmentType.CORRIDOR
            vp = (480.0 + (rng.random() - 0.5) * 60, 260.0 + (rng.random() - 0.5) * 30)
        elif "warehouse" in desc:
            env_t = EnvironmentType.WAREHOUSE
            vp = (480.0, 260.0)
        elif "office" in desc or "penthouse" in desc or "executive" in desc:
            env_t = EnvironmentType.OFFICE
            vp = (520.0, 270.0)
        elif "vault" in desc or "safe" in desc or "deposit" in desc:
            env_t = EnvironmentType.VAULT
            vp = (480.0, 270.0)
        elif "rooftop" in desc or "roof" in desc:
            env_t = EnvironmentType.ROOFTOP
            vp = (480.0, 310.0)
        elif "street" in desc or "alley" in desc or "exterior" in desc:
            env_t = EnvironmentType.STREET
            vp = (420.0, 280.0)
        elif "interrogation" in desc or "cell" in desc:
            env_t = EnvironmentType.INTERROGATION_ROOM
            vp = (480.0, 250.0)
        elif "stair" in desc or "steps" in desc:
            env_t = EnvironmentType.STAIRCASE
            vp = (450.0, 260.0)
        elif "apartment" in desc or "living" in desc:
            env_t = EnvironmentType.APARTMENT
            vp = (480.0, 280.0)
        elif "forest" in desc or "woods" in desc:
            env_t = EnvironmentType.FOREST
            vp = (480.0, 300.0)
        elif "vehicle" in desc or "car" in desc:
            env_t = EnvironmentType.VEHICLE_INTERIOR
            vp = (480.0, 270.0)
        elif "industrial" in desc or "boiler" in desc or "dock" in desc:
            env_t = EnvironmentType.INDUSTRIAL_ROOM
            vp = (480.0, 260.0)
        else:
            env_t = EnvironmentType.WAREHOUSE
            vp = (480.0, 260.0)

        return cls(
            location_id=ref.location_id,
            name=ref.name,
            env_type=env_t,
            vanishing_point=vp,
            pillar_spacing=120.0 + rng.random() * 40.0,
            window_count=3 + (seed_int % 3),
            door_position_x=180.0 + rng.random() * 120.0,
            floor_level_y=420.0,
        )


class EnvironmentSketchRenderer:
    """Renders location perspective backgrounds using hand-drawn sketch lines."""

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
        stroke_color: str = "#475569",
    ) -> str:
        env_t = identity.env_type
        vp_x, vp_y = identity.vanishing_point
        floor_y = identity.floor_level_y
        elements = []

        if env_t == EnvironmentType.CORRIDOR:
            # Strong central vanishing point, repeating door frames, overhead lights
            elements.append(
                PerspectiveGrid.render(
                    vp_x=vp_x, vp_y=vp_y, bottom_y=height, width=width,
                    seed=f"{seed}_corr_floor",
                    num_radials=7,
                    num_horizontals=4,
                    stroke_color=stroke_color,
                    opacity=0.45,
                )
            )
            # Ceiling lines
            elements.append(
                PerspectiveGrid.render(
                    vp_x=vp_x, vp_y=vp_y, bottom_y=0.0, width=width,
                    seed=f"{seed}_corr_ceil",
                    num_radials=5,
                    num_horizontals=3,
                    stroke_color=stroke_color,
                    opacity=0.35,
                )
            )
            # Door frames on left and right walls receding
            door_elements = []
            for i in range(1, 4):
                t = i / 4.0
                # Left door
                lx = vp_x - (vp_x * t)
                ly_top = vp_y - ((vp_y - 120) * t)
                ly_bot = vp_y + ((floor_y - vp_y) * t)
                door_w = 45 * t
                door_elements.append(
                    SketchPolygon.render(
                        [(lx, ly_top), (lx + door_w, ly_top + 10), (lx + door_w, ly_bot), (lx, ly_bot)],
                        seed=f"{seed}_ldoor_{i}",
                        stroke_color=stroke_color,
                        stroke_width=1.6,
                        fill_color="#020617",
                        fill_opacity=0.4,
                    )
                )
                # Right door
                rx = vp_x + ((width - vp_x) * t)
                ry_top = vp_y - ((vp_y - 120) * t)
                ry_bot = vp_y + ((floor_y - vp_y) * t)
                door_elements.append(
                    SketchPolygon.render(
                        [(rx - door_w, ry_top + 10), (rx, ry_top), (rx, ry_bot), (rx - door_w, ry_bot)],
                        seed=f"{seed}_rdoor_{i}",
                        stroke_color=stroke_color,
                        stroke_width=1.6,
                        fill_color="#020617",
                        fill_opacity=0.4,
                    )
                )
            elements.append(f'<g id="corridor_doors">\n  ' + "\n  ".join(door_elements) + "\n</g>")

        elif env_t == EnvironmentType.WAREHOUSE:
            # I-beams, stacked crates, high multi-pane industrial windows, hanging practical lights
            # Perspective floor
            elements.append(
                PerspectiveGrid.render(
                    vp_x=vp_x, vp_y=vp_y + 40, bottom_y=height, width=width,
                    seed=f"{seed}_wh_floor",
                    num_radials=8,
                    num_horizontals=5,
                    stroke_color=stroke_color,
                    opacity=0.45,
                )
            )
            # Structural vertical I-beams
            beam_elements = []
            beam_x_positions = [80.0, 240.0, 720.0, 880.0]
            for bx in beam_x_positions:
                beam_elements.append(
                    SketchStroke.render_line(
                        bx, 0, bx, floor_y + 20,
                        seed=f"{seed}_beam1_{bx}",
                        stroke_color=stroke_color,
                        stroke_width=3.2,
                    )
                )
                beam_elements.append(
                    SketchStroke.render_line(
                        bx + 14, 0, bx + 14, floor_y + 20,
                        seed=f"{seed}_beam2_{bx}",
                        stroke_color=stroke_color,
                        stroke_width=3.2,
                    )
                )
                # Diagonal truss braces
                beam_elements.append(
                    SketchStroke.render_line(
                        bx, 40, bx + 14, 90,
                        seed=f"{seed}_truss_{bx}",
                        stroke_color="#334155",
                        stroke_width=1.4,
                    )
                )
            elements.append(f'<g id="structural_i_beams">\n  ' + "\n  ".join(beam_elements) + "\n</g>")

            # High Industrial Windows (paned grid)
            window_elements = []
            for w_idx in range(identity.window_count):
                wx = 320.0 + (w_idx * 85.0)
                wy = 60.0
                ww = 65.0
                wh = 95.0
                window_elements.append(
                    SketchPolygon.render(
                        [(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)],
                        seed=f"{seed}_win_{w_idx}",
                        stroke_color="#64748b",
                        stroke_width=1.8,
                        fill_color="#0284c7",
                        fill_opacity=0.15,
                    )
                )
                # Panes
                window_elements.append(SketchStroke.render_line(wx + ww / 2, wy, wx + ww / 2, wy + wh, seed=f"{seed}_wp1_{w_idx}", stroke_color="#475569", stroke_width=1.2))
                window_elements.append(SketchStroke.render_line(wx, wy + wh / 2, wx + ww, wy + wh / 2, seed=f"{seed}_wp2_{w_idx}", stroke_color="#475569", stroke_width=1.2))
            elements.append(f'<g id="industrial_windows">\n  ' + "\n  ".join(window_elements) + "\n</g>")
            # Hanging industrial lamps
            for lx in [380.0, 580.0]:
                elements.append(SketchStroke.render_line(lx, 0, lx, 140, seed=f"{seed}_cord_{lx}", stroke_color="#94a3b8", stroke_width=1.5))
                elements.append(SketchEllipse.render(lx, 145, 18, 8, seed=f"{seed}_shade_{lx}", stroke_color="#cbd5e1", stroke_width=2.0, fill_color="#fbbf24", fill_opacity=0.3))

        elif env_t == EnvironmentType.OFFICE:
            # Floor-to-ceiling modern glass windows, distant city skyline grid, executive desk
            # Window mullions
            for m in range(5):
                mx = 140.0 + (m * 180.0)
                elements.append(
                    SketchStroke.render_line(
                        mx, 0, mx, floor_y - 20,
                        seed=f"{seed}_mullion_{m}",
                        stroke_color="#334155",
                        stroke_width=2.5,
                    )
                )
                # Horizontal blinds / dividers
                for b in range(1, 4):
                    by = b * 90.0
                    elements.append(
                        SketchStroke.render_line(
                            mx - 80, by, mx + 80, by,
                            seed=f"{seed}_blind_{m}_{b}",
                            stroke_color="#1e293b",
                            stroke_width=1.2,
                            opacity=0.4,
                        )
                    )
            # Skyline silhouette in background
            elements.append(
                SketchPolyline.render(
                    [(0, 240), (120, 240), (120, 180), (220, 180), (220, 260), (380, 260), (380, 150), (460, 150), (460, 280), (620, 280), (620, 200), (740, 200), (740, 290), (960, 290)],
                    seed=f"{seed}_skyline",
                    stroke_color="#1e293b",
                    stroke_width=1.5,
                    opacity=0.5,
                )
            )
            # Floor line
            elements.append(SketchStroke.render_line(0, floor_y, width, floor_y, seed=f"{seed}_off_floor", stroke_color=stroke_color, stroke_width=2.2))

        elif env_t == EnvironmentType.VAULT:
            # Circular heavy vault door, grid of safe deposit boxes, steel wall bolts
            elements.append(
                SketchEllipse.render(
                    vp_x, vp_y, 140.0, 140.0,
                    seed=f"{seed}_vault_rim",
                    stroke_color=stroke_color,
                    stroke_width=3.5,
                    fill_color="#0f172a",
                    fill_opacity=0.85,
                )
            )
            # Gear teeth around vault rim
            for g in range(12):
                a = math.radians(g * 30)
                rx1 = vp_x + math.cos(a) * 140.0
                ry1 = vp_y + math.sin(a) * 140.0
                rx2 = vp_x + math.cos(a) * 156.0
                ry2 = vp_y + math.sin(a) * 156.0
                elements.append(
                    SketchStroke.render_line(
                        rx1, ry1, rx2, ry2,
                        seed=f"{seed}_gear_{g}",
                        stroke_color=stroke_color,
                        stroke_width=2.5,
                    )
                )
            # Deposit boxes on side walls
            for row in range(4):
                for col in range(3):
                    bx = 40.0 + (col * 55.0)
                    by = 120.0 + (row * 60.0)
                    elements.append(
                        SketchPolygon.render(
                            [(bx, by), (bx + 48, by), (bx + 48, by + 50), (bx, by + 50)],
                            seed=f"{seed}_box_{row}_{col}",
                            stroke_color="#334155",
                            stroke_width=1.4,
                            fill_color="#020617",
                            fill_opacity=0.5,
                        )
                    )

        elif env_t == EnvironmentType.ROOFTOP:
            # Low parapet wall, water tower silhouette, city skyline, rooftop exhaust vents
            parapet_y = floor_y - 40
            elements.append(
                SketchStroke.render_line(
                    0, parapet_y, width, parapet_y,
                    seed=f"{seed}_roof_parapet",
                    stroke_color=stroke_color,
                    stroke_width=3.0,
                )
            )
            # Water tower on legs (left side)
            elements.append(
                SketchPolygon.render(
                    [(120, 140), (200, 140), (200, 240), (120, 240)],
                    seed=f"{seed}_wtower",
                    stroke_color="#334155",
                    stroke_width=2.0,
                    fill_color="#020617",
                    fill_opacity=0.8,
                )
            )
            elements.append(SketchStroke.render_line(130, 240, 120, parapet_y, seed=f"{seed}_wtleg1", stroke_color="#334155", stroke_width=2.2))
            elements.append(SketchStroke.render_line(190, 240, 200, parapet_y, seed=f"{seed}_wtleg2", stroke_color="#334155", stroke_width=2.2))
            # Distant skyscrapers behind parapet
            elements.append(
                SketchPolyline.render(
                    [(240, parapet_y), (240, 80), (340, 80), (340, parapet_y), (420, parapet_y), (420, 110), (520, 110), (520, parapet_y), (680, parapet_y), (680, 60), (820, 60), (820, parapet_y)],
                    seed=f"{seed}_roof_skyline",
                    stroke_color="#1e293b",
                    stroke_width=1.8,
                    opacity=0.6,
                )
            )

        elif env_t == EnvironmentType.INTERROGATION_ROOM:
            # Bare concrete room, single low hanging bulb, two-way mirror frame
            elements.append(
                SketchPolygon.render(
                    [(180, 100), (460, 100), (460, 320), (180, 320)],
                    seed=f"{seed}_mirror",
                    stroke_color="#64748b",
                    stroke_width=2.5,
                    fill_color="#020617",
                    fill_opacity=0.6,
                )
            )
            # Hanging single bare bulb in center
            elements.append(SketchStroke.render_line(vp_x, 0, vp_x, 160, seed=f"{seed}_bulb_cord", stroke_color="#94a3b8", stroke_width=1.6))
            elements.append(SketchEllipse.render(vp_x, 165, 8, 12, seed=f"{seed}_bulb", stroke_color="#fef08a", stroke_width=2.0, fill_color="#fef08a", fill_opacity=0.85))
            # Floor line
            elements.append(SketchStroke.render_line(0, floor_y, width, floor_y, seed=f"{seed}_interr_fl", stroke_color=stroke_color, stroke_width=2.0))

        else:
            # Generic atmospheric architectural interior
            elements.append(
                PerspectiveGrid.render(
                    vp_x=vp_x, vp_y=vp_y, bottom_y=height, width=width,
                    seed=f"{seed}_gen_floor",
                    num_radials=6,
                    num_horizontals=4,
                    stroke_color=stroke_color,
                    opacity=0.4,
                )
            )
            elements.append(SketchStroke.render_line(0, floor_y, width, floor_y, seed=f"{seed}_gen_line", stroke_color=stroke_color, stroke_width=2.0))

        return "\n  ".join(elements)
