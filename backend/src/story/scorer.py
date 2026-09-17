"""Pure rubric scoring function and structure selection for D3 Story Lab."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any

from .models import (
    StoryFeatures,
    StoryStructureDefinition,
    StructureCandidate,
    StructureSelection,
)
from .loader import get_structure_registry
from .compatibility import DEFAULT_COMPATIBILITY_EVALUATOR


def score(
    features: StoryFeatures,
    definitions: Dict[str, StoryStructureDefinition],
) -> List[StructureCandidate]:
    """Pure rubric scoring function.
    
    Given StoryFeatures and structure definitions:
    - Same input produces exactly the same output.
    - Zero I/O, zero cloud calls.
    - Returns fit_score (0.0 - 1.0), never 'confidence' or 'probability'.
    - Returns transparent criterion_contributions mapping.
    - Excludes framing strategies from MACRO candidates.
    - Disqualifies or excludes manual_only structures from auto selection.
    """
    candidates: List[StructureCandidate] = []

    # Score only MACRO structures for primary candidate ranking
    macro_defs = {k: v for k, v in definitions.items() if v.axis == "MACRO"}

    for struct_id, defn in macro_defs.items():
        base_score = 0.50
        contributions: Dict[str, float] = {"base_score": base_score}
        disqualified = False
        disqualifier_reasons: List[str] = []

        if defn.manual_only:
            disqualified = True
            disqualifier_reasons.append("Structure is designated for manual selection only")

        # Evaluate each affinity defined in YAML
        for criterion, weight in defn.affinity.items():
            contrib = 0.0

            if criterion == "conflict_axis.external":
                val = 1.0 if features.conflict_axis == "EXTERNAL" else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "conflict_axis.internal":
                val = 1.0 if features.conflict_axis == "INTERNAL" else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "conflict_axis.social":
                val = 1.0 if features.conflict_axis == "SOCIAL" else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "twist_or_juxtaposition_driven":
                val = 1.0 if features.twist_or_juxtaposition_driven else 0.0
                contrib = weight * (val - 0.5) * 0.5
            elif criterion == "transformation_expected":
                val = 1.0 if features.transformation_expected else 0.0
                contrib = weight * (val - 0.5) * 0.3
            elif criterion == "return_to_origin":
                val = 1.0 if features.return_to_origin else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "protagonist_count.single":
                val = 1.0 if features.protagonist_count == 1 else 0.0
                contrib = weight * (val - 0.5) * 0.3
            elif criterion == "scope.epic":
                val = 1.0 if features.scope == "EPIC" else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "scope.intimate":
                val = 1.0 if features.scope == "INTIMATE" else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion == "moral_polarity.negative":
                val = 1.0 if features.moral_polarity < -0.2 else 0.0
                contrib = weight * (val - 0.5) * 0.4
            elif criterion.startswith("genre."):
                genre_name = criterion.split(".", 1)[1]
                val = 1.0 if genre_name in features.genre_signals else 0.0
                contrib = weight * (val - 0.2) * 0.3
            else:
                # Default generic criterion scaling
                contrib = weight * 0.1

            contributions[criterion] = round(contrib, 3)

        raw_total = sum(contributions.values())
        fit_score = max(0.05, min(0.95, round(raw_total, 3)))

        candidates.append(
            StructureCandidate(
                structure_id=struct_id,
                fit_score=fit_score,
                criterion_contributions=contributions,
                disqualified=disqualified,
                disqualifier_reasons=disqualifier_reasons,
            )
        )

    # Sort descending by (not disqualified, fit_score)
    candidates.sort(key=lambda c: (not c.disqualified, c.fit_score), reverse=True)
    return candidates


def select_structure(
    features: StoryFeatures,
    definitions: Optional[Dict[str, StoryStructureDefinition]] = None,
    mode: str = "AUTO",
    manual_macro: Optional[str] = None,
    manual_beat: Optional[str] = None,
    framing: str = "chronological",
    previous_selection: Optional[StructureSelection] = None,
    raise_on_invalid: bool = False,
) -> StructureSelection:
    """Select dramatic structure configuration, respecting manual overrides, compatibility, and persistence."""
    defs = definitions if definitions is not None else get_structure_registry()
    candidates = score(features, defs)

    # 1. Rule: in_medias_res is FRAMING, never MACRO
    if manual_macro and manual_macro.strip().lower() == "in_medias_res":
        raise ValueError("in_medias_res is FRAMING, never MACRO")

    # 2. If previous selection was overridden by user, preserve user override across re-scoring
    if previous_selection and previous_selection.overridden_by_user:
        primary_macro = previous_selection.primary_macro
        beat_layer = manual_beat if manual_beat is not None else previous_selection.beat_layer
        # Validate beat_layer compatibility if specified
        if beat_layer:
            verdict, reason = DEFAULT_COMPATIBILITY_EVALUATOR.check_macro_beat_verdict(primary_macro, beat_layer)
            if verdict.value == "REJECT":
                if raise_on_invalid:
                    raise ValueError(f"Invalid structure compatibility ({primary_macro} + {beat_layer}): {reason}")
                beat_layer = None

        framing_choice = framing if framing != "chronological" else previous_selection.framing
        return StructureSelection(
            primary_macro=primary_macro,
            beat_layer=beat_layer,
            framing=framing_choice,
            candidates=candidates,
            selection_mode="MANUAL",
            overridden_by_user=True,
        )

    # 3. If explicit manual mode is requested
    if mode.upper() == "MANUAL" and manual_macro:
        macro_key = manual_macro.strip().lower()
        if macro_key in defs and defs[macro_key].axis != "MACRO":
            raise ValueError(f"Structure '{manual_macro}' has axis '{defs[macro_key].axis}', expected 'MACRO'")

        beat_layer = manual_beat
        if beat_layer:
            verdict, reason = DEFAULT_COMPATIBILITY_EVALUATOR.check_macro_beat_verdict(macro_key, beat_layer)
            if verdict.value == "REJECT":
                if raise_on_invalid:
                    raise ValueError(f"Invalid structure compatibility ({macro_key} + {beat_layer}): {reason}")
                beat_layer = None

        return StructureSelection(
            primary_macro=macro_key,
            beat_layer=beat_layer,
            framing=framing,
            candidates=candidates,
            selection_mode="MANUAL",
            overridden_by_user=True,
        )

    # 4. AUTO mode: Pick top eligible MACRO candidate
    eligible = [c for c in candidates if not c.disqualified]
    best_macro = eligible[0].structure_id if eligible else "three_act"

    # Select compatible secondary beat framework if available
    macro_defn = defs.get(best_macro)
    chosen_beat: Optional[str] = None
    if macro_defn and macro_defn.compatible_beat_frameworks:
        for bf in macro_defn.compatible_beat_frameworks:
            verdict, _ = DEFAULT_COMPATIBILITY_EVALUATOR.check_macro_beat_verdict(best_macro, bf)
            if verdict.value == "ALLOW":
                chosen_beat = bf
                break

    return StructureSelection(
        primary_macro=best_macro,
        beat_layer=chosen_beat,
        framing=framing,
        candidates=candidates,
        selection_mode="AUTO",
        overridden_by_user=False,
    )

