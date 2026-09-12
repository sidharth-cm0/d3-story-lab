"""Recognizable hand-drawn sketch props and object continuity.

Renders iconic storyboard props (dossier, flashlight, safe, phone, keys, gun, etc.)
with canonical details derived from ObjectVisualReference.
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.visual_bible import ObjectVisualReference
from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchEllipse,
    SketchPolyline,
    SketchPolygon,
    CrossHatch,
    ScribbleShadow,
    get_rng,
    get_seed_hash,
)


class PropType(str, Enum):
    """Standard storyboard prop types."""
    DOSSIER = "DOSSIER"
    DOCUMENT = "DOCUMENT"
    PHONE = "PHONE"
    KEY = "KEY"
    FLASHLIGHT = "FLASHLIGHT"
    GUN = "GUN"
    KNIFE = "KNIFE"
    BRIEFCASE = "BRIEFCASE"
    COMPUTER = "COMPUTER"
    RADIO = "RADIO"
    SAFE = "SAFE"
    VAULT_DOOR = "VAULT_DOOR"
    TABLE = "TABLE"
    CHAIR = "CHAIR"
    CAR = "CAR"
    DOOR = "DOOR"
    MONITOR = "MONITOR"
    LETTER = "LETTER"


class ObjectSketchIdentity(BaseModel):
    """Persistent visual parameters for a canonical object."""
    model_config = ConfigDict(extra="ignore")

    object_id: str
    name: str
    prop_type: PropType = PropType.DOSSIER
    width: float = 60.0
    height: float = 45.0
    accent_color: str = "#f59e0b"
    unique_marking: str = "seal"  # "seal", "stamp", "serial", "logo"
    material_tone: str = "#0f172a"

    @classmethod
    def from_reference(cls, ref: ObjectVisualReference) -> ObjectSketchIdentity:
        desc = (ref.name + " " + ref.form_factor + " " + ref.materials + " " + ref.unique_markings).lower()

        # Classify prop type
        if "dossier" in desc or "folder" in desc or "file" in desc or "ledger" in desc:
            p_type = PropType.DOSSIER
        elif "document" in desc or "paper" in desc or "sheet" in desc:
            p_type = PropType.DOCUMENT
        elif "flashlight" in desc or "torch" in desc:
            p_type = PropType.FLASHLIGHT
        elif "phone" in desc or "transceiver" in desc or "mobile" in desc:
            p_type = PropType.PHONE
        elif "key" in desc:
            p_type = PropType.KEY
        elif "safe" in desc:
            p_type = PropType.SAFE
        elif "vault" in desc:
            p_type = PropType.VAULT_DOOR
        elif "briefcase" in desc or "case" in desc:
            p_type = PropType.BRIEFCASE
        elif "gun" in desc or "pistol" in desc or "weapon" in desc or "revolver" in desc:
            p_type = PropType.GUN
        elif "knife" in desc or "blade" in desc:
            p_type = PropType.KNIFE
        elif "computer" in desc or "laptop" in desc:
            p_type = PropType.COMPUTER
        elif "radio" in desc:
            p_type = PropType.RADIO
        elif "table" in desc or "desk" in desc:
            p_type = PropType.TABLE
        elif "chair" in desc or "seat" in desc:
            p_type = PropType.CHAIR
        elif "door" in desc:
            p_type = PropType.DOOR
        elif "letter" in desc or "envelope" in desc:
            p_type = PropType.LETTER
        elif "monitor" in desc or "screen" in desc:
            p_type = PropType.MONITOR
        else:
            p_type = PropType.DOSSIER

        # Check unique markings
        marking = "seal" if ("seal" in desc or "wax" in desc) else ("stamp" if "stamp" in desc else "serial")

        return cls(
            object_id=ref.object_id,
            name=ref.name,
            prop_type=p_type,
            unique_marking=marking,
            accent_color="#f59e0b" if "gold" in desc or "brass" in desc or "amber" in desc else "#38bdf8",
        )


class PropSketchRenderer:
    """Renders canonical props into SVG using hand-drawn sketch strokes."""

    def __init__(self):
        self._identities: Dict[str, ObjectSketchIdentity] = {}

    def get_or_create_identity(
        self,
        object_id: str,
        name: str = "",
        ref: Optional[ObjectVisualReference] = None,
    ) -> ObjectSketchIdentity:
        if object_id in self._identities:
            return self._identities[object_id]

        if ref:
            ident = ObjectSketchIdentity.from_reference(ref)
        else:
            dummy_ref = ObjectVisualReference(
                object_id=object_id,
                name=name or object_id,
            )
            ident = ObjectSketchIdentity.from_reference(dummy_ref)

        self._identities[object_id] = ident
        return ident

    def render_prop(
        self,
        identity: ObjectSketchIdentity,
        cx: float,
        cy: float,
        scale: float = 1.0,
        rotation_deg: float = 0.0,
        seed: str = "prop",
        stroke_color: str = "#e2e8f0",
    ) -> str:
        """Render a specific prop template into SVG elements."""
        p_type = identity.prop_type
        elements = []

        if p_type == PropType.DOSSIER:
            # Rectangular folio, corner brass clips, fold seam, red wax seal, label band
            w = 54.0 * scale
            h = 40.0 * scale
            x = cx - w / 2
            y = cy - h / 2

            # Folio cover
            folio_pts = [
                (x, y),
                (x + w, y - 2),
                (x + w + 2, y + h),
                (x - 2, y + h + 2),
            ]
            folio_svg = SketchPolygon.render(
                folio_pts,
                seed=f"{seed}_folio",
                fill_color="#18181b",
                fill_opacity=0.92,
                stroke_color=stroke_color,
                stroke_width=2.0,
            )
            elements.append(f'<g id="dossier_folio">\n  {folio_svg}\n</g>')

            # Center fold seam
            elements.append(
                SketchStroke.render_line(
                    cx, y - 1, cx, y + h + 1,
                    seed=f"{seed}_seam",
                    stroke_color="#94a3b8",
                    stroke_width=1.5,
                )
            )
            # Corner clips
            clip_len = 6.0 * scale
            clip1 = SketchStroke.render_line(
                x, y + clip_len, x + clip_len, y,
                seed=f"{seed}_clip1",
                stroke_color=identity.accent_color,
                stroke_width=2.2,
            )
            clip2 = SketchStroke.render_line(
                x + w - clip_len, y, x + w, y + clip_len,
                seed=f"{seed}_clip2",
                stroke_color=identity.accent_color,
                stroke_width=2.2,
            )
            elements.append(f'<g id="dossier_clips">\n  {clip1}\n  {clip2}\n</g>')

            # Label band across lower front
            elements.append(
                SketchStroke.render_line(
                    x + 4, y + h * 0.65, x + w - 4, y + h * 0.65,
                    seed=f"{seed}_band",
                    stroke_color="#64748b",
                    stroke_width=2.4,
                )
            )
            # Circular wax seal
            seal_svg = SketchEllipse.render(
                cx, cy - 2, 7.0 * scale, 7.0 * scale,
                seed=f"{seed}_seal",
                stroke_color="#ef4444",
                stroke_width=1.8,
                fill_color="#7f1d1d",
                fill_opacity=0.9,
            )
            elements.append(f'<g id="dossier_seal">\n  {seal_svg}\n</g>')

        elif p_type == PropType.DOCUMENT:
            # Paper sheet with text scribble lines and folded corner
            w = 44.0 * scale
            h = 58.0 * scale
            x = cx - w / 2
            y = cy - h / 2
            corner = 10.0 * scale

            doc_pts = [
                (x, y),
                (x + w - corner, y),
                (x + w, y + corner),
                (x + w, y + h),
                (x, y + h),
            ]
            elements.append(
                SketchPolygon.render(
                    doc_pts,
                    seed=f"{seed}_doc",
                    fill_color="#f8fafc",
                    fill_opacity=0.88,
                    stroke_color="#0f172a",
                    stroke_width=1.6,
                )
            )
            # Folded dog-ear corner
            elements.append(
                SketchStroke.render_line(
                    x + w - corner, y, x + w - corner, y + corner,
                    seed=f"{seed}_fold1",
                    stroke_color="#0f172a",
                    stroke_width=1.4,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    x + w - corner, y + corner, x + w, y + corner,
                    seed=f"{seed}_fold2",
                    stroke_color="#0f172a",
                    stroke_width=1.4,
                )
            )
            # Text lines
            for t in range(5):
                ty = y + 14 * scale + (t * 8.0 * scale)
                elements.append(
                    SketchStroke.render_line(
                        x + 6, ty, x + w - 8, ty,
                        seed=f"{seed}_txt_{t}",
                        stroke_color="#334155",
                        stroke_width=1.2,
                        passes=1,
                    )
                )

        elif p_type == PropType.FLASHLIGHT:
            # Cylindrical body, grip ribs, flared lens head, beam cone
            len_b = 48.0 * scale
            rad_b = 6.0 * scale
            head_rad = 12.0 * scale

            # Cylinder body
            elements.append(
                SketchStroke.render_line(
                    cx - len_b / 2, cy - rad_b, cx + len_b * 0.25, cy - rad_b,
                    seed=f"{seed}_fl_top",
                    stroke_color=stroke_color,
                    stroke_width=2.0,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cx - len_b / 2, cy + rad_b, cx + len_b * 0.25, cy + rad_b,
                    seed=f"{seed}_fl_bot",
                    stroke_color=stroke_color,
                    stroke_width=2.0,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cx - len_b / 2, cy - rad_b, cx - len_b / 2, cy + rad_b,
                    seed=f"{seed}_fl_cap",
                    stroke_color=stroke_color,
                    stroke_width=2.2,
                )
            )
            # Grip ribs
            for r in range(4):
                rx = cx - len_b * 0.35 + (r * 6.0 * scale)
                elements.append(
                    SketchStroke.render_line(
                        rx, cy - rad_b, rx, cy + rad_b,
                        seed=f"{seed}_fl_rib_{r}",
                        stroke_color="#94a3b8",
                        stroke_width=1.4,
                    )
                )
            # Flared head
            flare_pts = [
                (cx + len_b * 0.25, cy - rad_b),
                (cx + len_b * 0.5, cy - head_rad),
                (cx + len_b * 0.5, cy + head_rad),
                (cx + len_b * 0.25, cy + rad_b),
            ]
            elements.append(
                SketchPolygon.render(
                    flare_pts,
                    seed=f"{seed}_fl_head",
                    fill_color="#1e293b",
                    fill_opacity=0.9,
                    stroke_color=stroke_color,
                    stroke_width=2.0,
                )
            )
            # Luminous beam cone
            beam_pts = [
                (cx + len_b * 0.5, cy - head_rad),
                (cx + len_b * 0.5 + 160 * scale, cy - head_rad * 3.5),
                (cx + len_b * 0.5 + 160 * scale, cy + head_rad * 3.5),
                (cx + len_b * 0.5, cy + head_rad),
            ]
            elements.append(
                f'<g id="flashlight_beam">\n'
                f'  <polygon points="{" ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in beam_pts)}" '
                f'fill="#fbbf24" fill-opacity="0.18"/>\n'
                f'</g>'
            )

        elif p_type == PropType.PHONE:
            # Smartphone or radio transceiver
            w = 22.0 * scale
            h = 42.0 * scale
            x = cx - w / 2
            y = cy - h / 2
            elements.append(
                SketchPolygon.render(
                    [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                    seed=f"{seed}_phone",
                    fill_color="#020617",
                    fill_opacity=0.95,
                    stroke_color=stroke_color,
                    stroke_width=1.8,
                )
            )
            # Screen glow
            elements.append(
                SketchPolygon.render(
                    [(x + 2, y + 4), (x + w - 2, y + 4), (x + w - 2, y + h - 6), (x + 2, y + h - 6)],
                    seed=f"{seed}_screen",
                    fill_color="#38bdf8",
                    fill_opacity=0.35,
                    stroke_color="#38bdf8",
                    stroke_width=1.2,
                )
            )

        elif p_type == PropType.KEY:
            # Key ring, serrated shaft, bow
            ring_r = 8.0 * scale
            shaft_len = 24.0 * scale
            elements.append(
                SketchEllipse.render(
                    cx - shaft_len / 2, cy, ring_r, ring_r,
                    seed=f"{seed}_key_ring",
                    stroke_color=identity.accent_color,
                    stroke_width=2.0,
                    fill_color="none",
                )
            )
            # Shaft
            elements.append(
                SketchStroke.render_line(
                    cx - shaft_len / 2 + ring_r, cy, cx + shaft_len / 2, cy,
                    seed=f"{seed}_key_shaft",
                    stroke_color=identity.accent_color,
                    stroke_width=2.5,
                )
            )
            # Teeth
            elements.append(
                SketchStroke.render_line(
                    cx + shaft_len * 0.25, cy, cx + shaft_len * 0.25, cy + 6 * scale,
                    seed=f"{seed}_tooth1",
                    stroke_color=identity.accent_color,
                    stroke_width=2.0,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cx + shaft_len * 0.42, cy, cx + shaft_len * 0.42, cy + 8 * scale,
                    seed=f"{seed}_tooth2",
                    stroke_color=identity.accent_color,
                    stroke_width=2.0,
                )
            )

        elif p_type == PropType.SAFE:
            # Heavy beveled vault safe, combination wheel, hinge bolts
            w = 80.0 * scale
            h = 80.0 * scale
            x = cx - w / 2
            y = cy - h / 2
            elements.append(
                SketchPolygon.render(
                    [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                    seed=f"{seed}_safe_body",
                    fill_color="#0f172a",
                    fill_opacity=0.95,
                    stroke_color=stroke_color,
                    stroke_width=2.5,
                )
            )
            # Inner door seam
            elements.append(
                SketchPolygon.render(
                    [(x + 8, y + 8), (x + w - 8, y + 8), (x + w - 8, y + h - 8), (x + 8, y + h - 8)],
                    seed=f"{seed}_safe_door",
                    stroke_color="#94a3b8",
                    stroke_width=1.6,
                )
            )
            # Combination wheel
            elements.append(
                SketchEllipse.render(
                    cx, cy, 14.0 * scale, 14.0 * scale,
                    seed=f"{seed}_safe_wheel",
                    stroke_color="#f8fafc",
                    stroke_width=2.2,
                    fill_color="#334155",
                    fill_opacity=0.8,
                )
            )
            # Dial spokes
            for s in range(4):
                a = math.radians(s * 45)
                dx = math.cos(a) * 14 * scale
                dy = math.sin(a) * 14 * scale
                elements.append(
                    SketchStroke.render_line(
                        cx - dx, cy - dy, cx + dx, cy + dy,
                        seed=f"{seed}_spoke_{s}",
                        stroke_color="#cbd5e1",
                        stroke_width=1.5,
                    )
                )

        elif p_type == PropType.GUN:
            # Semi-auto pistol silhouette
            elements.append(
                SketchStroke.render_line(
                    cx - 16 * scale, cy - 6 * scale, cx + 18 * scale, cy - 6 * scale,
                    seed=f"{seed}_barrel",
                    stroke_color=stroke_color,
                    stroke_width=4.0,
                )
            )
            elements.append(
                SketchStroke.render_line(
                    cx - 12 * scale, cy - 6 * scale, cx - 18 * scale, cy + 16 * scale,
                    seed=f"{seed}_grip",
                    stroke_color=stroke_color,
                    stroke_width=5.0,
                )
            )
            elements.append(
                SketchEllipse.render(
                    cx - 6 * scale, cy + 2 * scale, 5 * scale, 5 * scale,
                    seed=f"{seed}_guard",
                    stroke_color=stroke_color,
                    stroke_width=1.6,
                )
            )

        elif p_type == PropType.TABLE:
            # Wooden / steel desk surface in perspective
            w = 120.0 * scale
            d = 30.0 * scale
            h_leg = 45.0 * scale
            top_pts = [
                (cx - w / 2, cy),
                (cx + w / 2, cy),
                (cx + w * 0.42, cy - d),
                (cx - w * 0.42, cy - d),
            ]
            elements.append(
                SketchPolygon.render(
                    top_pts,
                    seed=f"{seed}_tbl_top",
                    fill_color="#1e293b",
                    fill_opacity=0.9,
                    stroke_color=stroke_color,
                    stroke_width=2.0,
                )
            )
            # Legs
            elements.append(SketchStroke.render_line(cx - w / 2 + 4, cy, cx - w / 2 + 4, cy + h_leg, seed=f"{seed}_leg1", stroke_color=stroke_color, stroke_width=2.2))
            elements.append(SketchStroke.render_line(cx + w / 2 - 4, cy, cx + w / 2 - 4, cy + h_leg, seed=f"{seed}_leg2", stroke_color=stroke_color, stroke_width=2.2))
            elements.append(SketchStroke.render_line(cx - w * 0.42 + 4, cy - d, cx - w * 0.42 + 4, cy + h_leg - d, seed=f"{seed}_leg3", stroke_color="#64748b", stroke_width=1.6))
            elements.append(SketchStroke.render_line(cx + w * 0.42 - 4, cy - d, cx + w * 0.42 - 4, cy + h_leg - d, seed=f"{seed}_leg4", stroke_color="#64748b", stroke_width=1.6))

        else:
            # Generic recognizable prop box
            w = 36.0 * scale
            h = 28.0 * scale
            elements.append(
                SketchPolygon.render(
                    [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)],
                    seed=f"{seed}_box",
                    fill_color="#18181b",
                    fill_opacity=0.9,
                    stroke_color=stroke_color,
                    stroke_width=2.0,
                )
            )

        return "\n  ".join(elements)
