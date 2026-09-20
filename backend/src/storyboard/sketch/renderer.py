"""HandDrawnStoryboardProvider - 100% offline deterministic sketch storyboard engine.

Generates production film storyboard drawings with hand-drawn pencil/ink aesthetics,
distinct character identities, recognizable props, and architectural environments.
"""

from __future__ import annotations
import html
import logging
from typing import Dict, Any, Optional, List, Tuple

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
        style: SketchStyle = SketchStyle.GRAPHITE_PRODUCTION_BOARD,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.char_renderer = CharacterSketchRenderer()
        self.prop_renderer = PropSketchRenderer()
        self.env_renderer = EnvironmentSketchRenderer()
        self.style = style

    def get_capabilities(self) -> Dict[str, Any]:
        palette = STYLE_PALETTES.get(self.style, STYLE_PALETTES[SketchStyle.GRAPHITE_PRODUCTION_BOARD])
        return {
            "provider": "hand_drawn_storyboard",
            "selected_model": "deterministic_sketch_v2_cinematic",
            "style": palette.name,
            "available": True,
            "quota_status": "NOT_REQUIRED",
            "last_error_category": None,
            "continuity_mode": "Deterministic Visual Bible",
            "status_message": f"Hand-drawn offline sketch engine active ({palette.name}, 100% deterministic SVG).",
            "supports_image_conditioning": False,
            "fallback_enabled": False,
        }

    def get_status(self) -> Dict[str, Any]:
        caps = self.get_capabilities()
        caps["storyboard_image_provider"] = "hand_drawn_storyboard"
        caps["mode"] = "local"
        caps["status"] = ProviderState.AVAILABLE.value
        caps["model"] = "deterministic_sketch_v2_cinematic"
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

        palette = STYLE_PALETTES.get(self.style, STYLE_PALETTES[SketchStyle.CINEMATIC_INK_WASH])

        # 1. Resolve Location Identity
        loc_id = panel.location_id or "loc_default"
        loc_ref = bible.locations.get(loc_id) if bible else None
        loc_ident = self.env_renderer.get_or_create_identity(
            location_id=loc_id,
            name=panel.location_name or "Interior",
            ref=loc_ref,
        )

        # 2. Stage Scene (Actors, Props, Camera, LOD, Dutch Angle)
        staged: StagedScene = SceneStager.stage_panel(panel, version=version, seed=seed_base)

        # 3. Render Layers
        # A. Background Gradients & Vignette with Graphite Edge Filters & Paper Grain
        defs_svg = f"""
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette.bg_gradient_start}"/>
      <stop offset="100%" stop-color="{palette.bg_gradient_end}"/>
    </linearGradient>
    <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
      <stop offset="50%" stop-color="#000000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.65"/>
    </radialGradient>

    <!-- Restrained Graphite Edge Displacement (Section 18) -->
    <filter id="graphite_bg" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="0.7" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="graphite_subject" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.4" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="graphite_fg" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.2" xChannelSelector="R" yChannelSelector="G"/>
    </filter>

    <!-- Lightweight Paper Grain Filter (Section 21) -->
    <filter id="paper_grain" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" result="grain"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.9  0 0 0 0 0.9  0 0 0 0 0.9  0 0 0 0.04 0"/>
    </filter>

    <!-- Procedural Graphite Cross-Hatching Patterns (Section 20) -->
    <pattern id="hatch_light" width="12" height="12" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="12" stroke="#94a3b8" stroke-width="0.8" opacity="0.4"/>
    </pattern>
    <pattern id="hatch_mid" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="8" stroke="#64748b" stroke-width="1.0" opacity="0.6"/>
    </pattern>
    <pattern id="hatch_dark" width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="6" stroke="#334155" stroke-width="1.2" opacity="0.75"/>
      <line x1="0" y1="0" x2="6" y2="0" stroke="#334155" stroke-width="1.2" opacity="0.75"/>
    </pattern>

    <!-- Cinematic Depth of Field Filters (Section 22) -->
    <filter id="blur_foreground" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="1.8"/>
    </filter>
    <filter id="blur_background" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="0.7"/>
    </filter>
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
                is_insert=(staged.shot_type == ShotType.INSERT),
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

        # F. Traditional Storyboard Framing & Letterboxed Production Header
        shot_tag = panel.shot_type.value.replace("_", " ").upper()
        angle_tag = panel.camera_angle.value.replace("_", " ").upper()
        shot_num = panel.shot_number or panel.panel_number or 1
        shot_num_str = f"SHOT {shot_num:02d}"

        # Optional lens / movement tags
        lens_tag = f" • {panel.lens_feel}" if panel.lens_feel else ""
        if staged.is_over_shoulder:
            shot_tag = f"{shot_tag} / OTS"
        if staged.dutch_rotation_deg != 0.0:
            angle_tag = f"DUTCH {staged.dutch_rotation_deg:+.0f}°"

        # Sketched outer frame border
        frame_border = SketchPolygon.render(
            points=[(8, 8), (w - 8, 8), (w - 8, h - 8), (8, h - 8)],
            seed=f"{seed_base}_border",
            stroke_color="#475569",
            stroke_width=2.0,
            stroke_opacity=0.7,
        )

        # Minimal sleek header bar (artwork-first)
        header_bar = f"""
  <g id="production_header" opacity="0.9">
    <rect x="14" y="12" width="160" height="22" rx="3" fill="#090d16" fill-opacity="0.85" stroke="#334155" stroke-width="1"/>
    <text x="22" y="27" fill="#cbd5e1" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1">
      {shot_num_str} • SCENE {panel.scene_number or 1:02d}
    </text>
    <rect x="{w - 220:.1f}" y="12" width="206" height="22" rx="3" fill="#090d16" fill-opacity="0.85" stroke="#334155" stroke-width="1"/>
    <text x="{w - 212:.1f}" y="27" fill="#f59e0b" font-family="monospace" font-size="10" font-weight="700" letter-spacing="1">
      {shot_tag} | {angle_tag}
    </text>
  </g>"""

        # Dutch angle camera rotation wrapper
        camera_transform_open = ""
        camera_transform_close = ""
        if abs(staged.dutch_rotation_deg) > 0.01:
            camera_transform_open = f'<g id="dutch_camera_tilt" transform="rotate({staged.dutch_rotation_deg:.1f} {w/2:.1f} {h/2:.1f})">'
            camera_transform_close = "</g>"

        # Sound effect typography overlay (Section 30)
        sfx_label = panel.sfx_label or ""
        sfx_typography = ""
        if sfx_label:
            sfx_clean = sfx_label.upper()
            sfx_typography = f"""
  <!-- Sound Effect Typography (Section 30) -->
  <g id="sfx_typography" transform="rotate(-6 480 270)" pointer-events="none">
    <text x="482" y="272" text-anchor="middle" fill="#000000" font-family="impact, sans-serif" font-size="34" font-weight="900" letter-spacing="3" opacity="0.65">{html.escape(sfx_clean)}</text>
    <text x="480" y="270" text-anchor="middle" fill="#ef4444" font-family="impact, sans-serif" font-size="34" font-weight="900" letter-spacing="3">{html.escape(sfx_clean)}</text>
  </g>"""

        # Assemble full SVG
        full_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(w)} {int(h)}" width="100%" height="100%">
  <!-- D3 Story Lab: Hand-Drawn Storyboard Engine (Offline Deterministic SVG) -->
  {defs_svg}
  {bg_rect}

  {camera_transform_open}
  <!-- Architectural Environment with Graphite Contours -->
  <g id="environment_layer" filter="url(#graphite_bg)">
  {env_svg}
  </g>

  <!-- Volumetric Lighting & Shading -->
  <g id="lighting_layer">
  {lighting_svg}
  </g>

  <!-- Actors & Key Props with Graphite Subject Contours -->
  <g id="subjects_layer" filter="url(#graphite_subject)">
  {actors_and_props_svg}
  </g>

  <!-- Storyboard Motion Annotations -->
  <g id="motion_layer">
  {motion_svg}
  </g>
  {camera_transform_close}

  {sfx_typography}

  <!-- Subtle Paper Grain Texture (Section 21) -->
  <rect width="{w:.1f}" height="{h:.1f}" filter="url(#paper_grain)" opacity="0.22" pointer-events="none"/>

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
            "style": palette.name,
            "continuity": "Deterministic Visual Bible",
            "seed": seed_v,
            "actors_rendered": actors_rendered_names,
            "props_rendered": props_rendered_names,
            "environment": loc_ident.env_type.value,
            "version": version,
            "byte_size": len(full_svg.encode("utf-8")),
            "no_cloud_api": True,
            "dutch_angle_deg": staged.dutch_rotation_deg,
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

    def render_from_composition_plan(
        self,
        shot: Any,
        continuity: Optional[Any] = None,
        prompt: str = "",
        project_id: str = "default",
        version: int = 1,
    ) -> str:
        """Render an individual ShotPlan using its CompositionPlan and ContinuityPack into deterministic previs SVG."""
        w, h = 960.0, 540.0
        shot_id = getattr(shot, "shot_id", "shot_default")
        shot_type = getattr(shot.shot_type, "value", str(shot.shot_type)) if hasattr(shot, "shot_type") else "MEDIUM"
        camera_angle = getattr(shot.camera_angle, "value", str(shot.camera_angle)) if hasattr(shot, "camera_angle") else "EYE_LEVEL"
        lens_feel = getattr(shot, "lens_feel", "normal")
        emotion = getattr(shot, "emotion", "neutral")
        comp = getattr(shot, "composition_plan", None)

        loc_landmark = "INTERIOR"
        loc_arch = "unspecified architecture"
        if continuity and hasattr(continuity, "location_ref") and continuity.location_ref:
            loc_landmark = getattr(continuity.location_ref, "landmarks", loc_landmark)
            loc_arch = getattr(continuity.location_ref, "architecture", loc_arch)

        # 1. Header with gradient and paper grain
        svg_header = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <filter id="paper_grain" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" result="grain"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.9  0 0 0 0 0.9  0 0 0 0 0.9  0 0 0 0.04 0"/>
    </filter>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bgGrad)"/>
"""
        # 2. Architectural environment framing
        env_lines = f"""  <g id="environment" stroke="#475569" stroke-width="1.2" fill="none">
    <line x1="0" y1="{h*0.75}" x2="{w}" y2="{h*0.75}" stroke="#64748b" stroke-width="2"/>
    <rect x="{w*0.1}" y="{h*0.2}" width="{w*0.25}" height="{h*0.55}" stroke-dasharray="4 2"/>
    <rect x="{w*0.65}" y="{h*0.15}" width="{w*0.25}" height="{h*0.6}" stroke-dasharray="4 2"/>
    <text x="24" y="36" fill="#94a3b8" font-family="monospace" font-size="12" letter-spacing="1">LOCATION: {loc_landmark.upper()}</text>
    <text x="24" y="54" fill="#64748b" font-family="monospace" font-size="10">FRAMING: {shot_type} | {camera_angle} | {lens_feel.upper()}</text>
  </g>
"""
        # 3. Actors staged according to CompositionPlan
        actor_elements: List[str] = []
        if comp and hasattr(comp, "subject_positions"):
            for cid, pos in comp.subject_positions.items():
                x_pct, y_pct, scale = pos
                cx = x_pct * w
                cy = y_pct * h
                actor_name = cid.upper()
                actor_elements.append(
                    f"""  <g id="actor_{cid}" transform="translate({cx:.1f},{cy:.1f}) scale({scale:.2f})">
    <ellipse cx="0" cy="-60" rx="20" ry="26" fill="#1e293b" stroke="#94a3b8" stroke-width="1.8"/>
    <path d="M -24,-30 Q 0,-40 24,-30 L 30,50 L -30,50 Z" fill="#0f172a" stroke="#94a3b8" stroke-width="1.8"/>
    <text x="0" y="68" fill="#e2e8f0" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{actor_name}</text>
  </g>"""
                )

        # 4. Props staged
        prop_elements: List[str] = []
        if continuity and hasattr(continuity, "prop_refs"):
            for pref in continuity.prop_refs:
                prop_elements.append(
                    f"""  <g id="prop_{pref.prop_id}" transform="translate({w*0.5:.1f},{h*0.7:.1f})">
    <rect x="-30" y="-20" width="60" height="40" rx="3" fill="#334155" stroke="#cbd5e1" stroke-width="1.6"/>
    <text x="0" y="5" fill="#f8fafc" font-family="monospace" font-size="9" text-anchor="middle">{pref.prop_id[:12]}</text>
  </g>"""
                )

        # 5. Production board lower thirds
        footer = f"""  <g id="production_metadata" transform="translate(0, {h - 40})">
    <rect width="{w}" height="40" fill="#020617" opacity="0.85"/>
    <text x="24" y="24" fill="#38bdf8" font-family="monospace" font-size="11" font-weight="bold">SHOT {shot_id.upper()}</text>
    <text x="180" y="24" fill="#94a3b8" font-family="monospace" font-size="10">EMOTION: {emotion[:55]}</text>
    <text x="{w - 24}" y="24" fill="#64748b" font-family="monospace" font-size="10" text-anchor="end">DETERMINISTIC PREVIS SVG</text>
  </g>
</svg>"""

        return svg_header + env_lines + ("\n".join(actor_elements) + "\n" if actor_elements else "") + ("\n".join(prop_elements) + "\n" if prop_elements else "") + footer
