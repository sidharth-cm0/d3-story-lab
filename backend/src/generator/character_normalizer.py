"""Character profile normalizer transforming raw user input into structured drafts with field authorities."""

from __future__ import annotations
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from src.domain.continuity import ActorVisualProfile
from src.domain.character_creation import (
    FieldAuthority,
    FieldProvenance,
    CharacterInput,
    CharacterProfileDraft,
)
from src.domain.archetype import ArchetypeType

# Known personality keywords for deterministic extraction
PERSONALITY_LEXICON = [
    "ambitious", "cautious", "cynical", "loyal", "observant", "guarded",
    "analytical", "ruthless", "empathetic", "arrogant", "nervous", "brave",
    "curious", "defiant", "quiet", "charming", "secretive", "paranoid",
    "honest", "stubborn", "reckless", "calm", "stoic", "resourceful",
    "distrusting", "distrustful", "suspicious", "vigilant", "calculating",
    "meticulous", "tenacious", "relentless", "pragmatic", "idealistic",
]

COMMON_ROLES = [
    "detective", "investigator", "courier", "scientist", "doctor",
    "neurosurgeon", "surgeon", "analyst", "operative", "agent", "lawyer",
    "engineer", "journalist", "reporter", "hacker", "assassin", "thief",
    "smuggler", "officer", "executive", "director", "pilot", "guard",
    "consultant", "broker", "informant", "archivist",
]


class CharacterProfileNormalizer:
    """Normalizes natural-language descriptions and guided form payloads into structured drafts."""

    def normalize(
        self,
        raw_text: Optional[str] = None,
        structured_payload: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        draft_id: Optional[str] = None,
    ) -> Tuple[CharacterInput, CharacterProfileDraft]:
        """Produce a CharacterInput record and a CharacterProfileDraft with appropriate FieldAuthority tags."""
        raw_text_clean = raw_text.strip() if raw_text else None
        char_input = CharacterInput(
            project_id=project_id,
            raw_text=raw_text_clean,
            structured_payload=structured_payload,
        )

        draft = CharacterProfileDraft(
            id=draft_id or f"draft_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            input_id=char_input.id,
        )

        # 1. If natural language text provided, extract fields deterministically
        if raw_text_clean:
            self._extract_from_text(raw_text_clean, draft)

        # 2. If structured payload provided, apply structured fields (higher priority)
        if structured_payload:
            self._apply_structured_payload(structured_payload, draft)

        # Ensure minimal name and role fallback if completely empty
        if not draft.name:
            # Fallback placeholder if user submitted totally blank input
            draft.name = "Unnamed Character"
            draft.provenance["name"] = FieldProvenance(
                field_name="name",
                value=draft.name,
                authority=FieldAuthority.SYSTEM_GENERATED,
            )

        if not draft.role:
            draft.role = "Protagonist"
            draft.provenance["role"] = FieldProvenance(
                field_name="role",
                value=draft.role,
                authority=FieldAuthority.SYSTEM_GENERATED,
            )

        # Link input to draft
        char_input.linked_character_id = draft.id
        return char_input, draft

    def _extract_from_text(self, text: str, draft: CharacterProfileDraft) -> None:
        """Extract profile fields deterministically from free-text natural language."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # A. Check for explicit line key-value pairs (e.g., "Name: Arjun", "Role: Investigator")
        kv_pairs = {}
        for line in lines:
            m = re.match(r"^([A-Za-z\s]+)[:=]\s*(.+)$", line)
            if m:
                k = m.group(1).strip().lower()
                v = m.group(2).strip()
                kv_pairs[k] = v

        # Also search inline key-value pairs (e.g., "Core Value: Medical ethics. Conscious Want: Find truth.")
        for m in re.finditer(r"\b([A-Za-z][A-Za-z\s]{1,30})[:=]\s*([^\n;]+?)(?=\s+[A-Z][A-Za-z\s]{1,30}[:=]|\.\s+[A-Z]|\n|$)", text):
            k = m.group(1).strip().lower()
            v = m.group(2).strip().rstrip(".")
            if k not in kv_pairs and len(k) > 1:
                kv_pairs[k] = v

        # 1. Name extraction
        name_val = kv_pairs.get("name")
        if name_val:
            draft.set_field("name", name_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Name: {name_val}")
        else:
            # Try patterns: "Meet <Name>", "Dr. <Name>", "<Name> is a...", "Detective <Name>"
            m_meet = re.search(r"(?:meet|introducing)\s+(?:(Dr\.|Doctor|Detective|Agent|Officer|Inspector|Captain)\s+)?([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*)", text, re.IGNORECASE)
            m_title = re.search(r"\b(Detective|Dr\.|Doctor|Agent|Officer|Inspector|Captain)\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*)", text)
            m_is = re.search(r"^([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*)\s+(?:is a|is an|\bas\b|,)", text)

            if m_meet:
                title = m_meet.group(1) or ""
                name_body = m_meet.group(2).strip()
                cand = f"{title} {name_body}".strip() if title else name_body
                draft.set_field("name", cand, FieldAuthority.USER_PREFERRED, source_snippet=m_meet.group(0))
            elif m_title:
                cand = f"{m_title.group(1)} {m_title.group(2)}".strip()
                draft.set_field("name", cand, FieldAuthority.USER_PREFERRED, source_snippet=m_title.group(0))
            elif m_is:
                cand = m_is.group(1).strip()
                draft.set_field("name", cand, FieldAuthority.USER_PREFERRED, source_snippet=m_is.group(0))
            else:
                # First two capitalized words
                words = re.findall(r"\b[A-Z][a-zA-Z'\-]+\b", text)
                if words:
                    cand = " ".join(words[:2]) if len(words) >= 2 else words[0]
                    draft.set_field("name", cand, FieldAuthority.USER_PREFERRED, source_snippet=cand)

        # 2. Role extraction
        role_val = kv_pairs.get("role") or kv_pairs.get("profession") or kv_pairs.get("occupation")
        if role_val:
            draft.set_field("role", role_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Role: {role_val}")
        else:
            # Look for regex "is a(n) <role>" or words from COMMON_ROLES
            m_role_is = re.search(r"\bis\s+an?\s+([a-zA-Z\-\s]+?)(?:,|\.|\s+who|\s+with|\s+whose)", text, re.IGNORECASE)
            found_role = None
            snippet = None
            if m_role_is:
                extracted = m_role_is.group(1).strip()
                # filter out non-role adjectives if too long
                if len(extracted.split()) <= 4:
                    found_role = extracted.title()
                    snippet = m_role_is.group(0)

            if not found_role:
                for cr in COMMON_ROLES:
                    m_cr = re.search(rf"\b({cr})\b", text, re.IGNORECASE)
                    if m_cr:
                        found_role = m_cr.group(1).title()
                        snippet = m_cr.group(0)
                        break

            if found_role:
                draft.set_field("role", found_role, FieldAuthority.USER_PREFERRED, source_snippet=snippet)

        # 3. Goals
        goals_val = kv_pairs.get("goal") or kv_pairs.get("goals") or kv_pairs.get("objective")
        if goals_val:
            g_list = [g.strip() for g in re.split(r"[;,]\s*", goals_val) if g.strip()]
            draft.set_field("goals", g_list, FieldAuthority.USER_PREFERRED, source_snippet=f"Goal: {goals_val}")
        else:
            # Look for "wants to ...", "aims to ...", "determined to ...", "mission is to ..."
            g_matches = re.findall(
                r"\b(?:wants to|aims to|determined to|seeking to|trying to|mission is to)\s+([^.,;\n]+)",
                text,
                re.IGNORECASE,
            )
            if g_matches:
                g_list = [g.strip().capitalize() for g in g_matches if g.strip()]
                draft.set_field("goals", g_list, FieldAuthority.USER_PREFERRED, source_snippet="; ".join(g_matches))

        # 4. Secrets / Fears
        sec_val = kv_pairs.get("secret") or kv_pairs.get("secrets") or kv_pairs.get("fear")
        if sec_val:
            s_list = [s.strip() for s in re.split(r"[;,]\s*", sec_val) if s.strip()]
            draft.set_field("secrets", s_list, FieldAuthority.USER_PREFERRED, source_snippet=f"Secret: {sec_val}")
        else:
            s_matches = re.findall(
                r"\b(?:secretly,?\s+|hiding\s+|fears?\s+(?:that\s+)?|his secret is\s+|her secret is\s+|their secret is\s+)([^.,;\n]+)",
                text,
                re.IGNORECASE,
            )
            if s_matches:
                s_list = [s.strip().capitalize() for s in s_matches if s.strip()]
                draft.set_field("secrets", s_list, FieldAuthority.USER_PREFERRED, source_snippet="; ".join(s_matches))

        # 5. Beliefs
        bel_val = kv_pairs.get("belief") or kv_pairs.get("beliefs") or kv_pairs.get("believes")
        if bel_val:
            b_list = [b.strip() for b in re.split(r"[;,]\s*", bel_val) if b.strip()]
            draft.set_field("beliefs", b_list, FieldAuthority.USER_PREFERRED, source_snippet=f"Belief: {bel_val}")
        else:
            b_matches = re.findall(
                r"\b(?:believes? that|believes?|suspects? that|suspects?|convinced that)\s+([^.,;\n]+)",
                text,
                re.IGNORECASE,
            )
            if b_matches:
                b_list = [b.strip().capitalize() for b in b_matches if b.strip()]
                draft.set_field("beliefs", b_list, FieldAuthority.USER_PREFERRED, source_snippet="; ".join(b_matches))

        # 6. Personality Traits
        traits_val = kv_pairs.get("personality") or kv_pairs.get("traits")
        found_traits: Dict[str, float] = {}
        trait_snippets: List[str] = []
        if traits_val:
            trait_words = [t.strip().lower() for t in re.split(r"[,;/\s]+", traits_val) if t.strip()]
            for tw in trait_words:
                found_traits[tw] = 0.8
            trait_snippets.append(traits_val)
        else:
            # Match keywords from lexicon
            lower_text = text.lower()
            for lex in PERSONALITY_LEXICON:
                if re.search(rf"\b{lex}\b", lower_text):
                    found_traits[lex] = 0.8
                    trait_snippets.append(lex)

        if found_traits:
            draft.set_field(
                "personality_traits",
                found_traits,
                FieldAuthority.USER_PREFERRED,
                source_snippet=", ".join(trait_snippets),
            )

        # 7. Visual Profile / Appearance
        vis_val = kv_pairs.get("appearance") or kv_pairs.get("looks") or kv_pairs.get("attire")
        age_match = re.search(r"\b(\d{1,2})[- ]years?[- ]old\b", text, re.IGNORECASE)
        age_decade = re.search(r"\b(?:in (?:his|her|their) )?(early|mid|late)?\s*(twenties|thirties|forties|fifties|sixties|20s|30s|40s|50s|60s)\b", text, re.IGNORECASE)
        cloth_match = re.search(r"\b(?:wearing|dressed in|wears)\s+([^.,;\n]+)", text, re.IGNORECASE)
        face_match = re.search(r"\b([^.,;\n]*(?:scar|jawline|beard|eyes|stubble|hair|gaze)[^.,;\n]*)", text, re.IGNORECASE)

        age_str = "Mid 30s"
        if age_match:
            age_str = f"{age_match.group(1)} years old"
        elif age_decade:
            age_str = f"{age_decade.group(0).strip().capitalize()}"

        clothing_str = cloth_match.group(1).strip() if cloth_match else ""
        face_str = face_match.group(1).strip() if face_match else ""

        if vis_val or age_match or age_decade or cloth_match or face_match:
            c_id = draft.id or "char_draft"
            vis = ActorVisualProfile(
                character_id=c_id,
                name=draft.name or "Character",
                age=age_str,
                clothing=clothing_str or "Practical everyday clothes",
                face_traits=face_str or "Attentive expression",
                hairstyle="Short hair",
                build="Average build",
                signature_items=[],
                emotional_style="Composed",
            )
            draft.set_field(
                "visual_profile",
                vis,
                FieldAuthority.USER_PREFERRED,
                source_snippet=vis_val or text[:80],
            )

        # Description
        draft.set_field("description", text, FieldAuthority.USER_PREFERRED, source_snippet=text[:120])

        # 8. Character Dynamics Fields
        # Core Value
        cv_val = kv_pairs.get("core value") or kv_pairs.get("value") or kv_pairs.get("values")
        if cv_val:
            draft.set_field("core_value", cv_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Value: {cv_val}")
        else:
            m_val = re.search(r"\b(?:values?|stands for|driven by|deeply values?)\s+([^.,;\n]+)", text, re.IGNORECASE)
            if m_val:
                draft.set_field("core_value", m_val.group(1).strip().capitalize(), FieldAuthority.USER_PREFERRED, source_snippet=m_val.group(0))

        # Shadow Value
        sv_val = kv_pairs.get("shadow value") or kv_pairs.get("shadow")
        if sv_val:
            draft.set_field("shadow_value", sv_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Shadow: {sv_val}")

        # Conscious Want
        want_val = kv_pairs.get("conscious want") or kv_pairs.get("want") or kv_pairs.get("wants")
        if want_val:
            draft.set_field("conscious_want", want_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Want: {want_val}")
        elif draft.goals and len(draft.goals) > 0:
            draft.set_field("conscious_want", draft.goals[0], FieldAuthority.USER_PREFERRED, source_snippet=draft.goals[0])

        # Dramatic Need (Analytical Only - Never directly drives simulation)
        need_val = kv_pairs.get("dramatic need") or kv_pairs.get("need") or kv_pairs.get("needs")
        if need_val:
            draft.set_field("dramatic_need", need_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Need: {need_val}")
        else:
            m_need = re.search(
                r"\b(?:dramatic need|deep down,? (?:he|she|they) needs? to|needs? to learn to|unconsciously needs? to)\s+([^.,;\n]+)",
                text,
                re.IGNORECASE,
            )
            if m_need:
                draft.set_field("dramatic_need", m_need.group(1).strip().capitalize(), FieldAuthority.USER_PREFERRED, source_snippet=m_need.group(0))

        # Fear
        fear_val = kv_pairs.get("fear") or kv_pairs.get("fears") or kv_pairs.get("deepest fear")
        if fear_val:
            draft.set_field("fear", fear_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Fear: {fear_val}")
        else:
            m_fear = re.search(r"\b(?:fears?\s+(?:that\s+)?|terrified of\s+|afraid of\s+)([^.,;\n]+)", text, re.IGNORECASE)
            if m_fear:
                draft.set_field("fear", m_fear.group(1).strip().capitalize(), FieldAuthority.USER_PREFERRED, source_snippet=m_fear.group(0))

        # Contradiction
        contra_val = kv_pairs.get("contradiction") or kv_pairs.get("paradox")
        if contra_val:
            draft.set_field("contradiction", contra_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Contradiction: {contra_val}")
        else:
            m_contra = re.search(r"\b(?:paradoxically|yet secretly|despite this,? (?:he|she|they))\s+([^.,;\n]+)", text, re.IGNORECASE)
            if m_contra:
                draft.set_field("contradiction", m_contra.group(1).strip().capitalize(), FieldAuthority.USER_PREFERRED, source_snippet=m_contra.group(0))

        # Moral Boundary
        mb_val = kv_pairs.get("moral boundary") or kv_pairs.get("boundary") or kv_pairs.get("line")
        if mb_val:
            draft.set_field("moral_boundary", mb_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Moral Boundary: {mb_val}")

        # Habits
        hab_val = kv_pairs.get("habit") or kv_pairs.get("habits")
        if hab_val:
            h_list = [h.strip() for h in re.split(r"[;,]\s*", hab_val) if h.strip()]
            draft.set_field("habits", h_list, FieldAuthority.USER_PREFERRED, source_snippet=f"Habits: {hab_val}")

        # Mannerisms
        man_val = kv_pairs.get("mannerism") or kv_pairs.get("mannerisms")
        if man_val:
            m_list = [m.strip() for m in re.split(r"[;,]\s*", man_val) if m.strip()]
            draft.set_field("mannerisms", m_list, FieldAuthority.USER_PREFERRED, source_snippet=f"Mannerisms: {man_val}")

        # Lifestyle
        life_val = kv_pairs.get("lifestyle")
        if life_val:
            draft.set_field("lifestyle", life_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Lifestyle: {life_val}")

        # Speech Style
        speech_val = kv_pairs.get("speech style") or kv_pairs.get("voice") or kv_pairs.get("speech")
        if speech_val:
            draft.set_field("speech_style", speech_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Speech Style: {speech_val}")
        else:
            m_speech = re.search(r"\b(?:speaks? with|speaks? in|speech style is)\s+([^.,;\n]+)", text, re.IGNORECASE)
            if m_speech:
                draft.set_field("speech_style", m_speech.group(1).strip().capitalize(), FieldAuthority.USER_PREFERRED, source_snippet=m_speech.group(0))

        # Conflict Strategy
        strat_val = kv_pairs.get("conflict strategy") or kv_pairs.get("conflict") or kv_pairs.get("pressure response") or kv_pairs.get("social strategy")
        if strat_val:
            draft.set_field("conflict_strategy", strat_val, FieldAuthority.USER_PREFERRED, source_snippet=f"Strategy: {strat_val}")

        # Primary Archetype
        arch_val = kv_pairs.get("primary archetype") or kv_pairs.get("archetype")
        if arch_val:
            parsed_arch = ArchetypeType.from_str(arch_val)
            if parsed_arch:
                draft.set_field("primary_archetype", parsed_arch, FieldAuthority.USER_PREFERRED, source_snippet=f"Archetype: {arch_val}")

        # Secondary Archetype
        sec_arch_val = kv_pairs.get("secondary archetype") or kv_pairs.get("shadow archetype")
        if sec_arch_val:
            parsed_sec_arch = ArchetypeType.from_str(sec_arch_val)
            if parsed_sec_arch:
                draft.set_field("secondary_archetype", parsed_sec_arch, FieldAuthority.USER_PREFERRED, source_snippet=f"Secondary Archetype: {sec_arch_val}")

    def _apply_structured_payload(self, payload: Dict[str, Any], draft: CharacterProfileDraft) -> None:
        """Apply structured form data to the draft with field authorities."""
        locked_fields = set(payload.get("locked_fields", []))

        def get_auth(field_name: str) -> FieldAuthority:
            return FieldAuthority.USER_LOCKED if field_name in locked_fields else FieldAuthority.USER_PREFERRED

        # Name
        if payload.get("name"):
            draft.set_field("name", str(payload["name"]).strip(), get_auth("name"), source_snippet="form:name")

        # Role
        if payload.get("role"):
            draft.set_field("role", str(payload["role"]).strip(), get_auth("role"), source_snippet="form:role")

        # Description
        if payload.get("description"):
            draft.set_field("description", str(payload["description"]).strip(), get_auth("description"), source_snippet="form:description")

        # Goals
        if payload.get("goals") is not None:
            goals = payload["goals"]
            if isinstance(goals, str):
                goals = [g.strip() for g in re.split(r"[\n,;]+", goals) if g.strip()]
            draft.set_field("goals", list(goals), get_auth("goals"), source_snippet="form:goals")

        # Secrets
        if payload.get("secrets") is not None:
            secrets = payload["secrets"]
            if isinstance(secrets, str):
                secrets = [s.strip() for s in re.split(r"[\n,;]+", secrets) if s.strip()]
            draft.set_field("secrets", list(secrets), get_auth("secrets"), source_snippet="form:secrets")

        # Beliefs
        if payload.get("beliefs") is not None:
            beliefs = payload["beliefs"]
            if isinstance(beliefs, str):
                beliefs = [b.strip() for b in re.split(r"[\n,;]+", beliefs) if b.strip()]
            draft.set_field("beliefs", list(beliefs), get_auth("beliefs"), source_snippet="form:beliefs")

        # Personality traits
        if payload.get("personality_traits") is not None:
            traits_raw = payload["personality_traits"]
            traits_dict: Dict[str, float] = {}
            if isinstance(traits_raw, dict):
                for k, v in traits_raw.items():
                    traits_dict[str(k).strip().lower()] = float(v)
            elif isinstance(traits_raw, list):
                for item in traits_raw:
                    traits_dict[str(item).strip().lower()] = 0.8
            elif isinstance(traits_raw, str):
                for item in re.split(r"[\n,;]+", traits_raw):
                    if item.strip():
                        traits_dict[item.strip().lower()] = 0.8
            draft.set_field("personality_traits", traits_dict, get_auth("personality_traits"), source_snippet="form:personality_traits")

        # Visual Profile
        if payload.get("visual_profile") is not None:
            vp = payload["visual_profile"]
            if isinstance(vp, dict):
                c_id = draft.id or "char_draft"
                vis = ActorVisualProfile(
                    character_id=c_id,
                    name=draft.name or "Character",
                    age=str(vp.get("age", "Mid 30s")),
                    clothing=str(vp.get("clothing", "Practical attire")),
                    face_traits=str(vp.get("face_traits", "Observant gaze")),
                    hairstyle=str(vp.get("hairstyle", "Short hair")),
                    build=str(vp.get("build", "Medium build")),
                    signature_items=list(vp.get("signature_items", [])),
                    emotional_style=str(vp.get("emotional_style", "Controlled")),
                )
                draft.set_field("visual_profile", vis, get_auth("visual_profile"), source_snippet="form:visual_profile")
            elif isinstance(vp, ActorVisualProfile):
                draft.set_field("visual_profile", vp, get_auth("visual_profile"), source_snippet="form:visual_profile")

        # Emotional state
        if payload.get("emotional_state") is not None:
            es = payload["emotional_state"]
            if isinstance(es, dict):
                draft.set_field("emotional_state", {k: float(v) for k, v in es.items()}, get_auth("emotional_state"), source_snippet="form:emotional_state")

        # Location
        if payload.get("current_location_id"):
            draft.set_field("current_location_id", str(payload["current_location_id"]), get_auth("current_location_id"), source_snippet="form:current_location_id")

        # Dynamics fields from structured payload
        dynamics_data = payload.get("dynamics") or {}
        if not isinstance(dynamics_data, dict):
            dynamics_data = {}

        for df in (
            "core_value", "shadow_value", "conscious_want", "dramatic_need",
            "fear", "contradiction", "moral_boundary", "lifestyle",
            "speech_style", "conflict_strategy"
        ):
            val = dynamics_data.get(df) if df in dynamics_data else payload.get(df)
            if val is not None and str(val).strip():
                auth = FieldAuthority.USER_LOCKED if (df in locked_fields or f"dynamics.{df}" in locked_fields) else FieldAuthority.USER_PREFERRED
                draft.set_field(df, str(val).strip(), auth, source_snippet=f"form:{df}")

        for list_df in ("habits", "mannerisms"):
            val = dynamics_data.get(list_df) if list_df in dynamics_data else payload.get(list_df)
            if val is not None:
                if isinstance(val, str):
                    items = [item.strip() for item in re.split(r"[\n,;]+", val) if item.strip()]
                elif isinstance(val, list):
                    items = [str(item).strip() for item in val if str(item).strip()]
                else:
                    items = []
                auth = FieldAuthority.USER_LOCKED if (list_df in locked_fields or f"dynamics.{list_df}" in locked_fields) else FieldAuthority.USER_PREFERRED
                draft.set_field(list_df, items, auth, source_snippet=f"form:{list_df}")

        # Archetype fields
        for af in ("primary_archetype", "secondary_archetype"):
            val = dynamics_data.get(af) if af in dynamics_data else payload.get(af)
            if val is not None:
                parsed_val = ArchetypeType.from_str(str(val)) if not isinstance(val, ArchetypeType) else val
                if parsed_val:
                    auth = FieldAuthority.USER_LOCKED if (af in locked_fields or f"dynamics.{af}" in locked_fields) else FieldAuthority.USER_PREFERRED
                    draft.set_field(af, parsed_val, auth, source_snippet=f"form:{af}")
