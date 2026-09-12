"""Visual identity and continuity models for actors, objects, and locations."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActorVisualProfile(BaseModel):
    """Visual identity profile for an actor to ensure continuity across panels."""
    model_config = ConfigDict(frozen=True)

    character_id: str
    name: str
    age: str = "Mid 30s"
    face_traits: str = "Sharp angular jawline, intense observant gaze, faint scar above right eye"
    hairstyle: str = "Short textured dark hair, slightly disheveled"
    build: str = "Lean athletic build, upright guarded posture"
    clothing: str = "Charcoal tailored trench coat over a dark collared shirt and pressed trousers"
    signature_items: List[str] = Field(default_factory=lambda: ["Silver mechanical watch", "Leather notebook"])
    emotional_style: str = "Controlled tension, calculating and watchful"

    def summary_prompt(self) -> str:
        """Condensed visual description for image generation prompts."""
        items_str = ", ".join(self.signature_items) if self.signature_items else "none"
        return (
            f"{self.name} ({self.age}, {self.build}, {self.face_traits}, {self.hairstyle}, "
            f"wearing {self.clothing}, signature items: {items_str})"
        )


class ObjectVisualProfile(BaseModel):
    """Visual profile for a key prop to maintain object consistency across panels."""
    model_config = ConfigDict(frozen=True)

    object_id: str
    name: str
    material: str = "Weathered calfskin leather with tarnished brass latches"
    size: str = "Folio size, approximately 12x9 inches, 2 inches thick"
    color: str = "Deep oxblood brown"
    condition: str = "Aged, scuffed corners, slight water stain on lower spine"
    unique_markers: str = "Embossed circular crest on front cover, red wax seal remnant"

    def summary_prompt(self) -> str:
        """Condensed visual description for image generation prompts."""
        return (
            f"{self.name} ({self.color} {self.material}, {self.size}, "
            f"condition: {self.condition}, distinct marker: {self.unique_markers})"
        )


class LocationVisualProfile(BaseModel):
    """Visual profile for a location environment to maintain spatial continuity."""
    model_config = ConfigDict(frozen=True)

    location_id: str
    name: str
    environment_type: str = "High-rise executive penthouse interior"
    lighting: str = "Moody chiaroscuro, cold ambient rain reflections through glass, warm low desk lamp"
    layout: str = "Spacious open room, panoramic floor-to-ceiling glass on one wall, heavy desk centered"
    palette: str = "Charcoal slate, cold steel blue, dark walnut wood, amber highlights"
    mood: str = "Tense, claustrophobic elegance, rain-streaked noir"

    def summary_prompt(self) -> str:
        """Condensed visual description for image generation prompts."""
        return (
            f"{self.name} ({self.environment_type}, palette: {self.palette}, "
            f"lighting: {self.lighting}, layout: {self.layout}, mood: {self.mood})"
        )
