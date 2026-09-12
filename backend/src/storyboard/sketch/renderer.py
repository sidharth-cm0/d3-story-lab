"""HandDrawnStoryboardProvider - 100% offline deterministic sketch storyboard engine.

Generates production film storyboard drawings with hand-drawn pencil/ink aesthetics,
distinct character identities, recognizable props, and architectural environments.
"""

from __future__ import annotations
import html
import logging
from typing import Dict, Any, Optional, List

from src.storyboard.models import (
    StoryboardPanel,
    StoryboardImageStatus,
    ShotType,
    CameraAngle,
)
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.image_provider import (
    StoryboardImageProvider,
    StoryboardImageResult,
    ProviderState,
)
from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchPolygon,
    SketchPolyline,
    get_rng,
)
from src.storyboard.sketch.character import CharacterSketchRenderer
from src.storyboard.sketch.props import PropSketchRenderer
from src.storyboard.sketch.environment import EnvironmentSketchRenderer
from src.storyboard.sketch.staging import SceneStager, StagedScene
from src.storyboard.sketch.lighting import (
    LightingSketchRenderer,
    SketchStyle,
    STYLE_PALETTES,
)
from src.storyboard.sketch.motion import MotionSketchRenderer

logger = logging.getLogger(__name__)


class HandDrawnStoryboardProvider(StoryboardImageProvider):
    """Offline deterministic storyboard engine producing authentic hand-drawn sketches.
    
    Requires:
    - NO API KEY
    - NO NETWORK
    - NO BILLING
    - NO CLOUD PROVIDER
    """

    def __init__(
        self,
        asset_store: Optional[StoryboardAssetStore] = None,
        style: SketchStyle = SketchStyle.PENCIL_NOIR,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.char_renderer = CharacterSketchRenderer()
        self.prop_renderer = PropSketchRenderer()
        self.env_renderer = EnvironmentSketchRenderer()
        self.style = style

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "provider": "hand_drawn_storyboard",
            "selected_model": "deterministic_sketch_v1",
            "style": "Pencil Noir",
            "available": True,
            "quota_status": "NOT_REQUIRED",
            "last_error_category": None,
            "continuity_mode": "Deterministic Visual Bible",
            "status_message": "Hand-drawn offline sketch engine active (100% deterministic SVG).",
            "supports_image_conditioning": False,
            "fallback_enabled": False,
        }

    def get_status(self) -> Dict[str, Any]:
        caps = self.get_capabilities()
        caps["storyboard_image_provider"] = "hand_drawn_storyboard"
        caps["mode"] = "local"
        caps["status"] = ProviderState.AVAILABLE.value
        caps["model"] = "deterministic_sketch_v1"
        caps["fallback_reason"] = None
        return caps

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        """Render panel as an authentic hand-drawn storyboard SVG."""
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        w, h = 960.0, 540.0
        seed_base = f"{panel.project_id}_{panel.panel_id or panel.id}"
        seed_v = f"{seed_base}_v{version}"

        palette = STYLE_PALETTES.get(self.style, STYLE_PALETTES[SketchStyle.PENCIL_NOIR])

        # 1. Resolve Location Identity
        loc_id = panel.location_id or "loc_default"
        loc_ref = bible.locations.get(loc_id) if bible else None
        loc_ident = self.env_renderer.get_or_create_identity(
            location_id=loc_id,
            name=panel.location_name or "Interior",
            ref=loc_ref,
        )

        # 2. Stage Scene (Actors, Props, Camera)
        staged: StagedScene = SceneStager.stage_panel(panel, version=version, seed=seed_base)

        # 3. Render Layers
        # A. Background Gradients & Vignette
        defs_svg = f"""
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette.bg_gradient_start}"/>
      <stop offset="100%" stop-color="{palette.bg_gradient_end}"/>
    </linearGradient>
    <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
      <stop offset="50%" stop-color="#000000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.6"/>
    </radialGradient>
  </defs>"""

        bg_rect = f'<rect width="{w:.1f}" height="{h:.1f}" fill="url(#bgGrad)"/>'

        # B. Architectural Environment
        env_svg = self.env_renderer.render_environment(
            identity=loc_ident,
            width=w,
            height=h,
            seed=f"{seed_base}_env",
            stroke_color=palette.stroke_color,
        )

        # C. Lighting & Chiaroscuro
        lighting_svg = LightingSketchRenderer.render_lighting(
            width=w,
            height=h,
            lighting_description=panel.lighting or "",
            seed=f"{seed_v}_lighting",
            style=self.style,
        )

        # D. Actors & Props (Sorted by Z-index)
        rendered_elements: List[Tuple[int, str]] = []
        actors_rendered_names: List[str] = []
        props_rendered_names: List[str] = []

        # Render Props
        for p in staged.props:
            prop_ref = bible.objects.get(p.prop_id) if bible else None
            prop_ident = self.prop_renderer.get_or_create_identity(
                object_id=p.prop_id,
                name=p.name,
                ref=prop_ref,
            )
            p_svg = self.prop_renderer.render_prop(
                identity=prop_ident,
                cx=p.cx,
                cy=p.cy,
                scale=p.scale,
                rotation_deg=p.rotation_deg,
                seed=f"{seed_base}_prop_{p.prop_id}",
                stroke_color=palette.stroke_color,
            )
            rendered_elements.append((p.z_index, p_svg))
            props_rendered_names.append(p.name)

        # Render Actors
        for a in staged.actors:
            char_ref = bible.characters.get(a.actor_id) if bible else None
            char_ident = self.char_renderer.get_or_create_identity(
                char_id=a.actor_id,
                name=a.name,
                ref=char_ref,
            )
            char_svg, _ = self.char_renderer.render_character(
                identity=char_ident,
                x=a.x,
                y=a.y,
                height=a.height,
                pose_type=a.pose,
                expression_type=a.expression,
                facing_direction=a.facing_direction,
                seed=f"{seed_v}_char_{a.actor_id}",
                crop_to_waist=a.crop_to_waist,
                crop_to_bust=a.crop_to_bust,
                stroke_color=palette.stroke_color,
            )
            rendered_elements.append((a.z_index, char_svg))
            actors_rendered_names.append(a.name)

        rendered_elements.sort(key=lambda item: item[0])
        actors_and_props_svg = "\n  ".join(elem for _, elem in rendered_elements)

        # E. Motion Language & Camera Annotations
        motion_svg = MotionSketchRenderer.render_motion(
            panel=panel,
            staged=staged,
            seed=f"{seed_v}_motion",
        )

        # F. Traditional Storyboard Framing & Film Header Overlay
        shot_tag = panel.shot_type.value.replace("_", " ").upper()
        angle_tag = panel.camera_angle.value.replace("_", " ").upper()
        loc_tag = html.escape((panel.location_name or "SCENE").upper())
        shot_num_str = f"SHOT {panel.shot_number:02d} • SCENE {panel.scene_number:02d}"

        # Sketched outer frame border
        frame_border = SketchPolygon.render(
            points=[(8, 8), (w - 8, 8), (w - 8, h - 8), (8, h - 8)],
            seed=f"{seed_base}_border",
            stroke_color="#475569",
            stroke_width=2.0,
            stroke_opacity=0.7,
        )

        # Technical production header bar
        header_bar = f"""
  <g opacity="0.9">
    <rect x="14" y="14" width="260" height="24" rx="3" fill="#090d16" fill-opacity="0.85" stroke="#334155" stroke-width="1"/>
    <text x="24" y="30" fill="#cbd5e1" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1">
      {shot_num_str}
    </text>
    <rect x="{w - 234:.1f}" y="14" width="220" height="24" rx="3" fill="#090d16" fill-opacity="0.85" stroke="#334155" stroke-width="1"/>
    <text x="{w - 224:.1f}" y="30" fill="#f59e0b" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1">
      {shot_tag} | {angle_tag}
    </text>
  </g>"""

        # Assemble full SVG
        full_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(w)} {int(h)}" width="100%" height="100%">
  <!-- D3 Story Lab: Hand-Drawn Storyboard Engine (Offline Deterministic SVG) -->
  {defs_svg}
  {bg_rect}
  
  <!-- Architectural Environment -->
  <g id="environment_layer">
  {env_svg}
  </g>

  <!-- Volumetric Lighting & Shading -->
  <g id="lighting_layer">
  {lighting_svg}
  </g>

  <!-- Actors & Key Props -->
  <g id="subjects_layer">
  {actors_and_props_svg}
  </g>

  <!-- Storyboard Motion Annotations -->
  <g id="motion_layer">
  {motion_svg}
  </g>

  <!-- Vignette -->
  <rect width="{w:.1f}" height="{h:.1f}" fill="url(#vignette)"/>

  <!-- Storyboard Production Framing -->
  {frame_border}
  {header_bar}
</svg>"""

        # Save to Asset Store if project_id is available
        image_url = ""
        project_id = panel.project_id or "default"
        try:
            filename = f"{panel.panel_id or panel.id}_v{version}.svg"
            image_url = self.asset_store.save_asset(
                project_id=project_id,
                category="panels",
                filename=filename,
                content=full_svg,
            )
        except Exception as err:
            logger.warning(f"Could not persist hand-drawn panel asset to disk: {err}")

        metadata = {
            "label": "HAND-DRAWN STORYBOARD",
            "renderer": "HandDrawnStoryboardProvider",
            "style": "Pencil Noir",
            "continuity": "Deterministic Visual Bible",
            "seed": seed_v,
            "actors_rendered": actors_rendered_names,
            "props_rendered": props_rendered_names,
            "environment": loc_ident.env_type.value,
            "version": version,
            "byte_size": len(full_svg.encode("utf-8")),
            "no_cloud_api": True,
        }

        return StoryboardImageResult(
            panel_id=panel.panel_id or panel.id,
            version=version,
            image_url=image_url,
            svg_content=full_svg,
            provider="hand_drawn_storyboard",
            mode="hand_drawn",
            compiled_prompt=compiled_prompt,
            negative_prompt=negative_prompt,
            status=StoryboardImageStatus.READY,
            fallback_reason=None,
            provider_status=ProviderState.AVAILABLE.value,
            continuity_mode="Deterministic Visual Bible",
            mime_type="image/svg+xml",
            render_metadata=metadata,
        )
