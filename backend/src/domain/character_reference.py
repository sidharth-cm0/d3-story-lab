"""Domain model for Character Reference Profile (stable visual identity) and authority tracking.

Phase G1 & G2:
- Authoritative model for stable visual identity: apparent age range, build, height impression,
  face description, hair, grooming, distinguishing features, baseline wardrobe, wardrobe palette,
  posture, body language, signature objects, usual environments.
- Per-field FieldAuthority and FieldProvenance tracking (USER_LOCKED, USER_PREFERRED, SYSTEM_INFERRED, SYSTEM_GENERATED).
- Single-Authority Rule:
  Where concepts overlap with CharacterDynamicsProfile (mannerisms, habits, lifestyle),
  CharacterDynamicsProfile remains authoritative. CharacterReferenceProfile derives/references
  visual expressions from these fields rather than duplicating editable copies.
  (speech_style remains strictly in dynamics).
- Compatibility adapters for ActorVisualProfile and CharacterVisualRef.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from .character_creation import FieldAuthority, FieldProvenance
from .continuity import ActorVisualProfile

REFERENCE_FIELD_NAMES = {
    "apparent_age_range",
    "build",
    "height_impression",
    "face_description",
    "hair",
    "grooming",
    "distinguishing_features",
    "baseline_wardrobe",
    "wardrobe_palette",
    "posture",
    "body_language",
    "signature_objects",
    "usual_environments",
}


class CharacterReferenceProfile(BaseModel):
    """Authoritative design-time profile for a character's stable visual identity.

    CRITICAL ARCHITECTURAL INVARIANT:
    This profile is visual design and storyboard identity metadata.
    It must NEVER influence canonical simulation state, DecisionPolicy,
    GoalActionSelector, Motivation, ActionProposal, or ActionValidator scoring.
    """

    apparent_age_range: str = Field(default="", description="Perceived age band (e.g. 'Late 30s', 'Early 20s')")
    build: str = Field(default="", description="Physical frame and build (e.g. 'Lean athletic build', 'Stocky compact')")
    height_impression: str = Field(default="", description="Height impression (e.g. 'Tall and imposing', 'Average height')")
    face_description: str = Field(default="", description="Facial structure and features (e.g. 'Sharp angular jawline, intense observant gaze')")
    hair: str = Field(default="", description="Hair color, length, and style (e.g. 'Short textured dark hair, slight silvering at temples')")
    grooming: str = Field(default="", description="Grooming state (e.g. 'Meticulously kept', 'Rough stubble, unkempt')")
    distinguishing_features: str = Field(default="", description="Scars, marks, or physical identifiers (e.g. 'Faint scar above right brow')")
    baseline_wardrobe: str = Field(default="", description="Default signature attire (e.g. 'Tailored charcoal wool trench coat over dark collared shirt')")
    wardrobe_palette: List[str] = Field(default_factory=list, description="Dominant clothing colors (e.g. ['charcoal', 'slate gray', 'matte black'])")
    posture: str = Field(default="", description="Default physical stance (e.g. 'Upright, guarded, coiled readiness')")
    body_language: str = Field(default="", description="Visible physical carriage and gestural baseline (derived from dynamics mannerisms when available)")
    signature_objects: List[str] = Field(default_factory=list, description="Recognizable personal props/items (e.g. ['Silver pocket watch', 'Leather notebook'])")
    usual_environments: List[str] = Field(default_factory=list, description="Typical spatial settings (derived from dynamics lifestyle when available)")
    reference_mode: str = Field(default="TEXT_ONLY", description="Visual reference mode: 'TEXT_ONLY' or 'USER_UPLOAD'")
    reference_image_path: Optional[str] = Field(default=None, description="Path to verified user-uploaded reference image")

    provenance: Dict[str, FieldProvenance] = Field(
        default_factory=dict,
        description="Per-field authority and provenance metadata",
    )

    model_config = ConfigDict(extra="ignore")

    def get_authority(self, field_name: str) -> Optional[FieldAuthority]:
        """Get the authority of a field, or None if no provenance recorded."""
        prov = self.provenance.get(field_name)
        return prov.authority if prov else None

    def is_locked(self, field_name: str) -> bool:
        """Check if a field is locked by the user."""
        return self.get_authority(field_name) == FieldAuthority.USER_LOCKED

    def lock_field(self, field_name: str) -> None:
        """Lock a field so it cannot be overwritten by enrichment or regeneration."""
        now = datetime.now(timezone.utc).isoformat()
        current_val = getattr(self, field_name, None)
        existing = self.provenance.get(field_name)

        if existing:
            self.provenance[field_name] = existing.model_copy(
                update={"authority": FieldAuthority.USER_LOCKED, "locked_at": now}
            )
        else:
            self.provenance[field_name] = FieldProvenance(
                field_name=field_name,
                value=current_val,
                authority=FieldAuthority.USER_LOCKED,
                locked_at=now,
            )

    def unlock_field(self, field_name: str) -> None:
        """Unlock a previously locked field."""
        existing = self.provenance.get(field_name)
        if not existing:
            return

        if existing.source_snippet:
            new_auth = FieldAuthority.USER_PREFERRED
        elif existing.inference_rule:
            new_auth = FieldAuthority.SYSTEM_INFERRED
        else:
            new_auth = FieldAuthority.SYSTEM_GENERATED

        self.provenance[field_name] = existing.model_copy(
            update={"authority": new_auth, "locked_at": None}
        )

    def set_field(
        self,
        field_name: str,
        value: Any,
        authority: FieldAuthority,
        source_snippet: Optional[str] = None,
        inference_rule: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Set a field value and record its provenance, respecting existing lock/priority constraints.

        Returns True if the field was updated, False if blocked by authority rules.
        """
        existing = self.provenance.get(field_name)
        if not force and existing:
            # Rule 1: USER_LOCKED fields can NEVER be overwritten
            if existing.authority == FieldAuthority.USER_LOCKED:
                return False

            # Rule 2: USER_PREFERRED cannot be overwritten by SYSTEM_*
            if existing.authority == FieldAuthority.USER_PREFERRED and authority in (
                FieldAuthority.SYSTEM_INFERRED,
                FieldAuthority.SYSTEM_GENERATED,
            ):
                return False

        # Apply update
        if hasattr(self, field_name):
            setattr(self, field_name, value)

        now = datetime.now(timezone.utc).isoformat()
        self.provenance[field_name] = FieldProvenance(
            field_name=field_name,
            value=value,
            authority=authority,
            source_snippet=source_snippet,
            inference_rule=inference_rule,
            created_at=existing.created_at if existing else now,
            locked_at=now if authority == FieldAuthority.USER_LOCKED else None,
        )
        return True

    def sync_from_dynamics(self, dynamics: Any) -> None:
        """Single-authority derivation: derive body language, posture, and usual environments from dynamics.

        Does not overwrite USER_LOCKED or USER_PREFERRED values.
        """
        if not dynamics:
            return

        # 1. Mannerisms -> Body Language
        mannerisms = getattr(dynamics, "mannerisms", None)
        if mannerisms and isinstance(mannerisms, list) and len(mannerisms) > 0:
            if not self.is_locked("body_language") and self.get_authority("body_language") != FieldAuthority.USER_PREFERRED:
                derived_bl = "; ".join(mannerisms)
                self.set_field(
                    "body_language",
                    derived_bl,
                    FieldAuthority.SYSTEM_INFERRED,
                    inference_rule="derived_from:dynamics.mannerisms",
                )

        # 2. Habits -> Posture baseline cues
        habits = getattr(dynamics, "habits", None)
        if habits and isinstance(habits, list) and len(habits) > 0:
            if not self.is_locked("posture") and self.get_authority("posture") != FieldAuthority.USER_PREFERRED:
                if not self.posture:
                    # Choose habit related to physical carriage if any
                    self.set_field(
                        "posture",
                        f"Observable habits: {'; '.join(habits[:2])}",
                        FieldAuthority.SYSTEM_INFERRED,
                        inference_rule="derived_from:dynamics.habits",
                    )

        # 3. Lifestyle -> Usual Environments
        lifestyle = getattr(dynamics, "lifestyle", None)
        if lifestyle and isinstance(lifestyle, str) and lifestyle.strip():
            if not self.is_locked("usual_environments") and self.get_authority("usual_environments") != FieldAuthority.USER_PREFERRED:
                if not self.usual_environments:
                    self.set_field(
                        "usual_environments",
                        [lifestyle.strip()],
                        FieldAuthority.SYSTEM_INFERRED,
                        inference_rule="derived_from:dynamics.lifestyle",
                    )

    def to_actor_visual_profile(self, character_id: str = "char_ref", name: str = "Character") -> ActorVisualProfile:
        """Compatibility adapter: project into legacy ActorVisualProfile."""
        face_full = self.face_description
        if self.distinguishing_features:
            face_full = f"{face_full}, {self.distinguishing_features}" if face_full else self.distinguishing_features

        hair_full = self.hair
        if self.grooming:
            hair_full = f"{hair_full} ({self.grooming})" if hair_full else self.grooming

        return ActorVisualProfile(
            character_id=character_id,
            name=name,
            age=self.apparent_age_range or "Mid 30s",
            face_traits=face_full or "Focused observant gaze",
            hairstyle=hair_full or "Short hair",
            build=self.build or "Standard build",
            clothing=self.baseline_wardrobe or "Utilitarian attire",
            signature_items=list(self.signature_objects),
            emotional_style=self.posture or "Composed",
        )

    @classmethod
    def from_actor_visual_profile(cls, avp: ActorVisualProfile) -> CharacterReferenceProfile:
        """Compatibility adapter: construct CharacterReferenceProfile from legacy ActorVisualProfile."""
        profile = cls(
            apparent_age_range=avp.age or "Mid 30s",
            build=avp.build or "Standard build",
            face_description=avp.face_traits or "Observant gaze",
            hair=avp.hairstyle or "Short hair",
            baseline_wardrobe=avp.clothing or "Practical attire",
            signature_objects=list(avp.signature_items or []),
            posture=avp.emotional_style or "Composed posture",
        )
        # Register provenance for converted fields
        now = datetime.now(timezone.utc).isoformat()
        for f in ("apparent_age_range", "build", "face_description", "hair", "baseline_wardrobe", "signature_objects", "posture"):
            val = getattr(profile, f)
            if val:
                profile.provenance[f] = FieldProvenance(
                    field_name=f,
                    value=val,
                    authority=FieldAuthority.SYSTEM_INFERRED,
                    inference_rule="migrated_from:ActorVisualProfile",
                    created_at=now,
                )
        return profile
