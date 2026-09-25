"""Deterministic, rule-based archetype inference engine for D3 Story Lab.

CRITICAL INVARIANTS:
1. Purely deterministic baseline: zero external LLM dependencies required.
2. Respects FieldAuthority: NEVER overwrites USER_LOCKED or USER_PREFERRED archetype fields.
3. Archetype is design metadata: NEVER forces actions or grants omniscient knowledge.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple, Any

from ..domain.archetype import ArchetypeType
from ..domain.character_creation import FieldAuthority
from ..domain.character_dynamics import CharacterDynamicsProfile


# Lexical and semantic indicator maps for the 12 standard narrative archetypes
ARCHETYPE_SIGNALS: Dict[ArchetypeType, Dict[str, List[str]]] = {
    ArchetypeType.SAGE: {
        "roles": [
            "detective", "investigator", "analyst", "scientist", "researcher",
            "scholar", "doctor", "surgeon", "neurosurgeon", "inspector", "pathologist"
        ],
        "keywords": [
            "truth", "knowledge", "empirical", "data", "facts", "analyze", "examine",
            "evidence", "rigor", "logic", "clarity", "objective", "inquiry", "uncover",
            "comprehend", "investigate", "deduce", "accurate", "precision", "verifiable"
        ],
        "fears": ["ignorance", "falsehood", "deception", "misdiagnosis", "error", "delusion"],
    },
    ArchetypeType.HERO: {
        "roles": [
            "operative", "agent", "soldier", "warrior", "protector", "guardian",
            "defender", "champion", "enforcer", "sentinel"
        ],
        "keywords": [
            "courage", "mission", "duty", "justice", "honor", "execute", "resolve",
            "confront", "protect", "stand", "overcome", "strength", "discipline",
            "brave", "tenacious", "sacrifice", "resilient", "victory"
        ],
        "fears": ["weakness", "cowardice", "failure", "powerlessness", "compromise"],
    },
    ArchetypeType.RULER: {
        "roles": [
            "executive", "director", "corporate", "chief", "boss", "administrator",
            "leader", "governor", "manager", "official", "commissioner"
        ],
        "keywords": [
            "order", "control", "dominance", "leadership", "authority", "leverage",
            "strategic", "stability", "command", "power", "organizational", "structure",
            "status", "hierarchy", "mandate", "govern"
        ],
        "fears": ["chaos", "overthrow", "loss of control", "humiliation", "irrelevance", "anarchy"],
    },
    ArchetypeType.CAREGIVER: {
        "roles": [
            "caretaker", "nurse", "healer", "counselor", "mentor", "social worker",
            "advocate", "paramedic", "guardian"
        ],
        "keywords": [
            "care", "compassion", "protect", "nurture", "help", "support", "empathy",
            "safety", "service", "comfort", "shelter", "heal", "kindness", "loyalty",
            "selfless", "vulnerable"
        ],
        "fears": ["harming others", "selfishness", "neglect", "ingratitude", "abandonment"],
    },
    ArchetypeType.OUTLAW: {
        "roles": [
            "rebel", "smuggler", "outlaw", "fugitive", "rogue", "insurgent",
            "thief", "vigilante", "hacker", "dissident"
        ],
        "keywords": [
            "freedom", "disruption", "defiance", "subvert", "shatter", "rebellion",
            "unconventional", "independence", "break", "radical", "rulebreaker",
            "undercover", "underground", "black market", "bypass"
        ],
        "fears": ["confinement", "compliance", "entrapment", "conformity", "subjugation"],
    },
    ArchetypeType.EXPLORER: {
        "roles": [
            "courier", "runner", "traveler", "scout", "explorer", "voyager",
            "wanderer", "navigator", "pioneer", "smuggler"
        ],
        "keywords": [
            "discovery", "journey", "nomadic", "autonomy", "movement", "transit",
            "uncharted", "horizon", "roam", "seek", "escape", "agile", "distance",
            "open road", "routes", "expand"
        ],
        "fears": ["stagnation", "entrapment", "confinement", "monotony", "boredom"],
    },
    ArchetypeType.CREATOR: {
        "roles": [
            "artist", "inventor", "architect", "engineer", "designer", "builder",
            "craftsman", "author", "composer"
        ],
        "keywords": [
            "create", "innovate", "vision", "design", "invent", "originality",
            "craft", "express", "aesthetic", "manifest", "transform", "imagine",
            "artistic", "structure", "build"
        ],
        "fears": ["mediocrity", "creative block", "imitation", "destruction", "sterility"],
    },
    ArchetypeType.INNOCENT: {
        "roles": [
            "novice", "apprentice", "optimist", "idealist", "youth", "believer"
        ],
        "keywords": [
            "hope", "faith", "trust", "goodness", "purity", "optimism", "sincere",
            "innocence", "ideal", "clean", "simple", "untainted", "honest"
        ],
        "fears": ["corruption", "guilt", "punishment", "deceit", "cynicism"],
    },
    ArchetypeType.MAGICIAN: {
        "roles": [
            "catalyst", "visionary", "strategist", "alchemist", "mentalist",
            "transformer", "shaman", "specialist"
        ],
        "keywords": [
            "transform", "catalyst", "insight", "phenomenon", "fundamental", "shift",
            "hidden laws", "metamorphosis", "alchemy", "vision", "intuition", "unseen"
        ],
        "fears": ["stagnation", "unintended destruction", "powerlessness", "blindness"],
    },
    ArchetypeType.LOVER: {
        "roles": [
            "diplomat", "mediator", "companion", "partner", "romantic", "peacemaker"
        ],
        "keywords": [
            "connection", "intimacy", "passion", "harmony", "bond", "devotion",
            "relationship", "unite", "affection", "commitment", "empathy", "belong"
        ],
        "fears": ["rejection", "isolation", "disconnection", "unloved", "conflict"],
    },
    ArchetypeType.JESTER: {
        "roles": [
            "trickster", "provocateur", "wit", "satirist", "comic", "entertainer"
        ],
        "keywords": [
            "humor", "play", "irreverence", "wit", "irony", "satire", "laugh",
            "levity", "provoke", "absurd", "defuse", "subversive", "joke"
        ],
        "fears": ["seriousness", "boredom", "humiliation", "stifling"],
    },
    ArchetypeType.EVERYMAN: {
        "roles": [
            "worker", "citizen", "neighbor", "laborer", "regular", "survivor",
            "bystander", "comrade", "commoner"
        ],
        "keywords": [
            "belonging", "grounded", "fairness", "resilience", "solidarity",
            "practical", "common", "solid", "peer", "equal", "humble", "survive"
        ],
        "fears": ["abandonment", "standing out", "elitism", "exile", "isolation"],
    },
}


class ArchetypeInferenceEngine:
    """Purely deterministic archetype inference service."""

    @staticmethod
    def score_archetypes(
        role: str = "",
        core_value: str = "",
        shadow_value: Optional[str] = None,
        conscious_want: str = "",
        dramatic_need: str = "",
        fear: str = "",
        contradiction: str = "",
        moral_boundary: Optional[str] = None,
        personality_traits: Optional[Dict[str, float]] = None,
        extra_text: str = "",
    ) -> Dict[ArchetypeType, float]:
        """Score each ArchetypeType based on semantic frequency and role weights."""
        scores: Dict[ArchetypeType, float] = {a: 0.0 for a in ArchetypeType}
        role_lower = (role or "").lower()
        text_corpus = " ".join([
            core_value or "",
            shadow_value or "",
            conscious_want or "",
            dramatic_need or "",
            fear or "",
            contradiction or "",
            moral_boundary or "",
            extra_text or "",
        ]).lower()

        traits_dict = personality_traits or {}

        for archetype, signals in ARCHETYPE_SIGNALS.items():
            # 1. Role match (high weight: 3.0)
            for r in signals["roles"]:
                if re.search(rf"\b{re.escape(r)}\b", role_lower):
                    scores[archetype] += 3.0
                    break

            # 2. Keyword match in values / wants / text (weight: 1.0 each)
            for kw in signals["keywords"]:
                if re.search(rf"\b{re.escape(kw)}\b", text_corpus):
                    scores[archetype] += 1.0

            # 3. Fear match (weight: 1.5)
            for f in signals["fears"]:
                if re.search(rf"\b{re.escape(f)}\b", (fear or "").lower()) or re.search(rf"\b{re.escape(f)}\b", text_corpus):
                    scores[archetype] += 1.5

            # 4. Trait affinity (weight: 1.0)
            for trait_name, trait_val in traits_dict.items():
                if trait_val > 0.6 and trait_name.lower() in signals["keywords"]:
                    scores[archetype] += 1.0 * trait_val

        return scores

    @classmethod
    def infer_archetypes(
        cls,
        role: str = "",
        core_value: str = "",
        shadow_value: Optional[str] = None,
        conscious_want: str = "",
        dramatic_need: str = "",
        fear: str = "",
        contradiction: str = "",
        moral_boundary: Optional[str] = None,
        personality_traits: Optional[Dict[str, float]] = None,
        extra_text: str = "",
    ) -> Tuple[ArchetypeType, Optional[ArchetypeType], str]:
        """Deterministically determine primary and secondary archetype with rationale."""
        scores = cls.score_archetypes(
            role=role,
            core_value=core_value,
            shadow_value=shadow_value,
            conscious_want=conscious_want,
            dramatic_need=dramatic_need,
            fear=fear,
            contradiction=contradiction,
            moral_boundary=moral_boundary,
            personality_traits=personality_traits,
            extra_text=extra_text,
        )

        # Sort descending by score, tie-break by archetype enum name
        sorted_archetypes = sorted(
            scores.items(),
            key=lambda item: (item[1], item[0].value),
            reverse=True,
        )

        top_archetype, top_score = sorted_archetypes[0]
        second_archetype, second_score = sorted_archetypes[1]

        # If zero signal matched, fall back safely based on general archetype
        if top_score <= 0.0:
            top_archetype = ArchetypeType.EVERYMAN
            second_archetype = None
            rationale = "Default fallback to EVERYMAN due to unpolarized starting profile."
        else:
            rationale = f"Primary {top_archetype.value} (score={top_score:.1f})"
            if second_score >= 1.5 and second_score >= (top_score * 0.4):
                rationale += f" with secondary {second_archetype.value} (score={second_score:.1f})"
            else:
                second_archetype = None

        return top_archetype, second_archetype, rationale

    @classmethod
    def enrich_dynamics_archetypes(
        cls,
        dynamics: CharacterDynamicsProfile,
        role: str = "",
        personality_traits: Optional[Dict[str, float]] = None,
        force: bool = False,
    ) -> bool:
        """Populate primary and secondary archetypes on a dynamics profile if unlocked.
        
        Guarantees USER_LOCKED fields are never modified.
        Returns True if any field was updated, False otherwise.
        """
        primary, secondary, rationale = cls.infer_archetypes(
            role=role,
            core_value=dynamics.core_value,
            shadow_value=dynamics.shadow_value,
            conscious_want=dynamics.conscious_want,
            dramatic_need=dynamics.dramatic_need,
            fear=dynamics.fear,
            contradiction=dynamics.contradiction,
            moral_boundary=dynamics.moral_boundary,
            personality_traits=personality_traits,
        )

        updated = False

        # 1. Primary archetype
        if dynamics.get_authority("primary_archetype") != FieldAuthority.USER_LOCKED:
            if force or dynamics.primary_archetype is None or dynamics.get_authority("primary_archetype") != FieldAuthority.USER_PREFERRED:
                dynamics.set_field(
                    "primary_archetype",
                    primary,
                    FieldAuthority.SYSTEM_INFERRED,
                    inference_rule=f"archetype_inference:primary_{primary.value.lower()}",
                )
                updated = True

        # 2. Secondary archetype
        if secondary and dynamics.get_authority("secondary_archetype") != FieldAuthority.USER_LOCKED:
            if force or dynamics.secondary_archetype is None or dynamics.get_authority("secondary_archetype") != FieldAuthority.USER_PREFERRED:
                dynamics.set_field(
                    "secondary_archetype",
                    secondary,
                    FieldAuthority.SYSTEM_INFERRED,
                    inference_rule=f"archetype_inference:secondary_{secondary.value.lower()}",
                )
                updated = True

        return updated
