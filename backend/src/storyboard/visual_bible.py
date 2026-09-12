"""Visual Bible and Continuity Reference models for Storyboard Generation.

Maintains canonical character turnarounds, key object specifications, location palettes,
and artistic style profiles to guarantee visual consistency across comic panels.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from src.domain.world import WorldState


class StoryboardStyleProfile(BaseModel):
    """Artistic styling guidelines for comic/graphic novel rendering."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = "noir_graphic_novel"
    name: str = "Cinematic Noir Graphic Novel"
    medium: str = "Inked comic graphic novel illustration"
    linework: str = "Heavy black brushwork, sharp angular contour inking, expressive crosshatching"
    lighting_style: str = "Stark chiaroscuro, deep shadow pools, dramatic rim lighting, edge highlights"
    color_palette: str = "Monochrome black and white with deep charcoal slate, muted cold cyan undertones, and warm amber practical accents"
    composition_rules: str = "Cinematic widescreen framing, dynamic perspective diagonals, high-tension camera tilts"
    artist_influences: List[str] = Field(
        default_factory=lambda: [
            "Frank Miller Sin City high contrast ink",
            "Sean Phillips noir comic chiaroscuro",
            "David Mazzucchelli Batman Year One atmosphere",
            "Alberto Breccia dramatic ink silhouettes",
        ]
    )
    negative_constraints: str = (
        "no text inside image, no watermarks, no speech bubbles rendered in art, "
        "no 3D CGI plastic skin, no photorealistic glossy skin, no cheerful colors, "
        "no distorted fingers, no oversaturated backgrounds"
    )

    def prompt_prefix(self) -> str:
        influences_str = ", ".join(self.artist_influences[:2])
        return (
            f"{self.medium}, {influences_str}. {self.linework}. "
            f"{self.lighting_style}. Color palette: {self.color_palette}."
        )


class CharacterVisualReference(BaseModel):
    """Canonical visual turnaround reference for an actor."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    character_id: str
    name: str
    role: str = ""
    age: str = "Mid 30s"
    build: str = "Lean athletic build, upright guarded posture"
    face_features: str = "Sharp angular jawline, intense observant gaze, faint scar above right eye"
    hair: str = "Short textured dark hair, slightly disheveled"
    clothing: str = "Charcoal tailored trench coat over a dark collared shirt and pressed trousers"
    signature_props: List[str] = Field(default_factory=list)
    color_accents: str = "Cold charcoal, dark graphite, brushed silver watch"
    expression_tendency: str = "Guarded, calculating, watchful eyes"
    reference_image_url: Optional[str] = None

    def prompt_snippet(self) -> str:
        props = f", holding/wearing: {', '.join(self.signature_props)}" if self.signature_props else ""
        return (
            f"{self.name} ({self.role}, {self.age}, {self.build}, {self.face_features}, "
            f"{self.hair}, wearing {self.clothing}{props})"
        )


class ObjectVisualReference(BaseModel):
    """Canonical visual reference for a significant prop."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    object_id: str
    name: str
    form_factor: str = "Rectangular folio dossier"
    materials: str = "Weathered calfskin leather with tarnished brass latches"
    colors: str = "Deep oxblood brown and dark tarnished brass"
    unique_markings: str = "Embossed circular crest on front cover, faded red wax seal remnant"
    condition: str = "Aged, scuffed corners, slight water stain on lower spine"
    reference_image_url: Optional[str] = None

    def prompt_snippet(self) -> str:
        return (
            f"{self.name} ({self.form_factor}, {self.materials}, {self.colors}, "
            f"markings: {self.unique_markings}, condition: {self.condition})"
        )


class LocationVisualReference(BaseModel):
    """Canonical visual reference for a narrative environment."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    location_id: str
    name: str
    environment_type: str = "High-rise executive penthouse interior"
    architecture: str = "Brutalist modernism with tall floor-to-ceiling windows and geometric concrete pillars"
    lighting_setup: str = "Moody chiaroscuro, cold ambient city rain reflections through glass, warm low desk lamp"
    color_palette: str = "Charcoal slate, cold steel blue, dark walnut wood, amber highlights"
    key_landmarks: List[str] = Field(
        default_factory=lambda: ["Heavy walnut executive desk", "Floor-to-ceiling glass window", "Angular steel safe"]
    )
    mood: str = "Tense, claustrophobic elegance, rain-streaked noir"
    reference_image_url: Optional[str] = None

    def prompt_snippet(self) -> str:
        landmarks = f", landmarks: {', '.join(self.key_landmarks)}" if self.key_landmarks else ""
        return (
            f"{self.name} ({self.environment_type}, architecture: {self.architecture}, "
            f"palette: {self.color_palette}, lighting: {self.lighting_setup}{landmarks})"
        )


class VisualBible(BaseModel):
    """Complete visual reference bible for a story project."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    style_profile: StoryboardStyleProfile = Field(default_factory=StoryboardStyleProfile)
    characters: Dict[str, CharacterVisualReference] = Field(default_factory=dict)
    objects: Dict[str, ObjectVisualReference] = Field(default_factory=dict)
    locations: Dict[str, LocationVisualReference] = Field(default_factory=dict)

    @classmethod
    def from_world(
        cls,
        world: WorldState,
        style: Optional[StoryboardStyleProfile] = None,
    ) -> VisualBible:
        """Derive a canonical visual bible from a WorldState instance."""
        style_profile = style or StoryboardStyleProfile()
        char_refs: Dict[str, CharacterVisualReference] = {}
        obj_refs: Dict[str, ObjectVisualReference] = {}
        loc_refs: Dict[str, LocationVisualReference] = {}

        # 1. Characters
        for cid, char in world.characters.items():
            vp = getattr(char, "visual_profile", None)
            if vp:
                char_refs[cid] = CharacterVisualReference(
                    character_id=cid,
                    name=char.name,
                    role=char.role or "Protagonist",
                    age=getattr(vp, "age", "Mid 30s"),
                    build=getattr(vp, "build", "Lean athletic build, upright guarded posture"),
                    face_features=getattr(vp, "face_traits", "Sharp angular features"),
                    hair=getattr(vp, "hairstyle", "Dark textured hair"),
                    clothing=getattr(vp, "clothing", "Tailored dark trench coat and collared shirt"),
                    signature_props=list(getattr(vp, "signature_items", [])),
                    expression_tendency=getattr(vp, "emotional_style", "Guarded, calculating"),
                )
            else:
                char_refs[cid] = CharacterVisualReference(
                    character_id=cid,
                    name=char.name,
                    role=char.role or "Actor",
                    face_features=f"Distinctive silhouette, expressive eyes, {char.role.lower() if char.role else 'operative'}",
                    clothing="Dark tailored noir attire, sharp shadows",
                    signature_props=[],
                )

        # 2. Objects
        for oid, obj in world.objects.items():
            vp = getattr(obj, "visual_profile", None)
            if vp:
                obj_refs[oid] = ObjectVisualReference(
                    object_id=oid,
                    name=obj.name,
                    form_factor=getattr(vp, "size", "Handheld item"),
                    materials=getattr(vp, "material", "Dark polished metal or leather"),
                    colors=getattr(vp, "color", "Deep charcoal and brass"),
                    unique_markings=getattr(vp, "unique_markers", "Serial engravings"),
                    condition=getattr(vp, "condition", "Weathered"),
                )
            else:
                obj_refs[oid] = ObjectVisualReference(
                    object_id=oid,
                    name=obj.name,
                    form_factor="Key narrative prop",
                    materials="High-contrast materials, weathered texture",
                    colors="Noir tones, reflective brass or dark leather",
                    unique_markings=obj.description or "Identifiable item",
                    condition="Well-kept",
                )

        # 3. Locations
        for lid, loc in world.locations.items():
            vp = getattr(loc, "visual_profile", None)
            if vp:
                loc_refs[lid] = LocationVisualReference(
                    location_id=lid,
                    name=loc.name,
                    environment_type=getattr(vp, "environment_type", "Architectural interior"),
                    architecture=getattr(vp, "layout", "High-contrast architectural layout"),
                    lighting_setup=getattr(vp, "lighting", "Moody low-key chiaroscuro with deep shadows"),
                    color_palette=getattr(vp, "palette", "Cold slate, muted blue, warm amber highlights"),
                    key_landmarks=[loc.name],
                    mood=getattr(vp, "mood", "Tense, suspenseful"),
                )
            else:
                loc_refs[lid] = LocationVisualReference(
                    location_id=lid,
                    name=loc.name,
                    environment_type="Noir atmospheric setting",
                    architecture=loc.description or "Interior space with dramatic shadow play",
                    lighting_setup="Low-key cinematic chiaroscuro, sharp blinds shadows",
                    color_palette="Charcoal, deep black, cold cyan reflections",
                    key_landmarks=[loc.name],
                    mood="Ominous and tense",
                )

        return cls(
            style_profile=style_profile,
            characters=char_refs,
            objects=obj_refs,
            locations=loc_refs,
        )
