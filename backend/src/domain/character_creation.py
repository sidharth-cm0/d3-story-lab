"""Domain models for character creation, field-level authority, and design provenance."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from .continuity import ActorVisualProfile


class FieldAuthority(str, Enum):
    """Authority level governing whether a character profile field can be overwritten."""

    USER_LOCKED = "USER_LOCKED"
    USER_PREFERRED = "USER_PREFERRED"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"


class FieldProvenance(BaseModel):
    """Design-time provenance tracking origin and lock status for a single profile field."""

    field_name: str
    value: Any = None
    authority: FieldAuthority
    source_snippet: Optional[str] = None
    inference_rule: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    locked_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


from .character_dynamics import CharacterDynamicsProfile, DYNAMICS_FIELD_NAMES
from .character_reference import CharacterReferenceProfile, REFERENCE_FIELD_NAMES


class CharacterInput(BaseModel):
    """Immutable record of the raw user input (natural-language text and/or structured form data)."""

    id: str = Field(default_factory=lambda: f"cinp_{uuid.uuid4().hex[:8]}")
    project_id: Optional[str] = None
    raw_text: Optional[str] = None
    structured_payload: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    linked_character_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class CharacterProfileDraft(BaseModel):
    """Working draft of a character profile carrying per-field authority and provenance."""

    id: str = Field(default_factory=lambda: f"draft_{uuid.uuid4().hex[:8]}")
    project_id: Optional[str] = None
    input_id: Optional[str] = None
    name: str = ""
    role: str = ""
    description: Optional[str] = None
    personality_traits: Dict[str, float] = Field(default_factory=dict)
    goals: List[str] = Field(default_factory=list)
    secrets: List[str] = Field(default_factory=list)
    beliefs: List[str] = Field(default_factory=list)
    emotional_state: Dict[str, float] = Field(default_factory=dict)
    visual_profile: Optional[ActorVisualProfile] = None
    current_location_id: Optional[str] = None
    dynamics: CharacterDynamicsProfile = Field(
        default_factory=CharacterDynamicsProfile,
        description="Character dynamics design profile",
    )
    reference_profile: CharacterReferenceProfile = Field(
        default_factory=CharacterReferenceProfile,
        description="Character visual reference design profile",
    )
    provenance: Dict[str, FieldProvenance] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="ignore")

    def get_authority(self, field_name: str) -> Optional[FieldAuthority]:
        """Get the authority of a field, or None if no provenance recorded."""
        if field_name in DYNAMICS_FIELD_NAMES and self.dynamics:
            auth = self.dynamics.get_authority(field_name)
            if auth is not None:
                return auth
        if field_name in REFERENCE_FIELD_NAMES and self.reference_profile:
            auth = self.reference_profile.get_authority(field_name)
            if auth is not None:
                return auth
        prov = self.provenance.get(field_name)
        return prov.authority if prov else None

    def is_locked(self, field_name: str) -> bool:
        """Check if a field is locked by the user."""
        return self.get_authority(field_name) == FieldAuthority.USER_LOCKED

    def lock_field(self, field_name: str) -> None:
        """Lock a field so it cannot be overwritten by enrichment or regeneration."""
        now = datetime.now(timezone.utc).isoformat()
        if field_name in DYNAMICS_FIELD_NAMES and self.dynamics:
            self.dynamics.lock_field(field_name)
            if field_name in self.dynamics.provenance:
                self.provenance[field_name] = self.dynamics.provenance[field_name]
            self.updated_at = now
            return
        if field_name in REFERENCE_FIELD_NAMES and self.reference_profile:
            self.reference_profile.lock_field(field_name)
            if field_name in self.reference_profile.provenance:
                self.provenance[field_name] = self.reference_profile.provenance[field_name]
            self.updated_at = now
            return

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
        self.updated_at = now

    def unlock_field(self, field_name: str) -> None:
        """Unlock a previously locked field."""
        now = datetime.now(timezone.utc).isoformat()
        if field_name in DYNAMICS_FIELD_NAMES and self.dynamics:
            self.dynamics.unlock_field(field_name)
            if field_name in self.dynamics.provenance:
                self.provenance[field_name] = self.dynamics.provenance[field_name]
            self.updated_at = now
            return
        if field_name in REFERENCE_FIELD_NAMES and self.reference_profile:
            self.reference_profile.unlock_field(field_name)
            if field_name in self.reference_profile.provenance:
                self.provenance[field_name] = self.reference_profile.provenance[field_name]
            self.updated_at = now
            return

        existing = self.provenance.get(field_name)
        if not existing:
            return

        # Determine appropriate unlocked authority
        if existing.source_snippet:
            new_auth = FieldAuthority.USER_PREFERRED
        elif existing.inference_rule:
            new_auth = FieldAuthority.SYSTEM_INFERRED
        else:
            new_auth = FieldAuthority.SYSTEM_GENERATED

        self.provenance[field_name] = existing.model_copy(
            update={"authority": new_auth, "locked_at": None}
        )
        self.updated_at = now

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
        if field_name in DYNAMICS_FIELD_NAMES and self.dynamics:
            updated = self.dynamics.set_field(
                field_name=field_name,
                value=value,
                authority=authority,
                source_snippet=source_snippet,
                inference_rule=inference_rule,
                force=force,
            )
            if updated and field_name in self.dynamics.provenance:
                self.provenance[field_name] = self.dynamics.provenance[field_name]
                self.updated_at = datetime.now(timezone.utc).isoformat()
            return updated

        if field_name in REFERENCE_FIELD_NAMES and self.reference_profile:
            updated = self.reference_profile.set_field(
                field_name=field_name,
                value=value,
                authority=authority,
                source_snippet=source_snippet,
                inference_rule=inference_rule,
                force=force,
            )
            if updated and field_name in self.reference_profile.provenance:
                self.provenance[field_name] = self.reference_profile.provenance[field_name]
                self.updated_at = datetime.now(timezone.utc).isoformat()
            return updated

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
        self.updated_at = now
        return True
