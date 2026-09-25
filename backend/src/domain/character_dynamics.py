"""Domain models for character dynamics design-time profile and authority tracking."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from .character_creation import FieldAuthority, FieldProvenance
from .archetype import ArchetypeType

DYNAMICS_FIELD_NAMES = {
    "core_value",
    "shadow_value",
    "conscious_want",
    "dramatic_need",
    "fear",
    "contradiction",
    "moral_boundary",
    "habits",
    "mannerisms",
    "lifestyle",
    "speech_style",
    "conflict_strategy",
    "primary_archetype",
    "secondary_archetype",
}


class CharacterDynamicsProfile(BaseModel):
    """Design-time character dynamics profile.

    CRITICAL INVARIANT:
    This is character design metadata, NOT canonical simulation state.
    - conscious_want may project into canonical Goal.
    - dramatic_need is strictly analytical and must NEVER drive ActionProposal or DecisionPolicy.
    - habits, mannerisms, lifestyle, speech_style are design cues for later subtext/performance analysis.
    """

    core_value: str = Field(default="", description="Guiding principle or conscious primary value")
    shadow_value: Optional[str] = Field(default=None, description="Compromised or unacknowledged secondary value")
    conscious_want: str = Field(default="", description="Explicit external objective (can project into Goal)")
    dramatic_need: str = Field(
        default="",
        description="Analytical internal growth requirement (NEVER directly drives ActionProposal or DecisionPolicy)",
    )
    fear: str = Field(default="", description="Deepest internal aversion or vulnerability")
    contradiction: str = Field(default="", description="Paradoxical tension between behavior and belief")
    moral_boundary: Optional[str] = Field(default=None, description="Line character will not cross under pressure")
    habits: List[str] = Field(default_factory=list, description="Observable behavioral routines")
    mannerisms: List[str] = Field(default_factory=list, description="Physical/gestural signatures")
    lifestyle: Optional[str] = Field(default=None, description="Daily operational context / living conditions")
    speech_style: Optional[str] = Field(default=None, description="Verbal cadence, diction, vocabulary")
    conflict_strategy: Optional[str] = Field(default=None, description="Default approach to interpersonal tension")
    primary_archetype: Optional[ArchetypeType] = Field(default=None, description="Primary narrative archetype orientation")
    secondary_archetype: Optional[ArchetypeType] = Field(default=None, description="Secondary or shadow archetype orientation")

    provenance: Dict[str, FieldProvenance] = Field(
        default_factory=dict,
        description="Per-field authority and provenance metadata",
    )

    model_config = ConfigDict(extra="ignore")

    def get_authority(self, field_name: str) -> Optional[FieldAuthority]:
        """Get the authority of a dynamics field, or None if no provenance recorded."""
        prov = self.provenance.get(field_name)
        return prov.authority if prov else None

    def is_locked(self, field_name: str) -> bool:
        """Check if a dynamics field is locked by the user."""
        return self.get_authority(field_name) == FieldAuthority.USER_LOCKED

    def lock_field(self, field_name: str) -> None:
        """Lock a dynamics field so it cannot be overwritten by enrichment or regeneration."""
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
        """Unlock a previously locked dynamics field."""
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
        """Set a dynamics field value and record its provenance, respecting existing lock/priority constraints.

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
