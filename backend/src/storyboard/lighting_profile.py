"""Lighting profiles for cinematic storyboard rendering.

Defines 9 professional lighting configurations:
- NOIR_HARD: Stark chiaroscuro, heavy VALUE_4 black shadow masses, thin rim highlights, low fill
- MOONLIT_INDUSTRIAL: Cold cyan haze, high contrast, specular rain/wet reflections
- INTERROGATION: Overhead cone spotlight, high contrast facial plunge, black background
- PRACTICAL_WARM: Amber side lantern/desk lamp illumination, soft midtone roll-off
- EMERGENCY_RED: High alarm crimson saturation, stark silhouette rimming
- SILHOUETTE: Full backlight cutout, zero frontal fill, razor sharp black shapes
- BACKLIT: Halo rim contouring with deep shadow core
- LOW_KEY: Balanced cinematic noir standard, dark room atmosphere
- HIGH_KEY: Wide bright environmental diffusion with crisp pencil contours
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class LightingProfileType(str, Enum):
    """Presets for visual lighting and shadow treatment."""
    NOIR_HARD = "NOIR_HARD"
    MOONLIT_INDUSTRIAL = "MOONLIT_INDUSTRIAL"
    INTERROGATION = "INTERROGATION"
    PRACTICAL_WARM = "PRACTICAL_WARM"
    EMERGENCY_RED = "EMERGENCY_RED"
    SILHOUETTE = "SILHOUETTE"
    BACKLIT = "BACKLIT"
    LOW_KEY = "LOW_KEY"
    HIGH_KEY = "HIGH_KEY"


class LightingProfile(BaseModel):
    """Detailed volumetric lighting definition for storyboard SVG rendering."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: LightingProfileType
    name: str
    key_direction: str  # "top_left", "top_right", "direct_overhead", "side_left", "side_right", "rear_center"
    key_angle_deg: float
    fill_amount: float = Field(ge=0.0, le=1.0)
    rim_light: float = Field(ge=0.0, le=1.0)
    shadow_value: str  # Hex color for shadow mass (#090d16, #1e293b, etc.)
    shadow_opacity: float = Field(ge=0.0, le=1.0)
    background_suppression: float = Field(ge=0.0, le=1.0)
    accent_colors: List[str] = Field(default_factory=list)
    vignette_opacity: float = 0.65
    description: str = ""


LIGHTING_PROFILES: Dict[LightingProfileType, LightingProfile] = {
    LightingProfileType.NOIR_HARD: LightingProfile(
        id=LightingProfileType.NOIR_HARD,
        name="Noir Hard Chiaroscuro",
        key_direction="top_left",
        key_angle_deg=45.0,
        fill_amount=0.10,
        rim_light=0.85,
        shadow_value="#090d16",
        shadow_opacity=0.88,
        background_suppression=0.80,
        accent_colors=["#ffffff", "#cbd5e1"],
        vignette_opacity=0.80,
        description="Heavy black VALUE_4 masses, razor rim cuts, deep theatrical shadow.",
    ),
    LightingProfileType.MOONLIT_INDUSTRIAL: LightingProfile(
        id=LightingProfileType.MOONLIT_INDUSTRIAL,
        name="Moonlit Industrial Cold",
        key_direction="top_right",
        key_angle_deg=60.0,
        fill_amount=0.25,
        rim_light=0.90,
        shadow_value="#0b132b",
        shadow_opacity=0.75,
        background_suppression=0.60,
        accent_colors=["#38bdf8", "#94a3b8"],
        vignette_opacity=0.70,
        description="Cyan-tinted moonbeams cutting through warehouse rafters.",
    ),
    LightingProfileType.INTERROGATION: LightingProfile(
        id=LightingProfileType.INTERROGATION,
        name="Interrogation Cone",
        key_direction="direct_overhead",
        key_angle_deg=90.0,
        fill_amount=0.05,
        rim_light=0.30,
        shadow_value="#030712",
        shadow_opacity=0.92,
        background_suppression=0.95,
        accent_colors=["#fef08a", "#f1f5f9"],
        vignette_opacity=0.85,
        description="Harsh vertical downlight, plunging eyes in deep socket shadows.",
    ),
    LightingProfileType.PRACTICAL_WARM: LightingProfile(
        id=LightingProfileType.PRACTICAL_WARM,
        name="Practical Warm Lamp",
        key_direction="side_right",
        key_angle_deg=25.0,
        fill_amount=0.40,
        rim_light=0.50,
        shadow_value="#18181b",
        shadow_opacity=0.60,
        background_suppression=0.40,
        accent_colors=["#f59e0b", "#d97706"],
        vignette_opacity=0.55,
        description="Warm desk lamp illumination casting soft sepia and amber rim tones.",
    ),
    LightingProfileType.EMERGENCY_RED: LightingProfile(
        id=LightingProfileType.EMERGENCY_RED,
        name="Emergency Red Beacon",
        key_direction="side_left",
        key_angle_deg=30.0,
        fill_amount=0.15,
        rim_light=0.95,
        shadow_value="#1a0505",
        shadow_opacity=0.82,
        background_suppression=0.70,
        accent_colors=["#dc2626", "#ef4444"],
        vignette_opacity=0.75,
        description="Pulsing alarm claxon glow, silhouette edges soaked in crimson.",
    ),
    LightingProfileType.SILHOUETTE: LightingProfile(
        id=LightingProfileType.SILHOUETTE,
        name="Pure Silhouette",
        key_direction="rear_center",
        key_angle_deg=0.0,
        fill_amount=0.0,
        rim_light=1.0,
        shadow_value="#000000",
        shadow_opacity=0.98,
        background_suppression=0.10,
        accent_colors=["#f8fafc"],
        vignette_opacity=0.60,
        description="Full backlight cutout; subject renders as pitch black graphic silhouette.",
    ),
    LightingProfileType.BACKLIT: LightingProfile(
        id=LightingProfileType.BACKLIT,
        name="Backlit Halo Rim",
        key_direction="rear_center",
        key_angle_deg=15.0,
        fill_amount=0.20,
        rim_light=0.90,
        shadow_value="#0f172a",
        shadow_opacity=0.75,
        background_suppression=0.50,
        accent_colors=["#e2e8f0"],
        vignette_opacity=0.65,
        description="Bright rim separating character silhouette from dark room.",
    ),
    LightingProfileType.LOW_KEY: LightingProfile(
        id=LightingProfileType.LOW_KEY,
        name="Low-Key Noir Standard",
        key_direction="top_left",
        key_angle_deg=40.0,
        fill_amount=0.30,
        rim_light=0.70,
        shadow_value="#0f172a",
        shadow_opacity=0.70,
        background_suppression=0.50,
        accent_colors=["#cbd5e1"],
        vignette_opacity=0.60,
        description="Atmospheric film noir default with balanced shadows and readability.",
    ),
    LightingProfileType.HIGH_KEY: LightingProfile(
        id=LightingProfileType.HIGH_KEY,
        name="High-Key Diffuse",
        key_direction="top_left",
        key_angle_deg=35.0,
        fill_amount=0.65,
        rim_light=0.40,
        shadow_value="#334155",
        shadow_opacity=0.35,
        background_suppression=0.15,
        accent_colors=["#ffffff"],
        vignette_opacity=0.35,
        description="Daylight or bright industrial diffusion, soft graphite shadows.",
    ),
}


def resolve_lighting_profile(mood: str, action: str, scene_purpose: str = "") -> LightingProfile:
    """Select the most narratively coherent lighting profile based on dramatic context."""
    text = f"{mood} {action} {scene_purpose}".lower()

    if any(w in text for w in ["alarm", "explosion", "emergency", "fire", "danger", "burst", "catastrophe"]):
        return LIGHTING_PROFILES[LightingProfileType.EMERGENCY_RED]
    if any(w in text for w in ["interrogate", "question", "confess", "truth", "trap"]):
        return LIGHTING_PROFILES[LightingProfileType.INTERROGATION]
    if any(w in text for w in ["silhouette", "doorway", "shadow figure", "unseen", "lurks"]):
        return LIGHTING_PROFILES[LightingProfileType.SILHOUETTE]
    if any(w in text for w in ["moon", "dock", "water", "rain", "midnight", "exterior", "cold"]):
        return LIGHTING_PROFILES[LightingProfileType.MOONLIT_INDUSTRIAL]
    if any(w in text for w in ["desk", "lamp", "office", "warm", "whisper", "study", "intimate"]):
        return LIGHTING_PROFILES[LightingProfileType.PRACTICAL_WARM]
    if any(w in text for w in ["confront", "threat", "gun", "climax", "standoff", "noir"]):
        return LIGHTING_PROFILES[LightingProfileType.NOIR_HARD]
    if any(w in text for w in ["behind", "backlit", "halo"]):
        return LIGHTING_PROFILES[LightingProfileType.BACKLIT]

    return LIGHTING_PROFILES[LightingProfileType.LOW_KEY]
