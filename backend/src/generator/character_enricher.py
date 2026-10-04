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
        auth = draft.get_authority(field_name)
        if auth in (FieldAuthority.USER_LOCKED, FieldAuthority.USER_PREFERRED):
            return False

        if not auth:
            val = getattr(draft, field_name, None)
            if val is None and hasattr(draft, "dynamics") and draft.dynamics:
                val = getattr(draft.dynamics, field_name, None)
            if val is None and hasattr(draft, "reference_profile") and draft.reference_profile:
                val = getattr(draft.reference_profile, field_name, None)
            if val is None or val == [] or val == {} or val == "":
                return True
            return True

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

        # 7. Character Dynamics Fields (Design Metadata)
        premise_ctx = f" regarding the situation ({premise[:40]}...)" if premise else ""
        if any(k in role_lower for k in ("detective", "investigator", "inspector")):
            dyn_data = {
                "core_value": ("Objective truth and accountability", "role_inference:investigator_core_value"),
                "shadow_value": ("Obsessive control over the narrative", "role_inference:investigator_shadow_value"),
                "conscious_want": (f"Uncover the concealed facts behind the current inquiry{premise_ctx}.", "role_inference:investigator_want"),
                "dramatic_need": ("Acknowledge personal culpability and learn to trust allies.", "role_inference:investigator_need"),
                "fear": ("Being misled or becoming complicit in institutional deception.", "role_inference:investigator_fear"),
                "contradiction": ("Demands full disclosure from others while harboring personal secrets.", "role_inference:investigator_contradiction"),
                "moral_boundary": ("Will not fabricate evidence or frame an innocent suspect.", "role_inference:investigator_moral_boundary"),
                "habits": (["Checks line of sight and room exits upon entering.", "Meticulously cross-references written notes."], "role_inference:investigator_habits"),
                "mannerisms": (["Direct, unblinking gaze when listening.", "Subtle tapping of pen against notebook."], "role_inference:investigator_mannerisms"),
                "lifestyle": ("Nocturnal work rhythm, minimalist apartment, constant case files.", "role_inference:investigator_lifestyle"),
                "speech_style": ("Precise, interrogative cadence with dry, economical phrasing.", "role_inference:investigator_speech_style"),
                "conflict_strategy": ("Methodical pressure, tactical silence, and evidential confrontation.", "role_inference:investigator_conflict_strategy"),
            }
        elif any(k in role_lower for k in ("courier", "smuggler", "runner")):
            dyn_data = {
                "core_value": ("Personal autonomy and survival", "role_inference:courier_core_value"),
                "shadow_value": ("Cynical detachment and self-preservation", "role_inference:courier_shadow_value"),
                "conscious_want": (f"Deliver the critical item to the destination cleanly{premise_ctx}.", "role_inference:courier_want"),
                "dramatic_need": ("Recognize when a cause is worth risking personal safety for.", "role_inference:courier_need"),
                "fear": ("Capture, confinement, and loss of independence.", "role_inference:courier_fear"),
                "contradiction": ("Claims loyalty only to the fee, but protects vulnerable bystanders.", "role_inference:courier_contradiction"),
                "moral_boundary": ("Refuses to traffic lethal biocontaminants or harm bystanders.", "role_inference:courier_moral_boundary"),
                "habits": (["Constantly scans peripheral crowds for surveillance tails.", "Keeps hands near concealed pockets."], "role_inference:courier_habits"),
                "mannerisms": (["Restless foot-shifting, quick darting glances.", "Speaks while checking surroundings."], "role_inference:courier_mannerisms"),
                "lifestyle": ("Nomadic existence across transit hubs, modular lightweight gear.", "role_inference:courier_lifestyle"),
                "speech_style": ("Fast-paced, colloquial street jargon, evasive answers to personal queries.", "role_inference:courier_speech_style"),
                "conflict_strategy": ("Rapid evasion and immediate disengagement over static confrontation.", "role_inference:courier_conflict_strategy"),
            }
        elif any(k in role_lower for k in ("analyst", "scientist", "doctor", "surgeon", "neurosurgeon", "researcher")):
            dyn_data = {
                "core_value": ("Empirical rigor and preservation of truth", "role_inference:analyst_core_value"),
                "shadow_value": ("Intellectual arrogance and emotional detachment", "role_inference:analyst_shadow_value"),
                "conscious_want": (f"Authenticate contested records and secure sensitive findings{premise_ctx}.", "role_inference:analyst_want"),
                "dramatic_need": ("Accept human vulnerability and unpredictable emotional factors.", "role_inference:analyst_need"),
                "fear": ("Catastrophic error due to incomplete data or external tampering.", "role_inference:analyst_fear"),
                "contradiction": ("Pursues objective reality while ignoring emotional impact on colleagues.", "role_inference:analyst_contradiction"),
                "moral_boundary": ("Will not falsify analytical conclusions under political pressure.", "role_inference:analyst_moral_boundary"),
                "habits": (["Adjusts glasses or rubs temples when evaluating conflicting claims.", "Organizes workspaces into strict functional zones."], "role_inference:analyst_habits"),
                "mannerisms": (["Calculated pauses before answering, steepled fingers.", "Even, monotone vocal delivery."], "role_inference:analyst_mannerisms"),
                "lifestyle": ("Structured schedules, sterile lab or office environment, coffee dependency.", "role_inference:analyst_lifestyle"),
                "speech_style": ("Articulate, qualified statements filled with technical precision.", "role_inference:analyst_speech_style"),
                "conflict_strategy": ("Defuses conflict with verifiable facts, logic, and policy constraints.", "role_inference:analyst_conflict_strategy"),
            }
        elif any(k in role_lower for k in ("executive", "director", "corporate")):
            dyn_data = {
                "core_value": ("Strategic order and organizational dominance", "role_inference:executive_core_value"),
                "shadow_value": ("Machiavellian leverage and ruthless expendability", "role_inference:executive_shadow_value"),
                "conscious_want": (f"Protect organizational assets and contain damaging leaks{premise_ctx}.", "role_inference:executive_want"),
                "dramatic_need": ("Confront the moral cost of relentless ambition.", "role_inference:executive_need"),
                "fear": ("Loss of status, public humiliation, and irrelevance.", "role_inference:executive_fear"),
                "contradiction": ("Preaches collective mission while treating subordinates as disposable.", "role_inference:executive_contradiction"),
                "moral_boundary": ("Avoids overt criminal acts that leave direct personal paper trails.", "role_inference:executive_moral_boundary"),
                "habits": (["Checks timepiece during conversations to signal dominance.", "Maintains an uncluttered, authoritative desk."], "role_inference:executive_habits"),
                "mannerisms": (["Smooth, measured posture with practiced smiles that do not reach the eyes.", "Minimal unscripted movement."], "role_inference:executive_mannerisms"),
                "lifestyle": ("Luxury surroundings, executive lounges, private transportation.", "role_inference:executive_lifestyle"),
                "speech_style": ("Diplomatic, persuasive rhetoric laced with veiled imperatives.", "role_inference:executive_speech_style"),
                "conflict_strategy": ("Institutional leverage, behind-the-scenes pressure, and strategic compromise.", "role_inference:executive_conflict_strategy"),
            }
        elif any(k in role_lower for k in ("operative", "agent", "spy")):
            dyn_data = {
                "core_value": ("Mission execution and operational discipline", "role_inference:operative_core_value"),
                "shadow_value": ("Total emotional suppression", "role_inference:operative_shadow_value"),
                "conscious_want": (f"Execute the operational mandate without compromise{premise_ctx}.", "role_inference:operative_want"),
                "dramatic_need": ("Rediscover genuine identity beneath layers of tactical deception.", "role_inference:operative_need"),
                "fear": ("Compromised cover and psychological unraveling.", "role_inference:operative_fear"),
                "contradiction": ("Lives entirely by lies in service of an overarching truth.", "role_inference:operative_contradiction"),
                "moral_boundary": ("Refuses to betray direct comrades in the field.", "role_inference:operative_moral_boundary"),
                "habits": (["Memorizes floorplans and vehicle plates automatically.", "Maintains sanitized digital footprints."], "role_inference:operative_habits"),
                "mannerisms": (["Relaxed readiness, unreadable neutral facial expression.", "Economy of physical gesture."], "role_inference:operative_mannerisms"),
                "lifestyle": ("Sparse safehouses, compartmentalized relationships, ready travel bag.", "role_inference:operative_lifestyle"),
                "speech_style": ("Guarded, neutral tone, answers with questions when pressed.", "role_inference:operative_speech_style"),
                "conflict_strategy": ("Calculated de-escalation followed by sudden, decisive neutralization.", "role_inference:operative_conflict_strategy"),
            }
        else:
            dyn_data = {
                "core_value": ("Integrity and self-determination", "default_inference:generic_core_value"),
                "shadow_value": ("Defensive skepticism", "default_inference:generic_shadow_value"),
                "conscious_want": (f"Protect personal standing and navigate the unfolding crisis{premise_ctx}.", "default_inference:generic_want"),
                "dramatic_need": ("Face unaddressed vulnerability and accept necessary change.", "default_inference:generic_need"),
                "fear": ("Helplessness in the face of escalating events.", "default_inference:generic_fear"),
                "contradiction": ("Desires connection yet pushes people away under stress.", "default_inference:generic_contradiction"),
                "moral_boundary": ("Will not compromise fundamental personal loyalties.", "default_inference:generic_moral_boundary"),
                "habits": (["Paces when thinking through complex dilemmas.", "Regularly double-checks personal belongings."], "default_inference:generic_habits"),
                "mannerisms": (["Expressive brow, earnest eye contact with slight hesitation.", "Quick self-correcting smile."], "role_inference:generic_mannerisms"),
                "lifestyle": ("Pragmatic urban routine, balancing work and survival.", "default_inference:generic_lifestyle"),
                "speech_style": ("Direct and sincere, occasionally hesitant when uncertain.", "default_inference:generic_speech_style"),
                "conflict_strategy": ("Direct confrontation tempered by moral appeal.", "default_inference:generic_conflict_strategy"),
            }

        for field_name, (val, rule) in dyn_data.items():
            if self.can_enrich_field(draft, field_name):
                draft.set_field(field_name, val, FieldAuthority.SYSTEM_INFERRED, inference_rule=rule)

        # 5. Primary and secondary archetype inference
        from .archetype_inference import ArchetypeInferenceEngine
        if draft.dynamics:
            ArchetypeInferenceEngine.enrich_dynamics_archetypes(
                dynamics=draft.dynamics,
                role=draft.role or "",
                personality_traits=draft.personality_traits,
            )
            # Sync provenance to draft
            if "primary_archetype" in draft.dynamics.provenance:
                draft.provenance["primary_archetype"] = draft.dynamics.provenance["primary_archetype"]
            if "secondary_archetype" in draft.dynamics.provenance:
                draft.provenance["secondary_archetype"] = draft.dynamics.provenance["secondary_archetype"]

        # 8. Character Reference Profile (Stable Visual Identity)
        if any(k in role_lower for k in ("detective", "investigator", "inspector")):
            ref_data = {
                "apparent_age_range": ("Late 30s", "role_inference:investigator_age"),
                "build": ("Lean athletic frame, upright posture", "role_inference:investigator_build"),
                "height_impression": ("Approx. 6ft (183cm)", "role_inference:investigator_height"),
                "face_description": ("Angular jawline, sharp observant eyes with faint crow's feet", "role_inference:investigator_face"),
                "hair": ("Short dark hair with slight silvering at temples", "role_inference:investigator_hair"),
                "grooming": ("Neatly trimmed stubble, clean collar", "role_inference:investigator_grooming"),
                "distinguishing_features": ("Faint scar near right temple", "role_inference:investigator_features"),
                "baseline_wardrobe": ("Dark wool trench coat over a collared shirt and tailored trousers", "role_inference:investigator_wardrobe"),
                "wardrobe_palette": (["charcoal", "slate gray", "matte black", "muted navy"], "role_inference:investigator_palette"),
                "posture": ("Upright guarded stance, watchful composure", "role_inference:investigator_posture"),
                "signature_objects": (["Pocket notebook with brass pen", "Vintage silver watch"], "role_inference:investigator_objects"),
                "usual_environments": (["Subterranean archives", "Dimly lit interrogation rooms"], "role_inference:investigator_environments"),
            }
        elif any(k in role_lower for k in ("courier", "smuggler", "runner")):
            ref_data = {
                "apparent_age_range": ("Late 20s", "role_inference:courier_age"),
                "build": ("Compact and wiry frame, quick reflexes", "role_inference:courier_build"),
                "height_impression": ("Average height, agile silhouette", "role_inference:courier_height"),
                "face_description": ("Sharp watchful gaze with alert brow", "role_inference:courier_face"),
                "hair": ("Close-cropped dark hair", "role_inference:courier_hair"),
                "grooming": ("Practical and low-maintenance", "role_inference:courier_grooming"),
                "distinguishing_features": ("Faded burn mark on left forearm", "role_inference:courier_features"),
                "baseline_wardrobe": ("Weatherproof hooded jacket, cargo pants, reinforced boots", "role_inference:courier_wardrobe"),
                "wardrobe_palette": (["graphite", "oil black", "weathered olive"], "role_inference:courier_palette"),
                "posture": ("Restless readiness, coiled to move", "role_inference:courier_posture"),
                "signature_objects": (["Heavy-duty courier pouch", "Waterproof flashlight"], "role_inference:courier_objects"),
                "usual_environments": (["Industrial transit bays", "Rooftops and service corridors"], "role_inference:courier_environments"),
            }
        elif any(k in role_lower for k in ("analyst", "scientist", "doctor", "surgeon", "neurosurgeon", "researcher")):
            ref_data = {
                "apparent_age_range": ("Early 40s", "role_inference:analyst_age"),
                "build": ("Slender, precise posture", "role_inference:analyst_build"),
                "height_impression": ("Average height, composed frame", "role_inference:analyst_height"),
                "face_description": ("Meticulous, observant eyes, narrow spectacles", "role_inference:analyst_face"),
                "hair": ("Combed dark brown hair, side-parted", "role_inference:analyst_hair"),
                "grooming": ("Impeccably clean-shaven", "role_inference:analyst_grooming"),
                "distinguishing_features": ("Wire-rimmed reading glasses", "role_inference:analyst_features"),
                "baseline_wardrobe": ("Pressed lab coat or tailored dark blazer with pressed shirt", "role_inference:analyst_wardrobe"),
                "wardrobe_palette": (["sterile white", "slate gray", "deep navy"], "role_inference:analyst_palette"),
                "posture": ("Erect, academic, deliberate stillness", "role_inference:analyst_posture"),
                "signature_objects": (["Encrypted data pad", "Stylus pen"], "role_inference:analyst_objects"),
                "usual_environments": (["Sterile laboratories", "Secure server rooms"], "role_inference:analyst_environments"),
            }
        else:
            ref_data = {
                "apparent_age_range": ("Mid 30s", "default_inference:generic_age"),
                "build": ("Standard athletic build", "default_inference:generic_build"),
                "height_impression": ("Average height, upright stance", "default_inference:generic_height"),
                "face_description": ("Composed facial expression with observant eyes", "default_inference:generic_face"),
                "hair": ("Neatly trimmed dark hair", "default_inference:generic_hair"),
                "grooming": ("Neatly groomed", "default_inference:generic_grooming"),
                "distinguishing_features": ("Quiet, unyielding gaze", "default_inference:generic_features"),
                "baseline_wardrobe": ("Subdued tailored outerwear suitable for urban settings", "default_inference:generic_wardrobe"),
                "wardrobe_palette": (["charcoal", "dark gray", "black"], "default_inference:generic_palette"),
                "posture": ("Composed and alert posture", "default_inference:generic_posture"),
                "signature_objects": (["Leather-bound notebook"], "default_inference:generic_objects"),
                "usual_environments": (["Urban interior spaces", "Transit corridors"], "default_inference:generic_environments"),
            }

        for field_name, (val, rule) in ref_data.items():
            if self.can_enrich_field(draft, field_name):
                draft.set_field(field_name, val, FieldAuthority.SYSTEM_INFERRED, inference_rule=rule)

        # Single-authority derivation from dynamics
        draft.reference_profile.sync_from_dynamics(draft.dynamics)

        # Keep legacy visual_profile synchronized
        draft.visual_profile = draft.reference_profile.to_actor_visual_profile(draft.id, draft.name)

        return draft
