"""Continuity Packs and Reference Sheet Models for Storyboard Consistency.

Maintains strict physical and visual continuity across storyboard panels for:
- Characters (turnarounds, facial geometry, hair, wardrobe, signature props, reference sheets)
- Locations (architecture, spatial layout, apertures, lighting, landmarks)
- Props (form, dimensions, materials, distinctive markings/damage)
- Sequence Context (cross-panel references, shared seed family)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from src.domain.character import Character
from src.domain.world import Location, WorldObject
from src.storyboard.visual_bible import (
    CharacterVisualReference,
    LocationVisualReference,
    ObjectVisualReference,
)


class CharacterReferenceSheet(BaseModel):
    """Multi-view character reference sheet specification."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    character_name: str
    front_portrait_prompt: str = ""
    three_quarter_prompt: str = ""
    profile_prompt: str = ""
    full_body_neutral_prompt: str = ""
    reference_views: Dict[str, str] = Field(
        default_factory=lambda: {
            "front_portrait": "",
            "three_quarter": "",
            "profile": "",
            "full_body_neutral": "",
        }
    )


class CharacterContinuityPack(BaseModel):
    """Mandatory physical and visual continuity identity for a character."""
    model_config = ConfigDict(extra="ignore")

    character_id: str
    name: str
    age: Optional[str] = "Mid 30s"
    face_shape: str = "angular jawline, strong cheekbones"
    skin_tone: str = "weathered fair"
    hair: str = "dark charcoal"
    hair_style: str = "short textured side-part, slightly disheveled"
    build: str = "lean athletic build, guarded posture"
    height: str = "approx. 6ft (183cm)"
    wardrobe: str = "dark charcoal wool trench coat over dark collared shirt and pressed trousers"
    accessories: List[str] = Field(default_factory=lambda: ["brushed steel wristwatch", "leather holster"])
    signature_props: List[str] = Field(default_factory=list)
    color_palette: List[str] = Field(default_factory=lambda: ["charcoal", "slate gray", "matte black", "muted navy"])
    reference_images: Dict[str, str] = Field(default_factory=dict)
    reference_seed: int = 42
    reference_sheet: Optional[CharacterReferenceSheet] = None

    def generate_reference_sheet(self) -> CharacterReferenceSheet:
        """Construct multi-view prompts for front, 3/4, profile, and full-body."""
        base_desc = (
            f"{self.name}, {self.age}, {self.build}, {self.face_shape}, {self.skin_tone} skin tone, "
            f"{self.hair} {self.hair_style}, wearing {self.wardrobe}"
        )
        sheet = CharacterReferenceSheet(
            character_id=self.character_id,
            character_name=self.name,
            front_portrait_prompt=f"Front portrait close-up: {base_desc}, direct eye contact, neutral cinematic lighting.",
            three_quarter_prompt=f"Three-quarter view portrait: {base_desc}, slight head turn, sharp rim lighting.",
            profile_prompt=f"Profile view headshot: {base_desc}, 90 degree side silhouette, crisp contour definition.",
            full_body_neutral_prompt=f"Full-body neutral turnaround: {base_desc}, eye-level standing pose, neutral production staging.",
        )
        self.reference_sheet = sheet
        return sheet

    def prompt_summary(self) -> str:
        """Dense textual prompt representation guaranteeing stable identity."""
        acc = f", accessories: {', '.join(self.accessories)}" if self.accessories else ""
        props = f", signature props: {', '.join(self.signature_props)}" if self.signature_props else ""
        return (
            f"{self.name} [ID:{self.character_id}]: {self.age}, {self.build}, {self.height}, "
            f"face: {self.face_shape}, skin: {self.skin_tone}, hair: {self.hair} ({self.hair_style}), "
            f"wardrobe: {self.wardrobe}{acc}{props}, palette: {', '.join(self.color_palette)}"
        )

    @classmethod
    def from_character(cls, char: Character, seed: int = 42) -> CharacterContinuityPack:
        """Build character pack from WorldState Character domain object."""
        vp = getattr(char, "visual_profile", None)
        if vp:
            pack = cls(
                character_id=char.id,
                name=char.name,
                age=str(getattr(vp, "age", "Mid 30s")),
                face_shape=getattr(vp, "face_traits", "angular jawline, intense observant gaze"),
                skin_tone=getattr(vp, "skin_tone", "neutral olive"),
                hair=getattr(vp, "hair_color", "dark"),
                hair_style=getattr(vp, "hairstyle", "short textured"),
                build=getattr(vp, "build", "lean athletic build"),
                height=getattr(vp, "height", "approx 5ft 11in"),
                wardrobe=getattr(vp, "clothing", "dark tailored noir attire"),
                accessories=list(getattr(vp, "accessories", ["leather gloves"])),
                signature_props=list(getattr(vp, "signature_items", [])),
                color_palette=list(getattr(vp, "palette", ["charcoal", "black", "steel"])),
                reference_seed=seed,
            )
        else:
            pack = cls(
                character_id=char.id,
                name=char.name,
                age="30s",
                wardrobe=f"Dark professional attire suitable for {char.role or 'operative'}",
                reference_seed=seed,
            )
        pack.generate_reference_sheet()
        return pack

    @classmethod
    def from_visual_reference(cls, ref: CharacterVisualReference, seed: int = 42) -> CharacterContinuityPack:
        """Build character pack from VisualBible CharacterVisualReference."""
        pack = cls(
            character_id=ref.character_id,
            name=ref.name,
            age=ref.age,
            face_shape=ref.face_features,
            build=ref.build,
            hair=ref.hair,
            hair_style=ref.hair,
            wardrobe=ref.clothing,
            signature_props=list(ref.signature_props),
            reference_images={"primary": ref.reference_image_url} if ref.reference_image_url else {},
            reference_seed=seed,
        )
        pack.generate_reference_sheet()
        return pack


class LocationContinuityPack(BaseModel):
    """Mandatory physical, structural, and atmospheric identity for a location."""
    model_config = ConfigDict(extra="ignore")

    location_id: str
    name: str = "Location"
    architecture: str = "Industrial brutalist concrete and steel beams"
    layout: str = "Expansive open floor plan with central clearing and perimeter catwalks"
    doors: str = "Heavy reinforced steel roll-up dock door and rusted service entrance"
    windows: str = "High clerestory wired glass panes, broken in several sections"
    furniture: str = "Stacked wooden shipping crates, rusted steel shelving, solitary metal table"
    materials: str = "Corrugated steel, stained concrete, weathered wood, tarnished iron"
    lighting: str = "Moonlight shafts filtering through high skylights, single swinging halogen work lamp"
    palette: str = "Cold charcoal slate, industrial rust orange, tarnished steel, nocturnal midnight blue"
    landmarks: List[str] = Field(default_factory=lambda: ["Rusted industrial crane hook", "Reinforced freight elevator shaft"])
    reference_images: List[str] = Field(default_factory=list)

    def prompt_summary(self) -> str:
        """Dense textual prompt summary for location continuity."""
        landmarks_str = f", landmarks: {', '.join(self.landmarks)}" if self.landmarks else ""
        return (
            f"{self.name} [ID:{self.location_id}]: {self.architecture}, layout: {self.layout}, "
            f"materials: {self.materials}, apertures: doors({self.doors}) windows({self.windows}), "
            f"lighting: {self.lighting}, palette: {self.palette}{landmarks_str}"
        )

    @classmethod
    def from_location(cls, loc: Location) -> LocationContinuityPack:
        """Build location pack from WorldState Location."""
        vp = getattr(loc, "visual_profile", None)
        if vp:
            return cls(
                location_id=loc.id,
                name=loc.name,
                architecture=getattr(vp, "architecture", loc.description or "Architectural interior"),
                layout=getattr(vp, "layout", "Open staged layout"),
                materials=getattr(vp, "materials", "Concrete and metal"),
                lighting=getattr(vp, "lighting", "Low-key chiaroscuro"),
                palette=getattr(vp, "palette", "Cold slate, deep black"),
                landmarks=[loc.name],
            )
        return cls(
            location_id=loc.id,
            name=loc.name,
            architecture=loc.description or "Moody atmospheric interior",
            landmarks=[loc.name],
        )

    @classmethod
    def from_visual_reference(cls, ref: LocationVisualReference) -> LocationContinuityPack:
        """Build location pack from VisualBible LocationVisualReference."""
        return cls(
            location_id=ref.location_id,
            name=ref.name,
            architecture=ref.architecture,
            layout=ref.environment_type,
            lighting=ref.lighting_setup,
            palette=ref.color_palette,
            landmarks=list(ref.key_landmarks),
            reference_images=[ref.reference_image_url] if ref.reference_image_url else [],
        )


class PropContinuityPack(BaseModel):
    """Mandatory physical and material continuity identity for key narrative props."""
    model_config = ConfigDict(extra="ignore")

    prop_id: str
    name: str = "Narrative Prop"
    shape: str = "Rectangular folio dossier with reinforced spine"
    dimensions: str = "Approx 30cm x 22cm x 3cm (A4 standard folio)"
    materials: str = "Aged oxblood calfskin leather, tarnished brass latch clasp"
    color: str = "Deep burgundy oxblood and tarnished antique brass"
    markings: str = "Debossed circular intelligence agency seal with redacted stencil markings"
    damage: str = "Scuffed corner edges, water ring on lower cover, creased leather spine"
    logos_stamps: str = "Faded crimson 'TOP SECRET // EYES ONLY' diagonal rubber stamp"
    reference_images: List[str] = Field(default_factory=list)

    def prompt_summary(self) -> str:
        """Dense textual prompt summary for prop continuity."""
        return (
            f"{self.name} [ID:{self.prop_id}]: {self.shape}, {self.dimensions}, materials: {self.materials}, "
            f"color: {self.color}, markings: {self.markings}, wear: {self.damage}, stamps: {self.logos_stamps}"
        )

    @classmethod
    def from_object(cls, obj: WorldObject) -> PropContinuityPack:
        """Build prop pack from WorldState WorldObject."""
        vp = getattr(obj, "visual_profile", None)
        if vp:
            return cls(
                prop_id=obj.id,
                name=obj.name,
                shape=getattr(vp, "shape", "Distinctive prop"),
                materials=getattr(vp, "material", "Leather and metal"),
                color=getattr(vp, "color", "Dark noir palette"),
                markings=getattr(vp, "unique_markers", obj.description or ""),
            )
        return cls(
            prop_id=obj.id,
            name=obj.name,
            shape=obj.description or "Identifiable story prop",
        )

    @classmethod
    def from_visual_reference(cls, ref: ObjectVisualReference) -> PropContinuityPack:
        """Build prop pack from VisualBible ObjectVisualReference."""
        return cls(
            prop_id=ref.object_id,
            name=ref.name,
            shape=ref.form_factor,
            materials=ref.materials,
            color=ref.colors,
            markings=ref.unique_markings,
            damage=ref.condition,
            reference_images=[ref.reference_image_url] if ref.reference_image_url else [],
        )


class StoryboardSequenceContext(BaseModel):
    """Contextual visual and narrative links across neighboring sequence panels."""
    model_config = ConfigDict(extra="ignore")

    previous_panel: Optional[str] = None
    previous_panel_reference: Optional[str] = None
    character_refs: Dict[str, str] = Field(default_factory=dict)
    location_refs: Dict[str, str] = Field(default_factory=dict)
    prop_refs: Dict[str, str] = Field(default_factory=dict)
    style_reference: str = "Cinematic graphite production storyboard"
    shared_seed_family: int = 1000
