"""Story Structure Selection Engine for D3 Story Lab.

Extracts narrative features from raw input and evaluates heuristic suitability scores
(0 - 100) across all dramatic structures.

Supports:
- AUTO mode (recommends highest-fit primary structure + compatible secondary)
- MANUAL mode (respects user selection with compatibility validation)
- Deterministic heuristic scoring with zero required cloud inference
- Non-statistical heuristic scores (never claimed as calibrated probability)
"""

from typing import Dict, List, Optional, Tuple, Any
import re

from src.domain.story_structure import (
    StoryStructureType,
    StructureSelectionMode,
    StructureSelectionResult,
)
from src.narrative.structure_library import (
    STRUCTURE_DEFINITIONS,
    get_compatible_secondary_structures,
    is_structure_pair_compatible,
)


class StructureSelector:
    """Selects or validates story structures based on narrative input features."""

    GENRE_KEYWORD_MAP = {
        "thriller": ["detective", "undercover", "spy", "agent", "dossier", "warehouse", "threat", "gun", "conspiracy", "covert", "classified"],
        "noir": ["midnight", "shadow", "rain", "whisper", "smoke", "alley", "corrupt", "betrayal", "cynical", "gritty"],
        "tragedy": ["downfall", "hubris", "inevitable", "doom", "fateful", "ruin", "collapse"],
        "adventure": ["quest", "journey", "threshold", "treasure", "relic", "ancient", "explore", "wilderness"],
        "contemplative": ["observe", "silence", "routine", "garden", "window", "reflection", "quiet", "afternoon", "tea", "bored in class"],
        "heist": ["vault", "safe", "steal", "robbery", "infiltrate", "security guard", "escape", "lockbox", "loot"],
    }

    def __init__(self, provider: Optional[Any] = None):
        self.provider = provider

    def analyze_input_features(self, prompt: str, input_type: str = "beginning") -> Dict[str, Any]:
        """Extract lightweight heuristic features from user prompt and input type."""
        prompt_lower = prompt.lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", prompt_lower))

        genre_matches: Dict[str, int] = {}
        for genre, keywords in self.GENRE_KEYWORD_MAP.items():
            count = sum(1 for kw in keywords if kw in prompt_lower)
            genre_matches[genre] = count

        has_adversarial_conflict = any(w in prompt_lower for w in ["detective", "spy", "guard", "lying", "secret", "stolen", "dossier", "threat", "confront", "infiltrate", "gun"])
        has_twist_potential = any(w in prompt_lower for w in ["secret", "lying", "hidden", "unforeseen", "mystery", "locked", "undercover"])
        has_mythic_journey = any(w in prompt_lower for w in ["journey", "quest", "travel", "return", "threshold", "trial", "destiny"])
        is_quiet_or_routine = any(w in prompt_lower for w in ["sitting", "classroom", "bored", "waiting", "porch", "staring", "quiet"])

        return {
            "prompt_length": len(words),
            "input_type": input_type.lower(),
            "genre_matches": genre_matches,
            "has_adversarial_conflict": has_adversarial_conflict,
            "has_twist_potential": has_twist_potential,
            "has_mythic_journey": has_mythic_journey,
            "is_quiet_or_routine": is_quiet_or_routine,
        }

    def compute_heuristic_fit_scores(self, features: Dict[str, Any]) -> Dict[StoryStructureType, float]:
        """Calculate heuristic fit scores between 0.0 and 100.0 for each structure."""
        scores: Dict[StoryStructureType, float] = {
            StoryStructureType.THREE_ACT: 65.0,       # Versatile baseline
            StoryStructureType.HERO_JOURNEY: 55.0,
            StoryStructureType.FREYTAG: 60.0,
            StoryStructureType.SAVE_THE_CAT: 60.0,
            StoryStructureType.STORY_CIRCLE: 58.0,
            StoryStructureType.KISHOTENKETSU: 45.0,
        }

        # Boost Three Act for adversarial/investigative setups
        if features["has_adversarial_conflict"]:
            scores[StoryStructureType.THREE_ACT] += 20.0
            scores[StoryStructureType.SAVE_THE_CAT] += 18.0
            scores[StoryStructureType.FREYTAG] += 12.0
            scores[StoryStructureType.KISHOTENKETSU] -= 15.0

        # Noir / gritty / high-stakes tragedy favors Freytag and Three Act
        noir_score = features["genre_matches"].get("noir", 0) + features["genre_matches"].get("thriller", 0)
        if noir_score >= 2:
            scores[StoryStructureType.THREE_ACT] += 8.0
            scores[StoryStructureType.FREYTAG] += 12.0
            scores[StoryStructureType.SAVE_THE_CAT] += 6.0

        # Heist / ticking clock favors Save the Cat
        if features["genre_matches"].get("heist", 0) >= 1:
            scores[StoryStructureType.SAVE_THE_CAT] += 16.0
            scores[StoryStructureType.THREE_ACT] += 6.0

        # Mythic quest favors Hero's Journey
        if features["has_mythic_journey"]:
            scores[StoryStructureType.HERO_JOURNEY] += 30.0
            scores[StoryStructureType.STORY_CIRCLE] += 15.0

        # Quiet / routine / contemplative or non-conflict favors Kishōtenketsu
        if features["is_quiet_or_routine"] and not features["has_adversarial_conflict"]:
            scores[StoryStructureType.KISHOTENKETSU] += 40.0
            scores[StoryStructureType.THREE_ACT] -= 15.0
            scores[StoryStructureType.FREYTAG] -= 20.0

        # Cap scores cleanly within 10.0 to 98.0 (avoiding artificial 100.0 certainty)
        for k in scores:
            scores[k] = round(max(10.0, min(96.0, scores[k])), 1)

        return scores

    def select_structure(
        self,
        prompt: str,
        input_type: str = "beginning",
        mode: StructureSelectionMode = StructureSelectionMode.AUTO,
        manual_primary: Optional[StoryStructureType] = None,
        manual_secondary: Optional[StoryStructureType] = None,
    ) -> StructureSelectionResult:
        """Select primary structure, heuristic fit score, and compatible secondary overlay."""
        features = self.analyze_input_features(prompt, input_type=input_type)
        scores = self.compute_heuristic_fit_scores(features)
        candidate_scores_dict = {k.value: v for k, v in scores.items()}

        if mode == StructureSelectionMode.MANUAL and manual_primary:
            primary = manual_primary
            fit_score = scores.get(primary, 70.0)
            rationale = (
                f"Manual selection: User specified {primary.value}. "
                f"Heuristic suitability assessed at {fit_score}/100 based on prompt elements."
            )
            # Validate secondary compatibility
            secondary = None
            if manual_secondary:
                if is_structure_pair_compatible(primary, manual_secondary):
                    secondary = manual_secondary
                else:
                    rationale += f" Note: Requested secondary {manual_secondary.value} is incompatible with {primary.value} and was omitted."
            return StructureSelectionResult(
                primary_structure=primary,
                fit_score=fit_score,
                fit_rationale=rationale,
                secondary_structure=secondary,
                candidate_scores=candidate_scores_dict,
                selection_mode=StructureSelectionMode.MANUAL,
            )

        # AUTO mode: Pick highest scoring primary structure
        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary, best_score = sorted_candidates[0]

        # Check for a compatible secondary with strong score (>= 68)
        compatibles = get_compatible_secondary_structures(primary)
        secondary: Optional[StoryStructureType] = None
        for cand, c_score in sorted_candidates:
            if cand in compatibles and c_score >= 68.0:
                secondary = cand
                break

        defn = STRUCTURE_DEFINITIONS[primary]
        sec_note = f" with compatible secondary overlay '{secondary.value}'" if secondary else ""
        rationale = (
            f"Heuristic fit score {best_score}/100. "
            f"Selected {defn.display_name}{sec_note} based on prompt genre affinities ({', '.join(defn.genre_affinities[:3])}) "
            f"and conflict profile."
        )

        return StructureSelectionResult(
            primary_structure=primary,
            fit_score=best_score,
            fit_rationale=rationale,
            secondary_structure=secondary,
            candidate_scores=candidate_scores_dict,
            selection_mode=StructureSelectionMode.AUTO,
        )
