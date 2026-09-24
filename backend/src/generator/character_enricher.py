"""Deterministic character enrichment service respecting field-level authority and user locks."""

from __future__ import annotations
from typing import Optional, Dict, Any, List

from src.domain.continuity import ActorVisualProfile
from src.domain.character_creation import (
    FieldAuthority,
    FieldProvenance,
    CharacterProfileDraft,
)


class CharacterEnrichmentService:
    """Enriches incomplete character profile drafts deterministically without overwriting user data."""

    def can_enrich_field(self, draft: CharacterProfileDraft, field_name: str) -> bool:
        """Return True if the field is missing or has SYSTEM_* authority (safe to enrich).

        Returns False if the field is USER_LOCKED or USER_PREFERRED.
        """
        prov = draft.provenance.get(field_name)
        if not prov:
            val = getattr(draft, field_name, None)
            if val is None or val == [] or val == {} or val == "":
                return True
            return True

        if prov.authority in (FieldAuthority.USER_LOCKED, FieldAuthority.USER_PREFERRED):
            return False

        return True

    def enrich(
        self,
        draft: CharacterProfileDraft,
        premise: Optional[str] = None,
    ) -> CharacterProfileDraft:
        """Deterministically populate missing and unlocked fields based on user data and story context.

        Guarantees that USER_LOCKED and USER_PREFERRED fields remain completely untouched.
        """
        role_lower = (draft.role or "").lower()

        # 1. Personality traits
        if self.can_enrich_field(draft, "personality_traits"):
            if any(k in role_lower for k in ("detective", "investigator", "inspector")):
                traits = {"cautious": 0.8, "observant": 0.9, "distrusting": 0.7, "tenacious": 0.85}
                rule = "role_inference:investigator_traits"
            elif any(k in role_lower for k in ("courier", "smuggler", "runner", "thief")):
                traits = {"agile": 0.85, "alert": 0.8, "pragmatic": 0.75, "secretive": 0.7}
                rule = "role_inference:courier_traits"
            elif any(k in role_lower for k in ("analyst", "scientist", "doctor", "neurosurgeon", "researcher")):
                traits = {"analytical": 0.9, "meticulous": 0.85, "curious": 0.8, "guarded": 0.6}
                rule = "role_inference:analyst_traits"
            elif any(k in role_lower for k in ("executive", "corporate", "lawyer", "director")):
                traits = {"ambitious": 0.9, "calculating": 0.85, "composed": 0.7, "shrewd": 0.8}
                rule = "role_inference:executive_traits"
            elif any(k in role_lower for k in ("operative", "agent", "spy")):
                traits = {"vigilant": 0.9, "stoic": 0.8, "calculating": 0.85, "resourceful": 0.8}
                rule = "role_inference:operative_traits"
            else:
                traits = {"cautious": 0.65, "observant": 0.75, "determined": 0.7}
                rule = "default_inference:generic_traits"

            draft.set_field("personality_traits", traits, FieldAuthority.SYSTEM_INFERRED, inference_rule=rule)

        # 2. Goals
        if self.can_enrich_field(draft, "goals"):
            premise_context = f" regarding the situation ({premise[:50]}...)" if premise else ""
            if any(k in role_lower for k in ("detective", "investigator", "inspector")):
                goals = [
                    f"Uncover the concealed facts behind the current inquiry{premise_context}.",
                    "Verify the credibility of key persons of interest.",
                ]
                rule = "role_inference:investigator_goals"
            elif any(k in role_lower for k in ("courier", "smuggler", "runner")):
                goals = [
                    f"Deliver the critical item to the rendezvous point undetected{premise_context}.",
                    "Evade surveillance and maintain an untraceable route.",
                ]
                rule = "role_inference:courier_goals"
            elif any(k in role_lower for k in ("analyst", "scientist", "doctor", "surgeon", "neurosurgeon", "researcher")):
                goals = [
                    f"Examine and authenticate contested records{premise_context}.",
                    "Prevent sensitive findings from falling into unauthorized hands.",
                ]
                rule = "role_inference:analyst_goals"
            elif any(k in role_lower for k in ("executive", "director", "corporate")):
                goals = [
                    f"Protect organizational assets and contain damaging leaks{premise_context}.",
                    "Secure definitive leverage over strategic competitors.",
                ]
                rule = "role_inference:executive_goals"
            else:
                goals = [
                    f"Protect personal standing and navigate the unfolding situation{premise_context}.",
                    "Secure reliable alliances before committing to further action.",
                ]
                rule = "default_inference:generic_goals"

            draft.set_field("goals", goals, FieldAuthority.SYSTEM_INFERRED, inference_rule=rule)

        # 3. Secrets
        if self.can_enrich_field(draft, "secrets"):
            if any(k in role_lower for k in ("detective", "investigator")):
                secrets = ["Possesses undisclosed prior knowledge of key suspects in the case."]
                rule = "role_inference:investigator_secret"
            elif any(k in role_lower for k in ("courier", "smuggler")):
                secrets = ["Knows the contents of the cargo are far more dangerous than declared."]
                rule = "role_inference:courier_secret"
            elif any(k in role_lower for k in ("analyst", "scientist", "doctor", "surgeon", "neurosurgeon", "researcher")):
                secrets = ["Maintains an unlogged encrypted archive of deleted source data."]
                rule = "role_inference:analyst_secret"
            elif any(k in role_lower for k in ("executive", "director")):
                secrets = ["Approved irregular expenditures to keep certain operations off the ledger."]
                rule = "role_inference:executive_secret"
            else:
                secrets = ["Concealing their true personal connection to the current conflict."]
                rule = "default_inference:generic_secret"

            draft.set_field("secrets", secrets, FieldAuthority.SYSTEM_INFERRED, inference_rule=rule)

        # 4. Beliefs
        if self.can_enrich_field(draft, "beliefs"):
            beliefs = ["Someone close to the center of events is concealing crucial evidence."]
            draft.set_field("beliefs", beliefs, FieldAuthority.SYSTEM_INFERRED, inference_rule="role_inference:primary_belief")

        # 5. Emotional state
        if self.can_enrich_field(draft, "emotional_state"):
            if any(k in role_lower for k in ("detective", "investigator")):
                emo = {"happiness": 0.0, "fear": 0.2, "anger": 0.2, "trust": -0.4, "curiosity": 0.8}
            elif any(k in role_lower for k in ("courier", "smuggler")):
                emo = {"happiness": 0.0, "fear": 0.4, "anger": 0.1, "trust": -0.2, "curiosity": 0.4}
            else:
                emo = {"happiness": 0.1, "fear": 0.2, "anger": 0.1, "trust": 0.0, "curiosity": 0.5}

            draft.set_field("emotional_state", emo, FieldAuthority.SYSTEM_INFERRED, inference_rule="role_inference:emotional_state")

        # 6. Visual Profile
        if self.can_enrich_field(draft, "visual_profile"):
            c_id = draft.id or "char_enriched"
            c_name = draft.name or "Character"
            if any(k in role_lower for k in ("detective", "investigator")):
                vis = ActorVisualProfile(
                    character_id=c_id,
                    name=c_name,
                    age="Late 30s",
                    face_traits="Angular jawline, sharp observant eyes with faint crow's feet",
                    hairstyle="Short dark hair with slight silvering at temples",
                    build="Lean athletic build with upright posture",
                    clothing="Dark wool trench coat over a collared shirt and tailored trousers",
                    signature_items=["Pocket notebook with brass pen", "Vintage silver watch"],
                    emotional_style="Controlled tension and alert observation",
                )
            elif any(k in role_lower for k in ("courier", "smuggler")):
                vis = ActorVisualProfile(
                    character_id=c_id,
                    name=c_name,
                    age="Late 20s",
                    face_traits="Sharp watchful gaze with alert brow",
                    hairstyle="Close-cropped dark hair",
                    build="Compact and wiry frame",
                    clothing="Weatherproof hooded jacket, cargo pants, and reinforced boots",
                    signature_items=["Heavy-duty courier pouch", "Waterproof flashlight"],
                    emotional_style="Restless readiness and quick reflexes",
                )
            else:
                vis = ActorVisualProfile(
                    character_id=c_id,
                    name=c_name,
                    age="Mid 30s",
                    face_traits="Composed facial expression with observant eyes",
                    hairstyle="Neatly combed parted hair",
                    build="Average height with composed posture",
                    clothing="Subdued tailored outerwear suitable for urban environments",
                    signature_items=["Leather-bound notebook"],
                    emotional_style="Guarded composure",
                )

            draft.set_field("visual_profile", vis, FieldAuthority.SYSTEM_INFERRED, inference_rule="role_inference:visual_profile")

        return draft
