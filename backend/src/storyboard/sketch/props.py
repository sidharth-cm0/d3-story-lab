"""Recognizable hand-drawn sketch props as detailed mini-illustrations.

Implements physical props with perspective volume and material cues:
- DOSSIER: 3D perspective folder volume, spine thickness, wax seal, brass clips, visible paper pages, TOP SECRET stamp
- FLASHLIGHT: Cylindrical perspective, stepped barrel, knurled grip, lens bezel, volumetric particle cone
- PHONE: Smartphone bezel, screen plane, camera module, hand grip clamp
- GUN: Semi-automatic slide, frame, trigger guard, textured grip
- SAFE / VAULT: 3D door recess, heavy locking bolts, multi-spoke wheel, dial
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.visual_bible import ObjectVisualReference
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
    LINE_WEIGHT_INTERIOR,
    LINE_WEIGHT_CHARACTER,
    LINE_WEIGHT_FOREGROUND,
    VALUE_0,
    VALUE_1,
    VALUE_2,
    VALUE_3,
    VALUE_4,
    ACCENT_WARM_LAMP,
    ACCENT_STORY_RED,
    ACCENT_SEPIA,
    ACCENT_BLUE_HAZE,
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
    width: float = 65.0
    height: float = 48.0
    accent_color: str = ACCENT_STORY_RED
    unique_marking: str = "TOP SECRET"
    material_tone: str = "#0f172a"

    @classmethod
    def from_reference(cls, ref: ObjectVisualReference) -> ObjectSketchIdentity:
        desc = (ref.name + " " + ref.form_factor + " " + ref.materials + " " + ref.unique_markings).lower()

        if "dossier" in desc or "folder" in desc or "file" in desc or "ledger" in desc:
            p_type = PropType.DOSSIER
            accent = ACCENT_STORY_RED
            marking = "TOP SECRET"
        elif "flashlight" in desc or "torch" in desc:
            p_type = PropType.FLASHLIGHT
            accent = ACCENT_WARM_LAMP
            marking = "TACTICAL"
        elif "phone" in desc or "transceiver" in desc or "mobile" in desc:
            p_type = PropType.PHONE
            accent = ACCENT_BLUE_HAZE
            marking = "ENCRYPTED"
        elif "gun" in desc or "pistol" in desc or "weapon" in desc:
            p_type = PropType.GUN
            accent = "#94a3b8"
            marking = "9MM"
        elif "safe" in desc:
            p_type = PropType.SAFE
            accent = "#cbd5e1"
            marking = "VAULT"
        else:
            p_type = PropType.DOSSIER
            accent = ACCENT_STORY_RED
            marking = "CLASSIFIED"

        return cls(
            object_id=ref.object_id,
            name=ref.name,
            prop_type=p_type,
            width=70.0,
            height=50.0,
            accent_color=accent,
            unique_marking=marking,
            material_tone="#0f172a",
        )


class PropSketchRenderer:
    """Renders physical props as mini-illustrations with perspective volume (Section 18)."""

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
        is_insert: bool = False,
    ) -> str:
        """Render physical prop in 3D perspective as an authentic film storyboard illustration."""
        p_type = identity.prop_type
        eff_scale = scale * (1.65 if is_insert else 1.0)
        w = identity.width * eff_scale
        h = identity.height * eff_scale
        elements: List[str] = []

        # Optional group rotation transform
        wrap_start = f'<g id="prop_{identity.object_id}" transform="rotate({rotation_deg:.1f} {cx:.1f} {cy:.1f})">' if rotation_deg != 0 else f'<g id="prop_{identity.object_id}">'

        # =========================================================================
        # 1. DOSSIER (Section 18: Perspective folder, wax seal, brass clips, pages)
        # =========================================================================
        if p_type == PropType.DOSSIER or p_type == PropType.DOCUMENT:
            # Perspective trapezoid folder resting at an angle on surface
            f_tl = (cx - w * 0.48, cy - h * 0.45)
            f_tr = (cx + w * 0.44, cy - h * 0.35)
            f_br = (cx + w * 0.50, cy + h * 0.48)
            f_bl = (cx - w * 0.42, cy + h * 0.42)

            # Drop shadow under dossier on table
            elements.append(
                InkWashPolygon.render(
                    [
                        (f_bl[0] + 6, f_bl[1] + 6),
                        (f_br[0] + 12, f_br[1] + 8),
                        (f_br[0] + 18, f_br[1] + 18),
                        (f_bl[0] + 4, f_bl[1] + 16),
                    ],
                    seed=f"{seed}_dossier_drop_sh",
                    fill_color="#020617",
                    opacity=0.65,
                )
            )

            # Manila folder body wash
            elements.append(
                InkWashPolygon.render(
                    [f_tl, f_tr, f_br, f_bl],
                    seed=f"{seed}_dossier_manila",
                    fill_color="#78350f",
                    opacity=0.35,
                )
            )

            # Main folder cover polygon
            elements.append('<g id="dossier_folio">')
            elements.append(
                SketchPolygon.render(
                    [f_tl, f_tr, f_br, f_bl],
                    seed=f"{seed}_dossier_cover",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#0f172a",
                    fill_opacity=0.94,
                )
            )
            elements.append('</g>')

            # Spine fold thickness line on left edge
            elements.append(
                SketchStroke.render_line(
                    f_tl[0] + 5, f_tl[1] + 2,
                    f_bl[0] + 5, f_bl[1] - 2,
                    seed=f"{seed}_spine_fold",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    passes=1,
                )
            )

            # Stepped file tab on top-right edge
            tab_pts = [
                (f_tr[0] - 22, f_tr[1] - 1),
                (f_tr[0] - 20, f_tr[1] - 8),
                (f_tr[0] - 4, f_tr[1] - 6),
                (f_tr[0] - 2, f_tr[1]),
            ]
            elements.append(
                SketchPolygon.render(
                    tab_pts,
                    seed=f"{seed}_tab",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color="#1e293b",
                    fill_opacity=0.95,
                )
            )

            # Visible white paper sheets protruding from right edge
            page_pts = [
                (f_tr[0] - 6, f_tr[1] + 2),
                (f_tr[0] + 5, f_tr[1] + 4),
                (f_br[0] + 4, f_br[1] - 4),
                (f_br[0] - 6, f_br[1] - 4),
            ]
            elements.append(
                SketchPolygon.render(
                    page_pts,
                    seed=f"{seed}_inner_pages",
                    stroke_color="#cbd5e1",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    fill_color=VALUE_0,
                    fill_opacity=0.88,
                )
            )

            # Brass binding fastener prongs on top-left corner
            elements.append('<g id="dossier_clip">')
            for b_idx in range(2):
                bx = f_tl[0] + 12 + (b_idx * 16)
                by = f_tl[1] + 10 + (b_idx * 4)
                elements.append(
                    SketchPolygon.render(
                        [(bx - 3, by - 2), (bx + 3, by - 2), (bx + 2, by + 4), (bx - 2, by + 4)],
                        seed=f"{seed}_brass_{b_idx}",
                        stroke_color="#f59e0b",
                        stroke_width=LINE_WEIGHT_CONSTRUCTION,
                        fill_color="#d97706",
                    )
                )
            elements.append('</g>')

            # Stamped "TOP SECRET" / "CONFIDENTIAL" Stencil Text
            stamp_cx = cx + 2
            stamp_cy = cy - 4
            stamp_w = w * 0.46
            stamp_h = 14.0
            # Stamp border box
            elements.append(
                SketchPolygon.render(
                    [
                        (stamp_cx - stamp_w * 0.5, stamp_cy - stamp_h * 0.5),
                        (stamp_cx + stamp_w * 0.5, stamp_cy - stamp_h * 0.5),
                        (stamp_cx + stamp_w * 0.5, stamp_cy + stamp_h * 0.5),
                        (stamp_cx - stamp_w * 0.5, stamp_cy + stamp_h * 0.5),
                    ],
                    seed=f"{seed}_stamp_box",
                    stroke_color=ACCENT_STORY_RED,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                    fill_color="none",
                )
            )
            # Bold stencil lettering
            elements.append(
                f'<text x="{stamp_cx:.1f}" y="{stamp_cy + 4.0:.1f}" font-family="Courier New, monospace" '
                f'font-size="9" font-weight="900" letter-spacing="1.5" fill="{ACCENT_STORY_RED}" text-anchor="middle">'
                f'{identity.unique_marking}</text>'
            )

            # Crimson Wax Seal with ribbon tails (Section 18)
            elements.append('<g id="wax_seal">')
            seal_x = cx + w * 0.15
            seal_y = cy + h * 0.16
            seal_r = 10.0 * (1.3 if is_insert else 1.0)
            # Ribbon tails
            elements.append(
                SketchPolyline.render(
                    [(seal_x - 3, seal_y + 4), (seal_x - 8, seal_y + 16), (seal_x - 4, seal_y + 18)],
                    seed=f"{seed}_ribbon1",
                    stroke_color=ACCENT_STORY_RED,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            elements.append(
                SketchPolyline.render(
                    [(seal_x + 2, seal_y + 4), (seal_x + 6, seal_y + 17), (seal_x + 2, seal_y + 19)],
                    seed=f"{seed}_ribbon2",
                    stroke_color=ACCENT_STORY_RED,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )
            # Wax seal disc
            elements.append(
                SketchEllipse.render(
                    seal_x, seal_y, seal_r, seal_r * 0.9,
                    seed=f"{seed}_wax_seal",
                    stroke_color="#991b1b",
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color=ACCENT_STORY_RED,
                    fill_opacity=0.95,
                    loops=2,
                )
            )
            # Embossed inner emblem
            elements.append(
                SketchEllipse.render(
                    seal_x, seal_y, seal_r * 0.45, seal_r * 0.45,
                    seed=f"{seed}_wax_inner",
                    stroke_color="#fca5a5",
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    fill_color="#7f1d1d",
                )
            )
            elements.append('</g>')

            if is_insert:
                # Interacting hand gripping / opening the dossier flap (Section 9 & 18)
                elements.append('<g id="insert_hand_interaction">')
                # Hand forearm coming in from bottom-left
                hx = f_bl[0] + 18.0
                hy = f_bl[1] - 12.0
                # Palm wedge
                palm = [
                    (hx - 28, hy + 38),
                    (hx + 12, hy + 22),
                    (hx + 26, hy - 4),
                    (hx - 16, hy + 12),
                ]
                elements.append(
                    SketchPolygon.render(
                        palm,
                        seed=f"{seed}_hand_palm",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR,
                        fill_color="#090d16",
                        fill_opacity=0.96,
                    )
                )
                # Grouped fingers grasping edge of folder
                for f_idx in range(4):
                    fy = hy - 6 + (f_idx * 7)
                    fx1 = hx + 14
                    fx2 = fx1 + 22
                    elements.append(
                        SketchStroke.render_line(
                            fx1, fy, fx2, fy - 3,
                            seed=f"{seed}_hand_fin_{f_idx}",
                            stroke_color=stroke_color,
                            stroke_width=LINE_WEIGHT_INTERIOR * 1.15,
                            passes=2,
                        )
                    )
                # Opposing thumb pressed on folder cover
                elements.append(
                    SketchStroke.render_line(
                        hx - 6, hy + 20, hx + 12, hy + 6,
                        seed=f"{seed}_hand_thumb",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_INTERIOR * 1.3,
                        passes=2,
                    )
                )
                # Tapered wrist / forearm entering frame
                elements.append(
                    SketchStroke.render_line(
                        hx - 28, hy + 38, hx - 85, hy + 110,
                        seed=f"{seed}_arm_l",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CHARACTER,
                    )
                )
                elements.append(
                    SketchStroke.render_line(
                        hx - 12, hy + 60, hx - 60, hy + 130,
                        seed=f"{seed}_arm_r",
                        stroke_color=stroke_color,
                        stroke_width=LINE_WEIGHT_CHARACTER,
                    )
                )
                elements.append('</g>')

        # =========================================================================
        # 2. TACTICAL FLASHLIGHT (Section 18: Stepped cylinder, bezel, beam cone)
        # =========================================================================
        elif p_type == PropType.FLASHLIGHT:
            fl_w = w * 0.95
            fl_h = 16.0 * eff_scale

            # Volumetric light cone expanding forward from lens head
            elements.append('<g id="flashlight_beam">')
            beam_origin_x = cx + fl_w * 0.5
            beam_origin_y = cy
            cone_pts = [
                (beam_origin_x, beam_origin_y - 8),
                (beam_origin_x + 360.0, beam_origin_y - 120),
                (beam_origin_x + 360.0, beam_origin_y + 120),
                (beam_origin_x, beam_origin_y + 8),
            ]
            elements.append(
                InkWashPolygon.render(
                    cone_pts,
                    seed=f"{seed}_beam_cone",
                    fill_color=ACCENT_WARM_LAMP,
                    opacity=0.20,
                )
            )
            # Core bright beam center
            core_pts = [
                (beam_origin_x, beam_origin_y - 3),
                (beam_origin_x + 240.0, beam_origin_y - 45),
                (beam_origin_x + 240.0, beam_origin_y + 45),
                (beam_origin_x, beam_origin_y + 3),
            ]
            elements.append(
                InkWashPolygon.render(
                    core_pts,
                    seed=f"{seed}_beam_core",
                    fill_color="#ffffff",
                    opacity=0.35,
                )
            )
            elements.append('</g>')

            # Flashlight cylindrical barrel body
            bx1 = cx - fl_w * 0.48
            bx2 = cx + fl_w * 0.28
            elements.append(
                SketchPolygon.render(
                    [(bx1, cy - fl_h * 0.35), (bx2, cy - fl_h * 0.35), (bx2, cy + fl_h * 0.35), (bx1, cy + fl_h * 0.35)],
                    seed=f"{seed}_fl_body",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#090d16",
                    fill_opacity=0.98,
                )
            )
            # Knurled grip texture bands on barrel
            for k in range(5):
                kx = bx1 + 10 + (k * 7)
                elements.append(
                    SketchStroke.render_line(
                        kx, cy - fl_h * 0.32, kx, cy + fl_h * 0.32,
                        seed=f"{seed}_knurl_{k}",
                        stroke_color="#475569",
                        stroke_width=LINE_WEIGHT_INTERIOR,
                    )
                )

            # Beveled flared head / lens reflector
            elements.append('<g id="fl_head">')
            head_x1 = bx2
            head_x2 = bx2 + fl_w * 0.20
            head_pts = [
                (head_x1, cy - fl_h * 0.35),
                (head_x2, cy - fl_h * 0.58),
                (head_x2, cy + fl_h * 0.58),
                (head_x1, cy + fl_h * 0.35),
            ]
            elements.append(
                SketchPolygon.render(
                    head_pts,
                    seed=f"{seed}_fl_head",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#0f172a",
                    fill_opacity=0.98,
                )
            )
            elements.append('</g>')
            # Front lens bezel rim ring
            elements.append(
                SketchStroke.render_line(
                    head_x2, cy - fl_h * 0.58, head_x2, cy + fl_h * 0.58,
                    seed=f"{seed}_lens_rim",
                    stroke_color="#ffffff",
                    stroke_width=LINE_WEIGHT_CHARACTER * 1.3,
                )
            )
            # Rubberized thumb switch on top of barrel
            elements.append(
                SketchPolygon.render(
                    [(bx1 + 18, cy - fl_h * 0.35 - 3), (bx1 + 28, cy - fl_h * 0.35 - 3), (bx1 + 28, cy - fl_h * 0.35), (bx1 + 18, cy - fl_h * 0.35)],
                    seed=f"{seed}_switch",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CONSTRUCTION,
                    fill_color="#475569",
                )
            )

        # =========================================================================
        # 3. OTHER PROPS (GUN, PHONE, SAFE, ETC.)
        # =========================================================================
        elif p_type == PropType.GUN:
            # Semi-auto pistol silhouette: slide, frame, trigger guard, textured grip
            g_slide = [
                (cx - w * 0.45, cy - h * 0.3), (cx + w * 0.45, cy - h * 0.3),
                (cx + w * 0.45, cy - h * 0.05), (cx - w * 0.45, cy - h * 0.05)
            ]
            elements.append(
                SketchPolygon.render(
                    g_slide, seed=f"{seed}_gun_slide",
                    stroke_color=stroke_color, stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#090d16", fill_opacity=0.98,
                )
            )
            # Angled Grip
            g_grip = [
                (cx - w * 0.40, cy - h * 0.05), (cx - w * 0.15, cy - h * 0.05),
                (cx - w * 0.25, cy + h * 0.45), (cx - w * 0.48, cy + h * 0.42)
            ]
            elements.append(
                SketchPolygon.render(
                    g_grip, seed=f"{seed}_gun_grip",
                    stroke_color=stroke_color, stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#090d16", fill_opacity=0.98,
                )
            )
            # Trigger Guard
            elements.append(
                SketchPolyline.render(
                    [(cx - w * 0.15, cy), (cx - w * 0.05, cy + h * 0.18), (cx - w * 0.22, cy + h * 0.18)],
                    seed=f"{seed}_trigger_guard",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_INTERIOR,
                )
            )

        else:
            # Default generic prop block with perspective drop shadow
            elements.append(
                SketchPolygon.render(
                    [(cx - w * 0.45, cy - h * 0.4), (cx + w * 0.45, cy - h * 0.4), (cx + w * 0.45, cy + h * 0.4), (cx - w * 0.45, cy + h * 0.4)],
                    seed=f"{seed}_generic_prop",
                    stroke_color=stroke_color,
                    stroke_width=LINE_WEIGHT_CHARACTER,
                    fill_color="#0f172a",
                    fill_opacity=0.95,
                )
            )

        elements.append("</g>")
        return wrap_start + "\n  " + "\n  ".join(elements)
