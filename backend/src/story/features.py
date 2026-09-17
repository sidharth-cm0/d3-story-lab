"""Story Input Analysis and Feature Extraction (AI Call Site #1 with Rule Fallback).

Produces:
1. StoryFeatures
2. CanonFact[]
3. StoryRoleBindings

Combined into one structured call when an LLM provider is available, or fully extracted via
deterministic rule-based heuristics when providers are disabled or offline.
"""
from __future__ import annotations
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from .models import StoryFeatures, CanonFact, StoryRoleBindings
from ..domain.proposition import Proposition

TWIST_JUXTAPOSITION_KEYWORDS = {
    "twist", "juxtaposition", "contrast", "routine", "quiet", "peaceful", "tea",
    "slice of life", "irony", "coincidence", "sitting", "classroom", "afternoon",
    "garden", "window", "bored", "staring", "observing", "unrelated", "meditative",
    "parallel", "simple day", "normal morning",
}

ADVERSARIAL_CONFLICT_KEYWORDS = {
    "detective", "spy", "threat", "gun", "kill", "chase", "enemy", "confront",
    "fight", "battle", "stolen", "dossier", "infiltrate", "guard", "vault",
    "heist", "escape", "security", "intrigue", "conspiracy", "covert", "weapon",
}

INTERNAL_CONFLICT_KEYWORDS = {
    "guilt", "regret", "doubt", "identity", "fear", "memory", "dream", "soul",
    "shame", "desire", "inner", "choice", "conscience", "existential", "longing",
}

SOCIAL_CONFLICT_KEYWORDS = {
    "betrayal", "corrupt", "downfall", "family", "society", "scandal", "reputation",
    "class", "power", "politics", "hierarchy", "tradition", "institution",
}

GENRE_KEYWORDS = {
    "thriller": ["detective", "spy", "agent", "dossier", "threat", "conspiracy", "covert"],
    "noir": ["shadow", "rain", "whisper", "smoke", "alley", "corrupt", "betrayal", "cynical"],
    "tragedy": ["downfall", "hubris", "inevitable", "doom", "fateful", "ruin", "collapse"],
    "adventure": ["quest", "journey", "threshold", "treasure", "relic", "ancient", "explore"],
    "contemplative": ["observe", "silence", "routine", "garden", "window", "reflection", "quiet", "tea"],
    "heist": ["vault", "safe", "steal", "robbery", "infiltrate", "security guard", "escape", "lockbox"],
}


class StoryInputAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    features: StoryFeatures
    canon_facts: List[CanonFact] = Field(default_factory=list)
    role_bindings: StoryRoleBindings = Field(default_factory=StoryRoleBindings)


def extract_story_input_rule_based(
    prompt: str,
    input_position: str = "BEGINNING",
) -> StoryInputAnalysisResult:
    """Pure, deterministic heuristic rule-based extraction of StoryFeatures, CanonFacts, and StoryRoleBindings."""
    prompt_lower = prompt.lower()
    words = set(re.findall(r"\b[a-z]{3,}\b", prompt_lower))

    # 1. Genre Signals
    genre_signals: List[str] = []
    for genre, kws in GENRE_KEYWORDS.items():
        if any(kw in prompt_lower for kw in kws):
            genre_signals.append(genre)
    if not genre_signals:
        genre_signals.append("drama")

    # 2. Conflict Axis & Twist Detection
    adversarial_count = sum(1 for kw in ADVERSARIAL_CONFLICT_KEYWORDS if kw in prompt_lower)
    twist_count = sum(1 for kw in TWIST_JUXTAPOSITION_KEYWORDS if kw in prompt_lower)
    internal_count = sum(1 for kw in INTERNAL_CONFLICT_KEYWORDS if kw in prompt_lower)
    social_count = sum(1 for kw in SOCIAL_CONFLICT_KEYWORDS if kw in prompt_lower)

    # Distinguish twist/juxtaposition-driven material from escalating conflict
    twist_driven = (twist_count > 0 and adversarial_count == 0) or (twist_count >= 2 and adversarial_count <= 1)

    if adversarial_count > internal_count and adversarial_count > social_count:
        conflict_axis = "EXTERNAL"
    elif internal_count >= adversarial_count and internal_count >= social_count:
        conflict_axis = "INTERNAL"
    elif social_count > 0:
        conflict_axis = "SOCIAL"
    else:
        conflict_axis = "EXTERNAL" if not twist_driven else "INTERNAL"

    # 3. Scope & Timespan
    if any(w in prompt_lower for w in ["world", "universe", "kingdom", "galaxy", "war", "empire"]):
        scope = "EPIC"
    elif any(w in prompt_lower for w in ["room", "office", "desk", "apartment", "table", "closet", "window"]):
        scope = "INTIMATE"
    else:
        scope = "LOCAL"

    if any(w in prompt_lower for w in ["years", "decades", "lifetime"]):
        timespan = "YEARS"
    elif any(w in prompt_lower for w in ["days", "week", "tomorrow"]):
        timespan = "DAYS"
    elif any(w in prompt_lower for w in ["minutes", "scene", "staring", "sitting", "moment"]):
        timespan = "SINGLE_SCENE"
    else:
        timespan = "HOURS"

    # 4. Input Position
    pos_upper = input_position.upper()
    if pos_upper not in ["BEGINNING", "MIDPOINT", "ENDING", "FULL_CONCEPT", "SOURCE_MATERIAL"]:
        pos_upper = "BEGINNING"

    # 5. Moral Polarity
    moral_polarity = 0.0
    if any(w in prompt_lower for w in ["doom", "fatal", "ruin", "corrupt", "betrayal", "death", "tragic"]):
        moral_polarity = -0.6
    elif any(w in prompt_lower for w in ["hope", "triumph", "redemption", "peace", "reunion"]):
        moral_polarity = 0.6

    features = StoryFeatures(
        input_position=pos_upper,  # type: ignore
        genre_signals=genre_signals,
        protagonist_count=1,
        conflict_axis=conflict_axis,  # type: ignore
        transformation_expected=True,
        withheld_information_present=any(w in prompt_lower for w in ["secret", "hidden", "dossier", "lying", "covert", "classified"]),
        return_to_origin=any(w in prompt_lower for w in ["return", "home", "circle", "journey back"]),
        ensemble=any(w in prompt_lower for w in ["team", "crew", "squad", "family", "ensemble", "group"]),
        tone="noir" if "noir" in genre_signals else ("contemplative" if twist_driven else "dramatic"),
        scope=scope,  # type: ignore
        timespan=timespan,  # type: ignore
        ending_known=pos_upper in ["ENDING", "FULL_CONCEPT"],
        moral_polarity=moral_polarity,
        twist_or_juxtaposition_driven=twist_driven,
    )

    # 6. Extract CanonFacts and RoleBindings from prompt text
    canon_facts: List[CanonFact] = []
    protagonist_id: Optional[str] = None
    antagonist_id: Optional[str] = None
    focal_object_id: Optional[str] = None
    central_proposition_id: Optional[str] = None

    # Detect characters
    if "detective" in prompt_lower or "arjun" in prompt_lower:
        protagonist_id = "char_detective" if "detective" in prompt_lower else "char_arjun"
    elif "courier" in prompt_lower or "maya" in prompt_lower:
        protagonist_id = "char_courier" if "courier" in prompt_lower else "char_maya"
    elif "guard" in prompt_lower:
        protagonist_id = "char_guard"

    if "courier" in prompt_lower and protagonist_id != "char_courier":
        antagonist_id = "char_courier"
    elif "guard" in prompt_lower and protagonist_id != "char_guard":
        antagonist_id = "char_guard"

    # Detect focal object
    for obj_name in ["dossier", "ledger", "key", "relic", "artifact", "device", "document"]:
        if obj_name in prompt_lower:
            focal_object_id = f"obj_{obj_name}"
            # Extract sentence or clause containing the object as source_span
            match = re.search(rf"([^.?!;]*\b{obj_name}\b[^.?!;]*)", prompt, re.IGNORECASE)
            span = match.group(1).strip() if match else f"Mentions {obj_name}"
            canon_facts.append(
                CanonFact(
                    proposition_id=f"prop_canon_{obj_name}",
                    source_span=span,
                    role_tag="focal_object",
                )
            )
            central_proposition_id = f"prop_canon_{obj_name}"
            break

    # If secret or hiding is mentioned
    if "secret" in prompt_lower or "hiding" in prompt_lower or "locked" in prompt_lower:
        match = re.search(r"([^.?!;]*(?:secret|hiding|locked)[^.?!;]*)", prompt, re.IGNORECASE)
        span = match.group(1).strip() if match else "Secret or hidden element"
        canon_facts.append(
            CanonFact(
                proposition_id="prop_canon_hidden_secret",
                source_span=span,
                role_tag="central_proposition",
            )
        )
        if not central_proposition_id:
            central_proposition_id = "prop_canon_hidden_secret"

    role_bindings = StoryRoleBindings(
        protagonist_character_id=protagonist_id,
        antagonist_character_id=antagonist_id,
        central_proposition_id=central_proposition_id,
        focal_object_id=focal_object_id,
    )

    return StoryInputAnalysisResult(
        features=features,
        canon_facts=canon_facts,
        role_bindings=role_bindings,
    )


def analyze_story_input(
    prompt: str,
    input_position: str = "BEGINNING",
    provider: Optional[Any] = None,
) -> StoryInputAnalysisResult:
    """Analyze story input through AI Call Site #1 (or deterministic fallback).
    
    Returns structured StoryInputAnalysisResult containing StoryFeatures, CanonFact[], and StoryRoleBindings.
    """
    if provider is not None and hasattr(provider, "generate_structured"):
        try:
            system_prompt = (
                "You are an expert story analyst. Analyze the narrative input fragment and extract "
                "StoryFeatures, CanonFacts, and StoryRoleBindings as structured output."
            )
            analysis_prompt = (
                f"Input narrative fragment (position: {input_position}):\n"
                f'"{prompt}"\n\n'
                f"Analyze dramatic conflict, scope, tone, genre, twist potential, facts, and character/object roles."
            )
            res = provider.generate_structured(StoryInputAnalysisResult, analysis_prompt, system_prompt=system_prompt)
            if isinstance(res, StoryInputAnalysisResult):
                return res
        except Exception:
            # Fall back cleanly to deterministic rule-based analysis
            pass

    return extract_story_input_rule_based(prompt, input_position=input_position)
