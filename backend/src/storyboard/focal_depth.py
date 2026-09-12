"""Focal depth and rack focus system for cinematic storyboard depth of field."""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class FocalDepthPlane(str, Enum):
    """The targeted depth plane in razor focus."""
    FOREGROUND = "foreground"      # Foreground prop or OTS shoulder
    FOCAL_PLANE = "focal_plane"    # Primary subject (character face/action)
    BACKGROUND = "background"      # Distant architecture or doorway


class FocalDepthConfig(BaseModel):
    """Depth blur and line weight parameters for SVG layer rendering."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    active_plane: FocalDepthPlane = FocalDepthPlane.FOCAL_PLANE
    foreground_blur_px: float = 1.8
    focal_plane_blur_px: float = 0.0
    background_blur_px: float = 0.7
    is_rack_focus: bool = False
    rack_focus_target: Optional[str] = None


class FocalDepthSystem:
    """Computes depth of field, Gaussian blur filters, and rack focus transitions."""

    @staticmethod
    def get_layer_filter_id(plane: FocalDepthPlane, config: FocalDepthConfig) -> Optional[str]:
        """Return SVG filter ID to apply to a specific visual layer."""
        if config.active_plane == FocalDepthPlane.FOCAL_PLANE:
            if plane == FocalDepthPlane.FOREGROUND:
                return "blur_foreground"
            elif plane == FocalDepthPlane.BACKGROUND:
                return "blur_background"
            return None  # Subject is razor sharp

        elif config.active_plane == FocalDepthPlane.FOREGROUND:
            # Macro shot on prop / clue: foreground is sharp, subject and background blurred
            if plane == FocalDepthPlane.FOCAL_PLANE:
                return "blur_foreground"  # Subject blurred
            elif plane == FocalDepthPlane.BACKGROUND:
                return "blur_background"
            return None  # Foreground is sharp

        elif config.active_plane == FocalDepthPlane.BACKGROUND:
            # Looking past actor to background doorway
            if plane == FocalDepthPlane.FOREGROUND or plane == FocalDepthPlane.FOCAL_PLANE:
                return "blur_foreground"
            return None

        return None

    @staticmethod
    def render_svg_defs(config: FocalDepthConfig) -> str:
        """Render SVG filter definitions for depth of field."""
        return f"""
    <!-- Cinematic Depth of Field Filters -->
    <filter id="blur_foreground" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="{config.foreground_blur_px:.1f}"/>
    </filter>
    <filter id="blur_background" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="{config.background_blur_px:.1f}"/>
    </filter>"""
