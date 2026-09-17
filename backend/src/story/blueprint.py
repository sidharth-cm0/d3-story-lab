"""Story Blueprint compiler and symbolic role reference resolution for D3 Story Lab."""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple, Any

from .models import (
    DramaticFunction,
    DirectorIntervention,
    PredicateClause,
    PredicateSpec,
    StoryStructureDefinition,
    StructureSelection,
    CanonFact,
    NarrativeIntent,
    StoryRoleBindings,
    BeatPressure,
    StoryBlueprint,
)
from .loader import get_structure_registry

logger = logging.getLogger(__name__)

# §B.5 Escalation ladders keyed by DramaticFunction
# Asymmetry is intentional: pressuring toward an obstacle is legitimate world-shaping;
# pressuring toward a specific discovery/resolution is puppetry.
DEFAULT_ESCALATION_LADDERS: Dict[DramaticFunction, List[DirectorIntervention]] = {
    "INCITING_INCIDENT": ["REVEAL_CLUE", "ENVIRONMENTAL_EVENT"],
    "ESCALATION": ["INTRODUCE_OBSTACLE", "INCREASE_TIME_PRESSURE"],
    "REVERSAL": ["REVEAL_CLUE", "INTRODUCE_OBSTACLE"],
    "CRISIS": ["ANNOUNCE_DEADLINE", "INCREASE_TIME_PRESSURE"],
    "CLIMAX": ["INCREASE_TIME_PRESSURE", "ENVIRONMENTAL_EVENT"],
    "CONFRONTATION": ["CHANGE_DOOR_STATE", "MOVE_NPC"],
    # DISCOVERY, REVELATION, RESOLUTION, SETUP: deliberately empty
    "DISCOVERY": [],
    "REVELATION": [],
    "RESOLUTION": [],
    "SETUP": [],
    "INVESTIGATION": [],
    "NEGOTIATION": [],
    "CHASE": ["INCREASE_TIME_PRESSURE"],
}

SYMBOLIC_ROLE_MAP = {
    "central_proposition": "central_proposition_id",
    "focal_object": "focal_object_id",
    "protagonist": "protagonist_character_id",
    "antagonist": "antagonist_character_id",
}


def resolve_predicate_clause(
    clause: PredicateClause,
    bindings: StoryRoleBindings,
) -> Optional[PredicateClause]:
    """Resolve symbolic role references in a PredicateClause against StoryRoleBindings.
    
    If any reference cannot be resolved, returns None so it can be dropped cleanly.
    """
    data = clause.model_dump()
    subj = data.get("subject")
    obj = data.get("object")
    char = data.get("character")

    # Resolve subject if symbolic
    if subj in SYMBOLIC_ROLE_MAP:
        bound = getattr(bindings, SYMBOLIC_ROLE_MAP[subj], None)
        if not bound:
            logger.warning(f"Unresolvable symbolic subject '{subj}' in clause {clause.type}")
            return None
        data["subject"] = bound

    # Resolve object if symbolic
    if obj in SYMBOLIC_ROLE_MAP:
        bound = getattr(bindings, SYMBOLIC_ROLE_MAP[obj], None)
        if not bound:
            logger.warning(f"Unresolvable symbolic object '{obj}' in clause {clause.type}")
            return None
        data["object"] = bound

    # Resolve character if symbolic
    if char in SYMBOLIC_ROLE_MAP:
        bound = getattr(bindings, SYMBOLIC_ROLE_MAP[char], None)
        if not bound:
            logger.warning(f"Unresolvable symbolic character '{char}' in clause {clause.type}")
            return None
        data["character"] = bound

    return PredicateClause.model_validate(data)


def resolve_predicate_spec(
    spec: PredicateSpec,
    bindings: StoryRoleBindings,
) -> Tuple[PredicateSpec, bool]:
    """Resolve symbolic role references across all clauses in a PredicateSpec.
    
    Returns:
        (resolved_spec, is_unevaluable)
    """
    if spec.any_of is not None:
        resolved_clauses: List[PredicateClause] = []
        for c in spec.any_of:
            res = resolve_predicate_clause(c, bindings)
            if res is not None:
                resolved_clauses.append(res)
        if not resolved_clauses:
            # Dropping clauses emptied the any_of spec -> unevaluable
            return PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED")]), True
        return PredicateSpec(any_of=resolved_clauses), False

    elif spec.all_of is not None:
        resolved_clauses = []
        for c in spec.all_of:
            res = resolve_predicate_clause(c, bindings)
            if res is not None:
                resolved_clauses.append(res)
        if not resolved_clauses or len(resolved_clauses) < len(spec.all_of):
            # If all_of lost clauses or is empty, mark unevaluable
            return PredicateSpec(all_of=resolved_clauses or [PredicateClause(type="GOAL_ADOPTED")]), True
        return PredicateSpec(all_of=resolved_clauses), False

    return spec, False


def compile_blueprint(
    structure_selection: StructureSelection,
    role_bindings: Optional[StoryRoleBindings] = None,
    canon_facts: Optional[List[CanonFact]] = None,
    intent: Optional[NarrativeIntent] = None,
    definitions: Optional[Dict[str, StoryStructureDefinition]] = None,
) -> StoryBlueprint:
    """Compile a complete StoryBlueprint from structure selection and role bindings.
    
    Gracefully degrades when symbolic references cannot be resolved.
    """
    defs = definitions if definitions is not None else get_structure_registry()
    bindings = role_bindings or StoryRoleBindings()
    canon = canon_facts or []
    narrative_intent = intent or NarrativeIntent()

    # Get MACRO definition
    macro_id = structure_selection.primary_macro
    macro_def = defs.get(macro_id)
    if not macro_def:
        raise ValueError(f"Primary macro structure '{macro_id}' not found in registry")

    beats: List[BeatPressure] = []

    # Compile beats from MACRO structure
    for beat_spec in macro_def.beats:
        resolved_spec, unevaluable = resolve_predicate_spec(beat_spec.satisfaction, bindings)
        ladder = list(DEFAULT_ESCALATION_LADDERS.get(beat_spec.dramatic_function, []))

        beat_pressure = BeatPressure(
            beat_id=beat_spec.id,
            dramatic_function=beat_spec.dramatic_function,
            target_window=beat_spec.window,
            satisfaction_predicate=resolved_spec,
            escalation_ladder=ladder,
            status="PENDING",
            deviation_note=None,
            unevaluable=unevaluable,
            required=beat_spec.required,
        )
        beats.append(beat_pressure)

    # If a secondary beat layer is selected, compile overlay beats
    if structure_selection.beat_layer and structure_selection.beat_layer in defs:
        beat_def = defs[structure_selection.beat_layer]
        for beat_spec in beat_def.beats:
            resolved_spec, unevaluable = resolve_predicate_spec(beat_spec.satisfaction, bindings)
            ladder = list(DEFAULT_ESCALATION_LADDERS.get(beat_spec.dramatic_function, []))
            overlay_beat = BeatPressure(
                beat_id=f"{beat_def.id}_{beat_spec.id}",
                dramatic_function=beat_spec.dramatic_function,
                target_window=beat_spec.window,
                satisfaction_predicate=resolved_spec,
                escalation_ladder=ladder,
                status="PENDING",
                deviation_note=None,
                unevaluable=unevaluable,
                required=beat_spec.required,
            )
            beats.append(overlay_beat)

    return StoryBlueprint(
        canon=canon,
        intent=narrative_intent,
        beats=beats,
        structure=structure_selection,
        role_bindings=bindings,
    )
