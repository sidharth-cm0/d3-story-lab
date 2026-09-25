"""Narrative Sufficiency Gate measuring dramatic shape satisfaction before downstream handoff."""
from __future__ import annotations
from typing import List, Optional, Tuple, Literal

from ..domain import WorldState
from ..story.models import (
    StoryBlueprint,
    BeatPressure,
    SufficiencyReport,
    DramaticFunction,
)


class NarrativeSufficiencyGate:
    """Measures whether the emergent simulation has satisfied the StoryBlueprint.
    
    Evaluates:
    - Required beats satisfaction
    - Dramatic climax detection
    - Character arc detection
    Produces one of four recommendations:
    - CONTINUE
    - ADJUST_PRESSURE_AND_CONTINUE
    - PROCEED
    - HALT_INSUFFICIENT (legal outcome, never raises)
    """

    def __init__(
        self,
        extension_increment_ticks: int = 5,
    ):
        self.extension_increment_ticks = extension_increment_ticks

    def evaluate(
        self,
        blueprint: StoryBlueprint,
        world: WorldState,
        current_tick: int,
        current_budget_ticks: int,
        hard_cap_ticks: int,
        differ: Optional[Any] = None,
        events: Optional[List[Any]] = None,
    ) -> SufficiencyReport:
        """Evaluate simulation against the blueprint, budget constraints, and dramatic signals."""
        from .dramatic_signals import extract_dramatic_signals

        signals = extract_dramatic_signals(
            world=world,
            events=events,
            differ=differ,
        )

        conflict_escalated = signals.has_major_conflict_escalation
        relationship_threshold_crossed = signals.has_relationship_threshold_crossing
        belief_or_secret_revealed = signals.has_secret_revelation or signals.has_belief_flip
        arc_movement_detected = signals.has_arc_movement
        has_unresolved_tension = signals.unresolved_tension_level > 0.0 or len(signals.unresolved_conflicts) > 0

        beats_list = getattr(blueprint, "beats", None) or getattr(blueprint, "expected_beats", [])
        required_beats = [b for b in beats_list if getattr(b, "required", True)]
        satisfied_required = [b for b in required_beats if getattr(b, "status", None) == "SATISFIED"]
        all_required_satisfied = len(satisfied_required) == len(required_beats) and len(required_beats) > 0

        # Climax detection: any beat with dramatic function CLIMAX is satisfied
        climax_beats = [
            b for b in beats_list
            if getattr(b, "dramatic_function", None) in ("CLIMAX", DramaticFunction.CLIMAX)
        ]
        climax_detected = any(getattr(b, "status", None) == "SATISFIED" for b in climax_beats)
        if not climax_beats and any(
            getattr(b, "status", None) == "SATISFIED"
            for b in beats_list
            if getattr(b, "dramatic_function", None) in ("CRISIS", "REVERSAL", DramaticFunction.CRISIS, DramaticFunction.REVERSAL)
        ):
            climax_detected = True

        # Arc detection: goal completion, relationship threshold, archetype movement, or mental shift
        arc_detected = False
        for goal in world.goals.values():
            status_name = goal.status.name if hasattr(goal.status, "name") else str(goal.status)
            if status_name in ("ACHIEVED", "COMPLETED"):
                arc_detected = True
                break

        if not arc_detected:
            for char in world.characters.values():
                rels = char.relationships.values() if isinstance(char.relationships, dict) else char.relationships
                for rel in rels:
                    if abs(getattr(rel, "affinity", 0.0)) > 0.1:
                        arc_detected = True
                        break
                if arc_detected:
                    break

        if not arc_detected and (arc_movement_detected or relationship_threshold_crossed or belief_or_secret_revealed):
            arc_detected = True

        if not arc_detected and len(world.events) >= 5:
            arc_detected = True  # emergent activity occurred

        unsatisfied = [b for b in beats_list if getattr(b, "status", None) == "UNSATISFIED"]
        pending = [b for b in beats_list if getattr(b, "status", None) in ("PENDING", "PARTIAL")]


        # Case 1: All required beats satisfied & climax detected -> PROCEED
        if all_required_satisfied and climax_detected:
            cliffhanger_note = " with compelling unresolved dramatic tension (cliffhanger/open thread)." if has_unresolved_tension else "."
            return SufficiencyReport(
                required_beats_satisfied=True,
                climax_detected=True,
                arc_detected=arc_detected,
                unsatisfied_beats=unsatisfied,
                recommendation="PROCEED",
                reason=f"All required narrative beats satisfied and dramatic climax detected{cliffhanger_note}",
                conflict_escalated=conflict_escalated,
                relationship_threshold_crossed=relationship_threshold_crossed,
                belief_or_secret_revealed=belief_or_secret_revealed,
                arc_movement_detected=arc_movement_detected,
                has_unresolved_tension=has_unresolved_tension,
                dramatic_signals=signals.model_dump(),
            )

        # Case 2: Hard tick cap reached
        if current_tick >= hard_cap_ticks:
            if all_required_satisfied:
                cliffhanger_note = " with unresolved tension maintained." if has_unresolved_tension else "."
                return SufficiencyReport(
                    required_beats_satisfied=True,
                    climax_detected=climax_detected,
                    arc_detected=arc_detected,
                    unsatisfied_beats=unsatisfied,
                    recommendation="PROCEED",
                    reason=f"Hard tick cap reached with required beats satisfied{cliffhanger_note}",
                    conflict_escalated=conflict_escalated,
                    relationship_threshold_crossed=relationship_threshold_crossed,
                    belief_or_secret_revealed=belief_or_secret_revealed,
                    arc_movement_detected=arc_movement_detected,
                    has_unresolved_tension=has_unresolved_tension,
                    dramatic_signals=signals.model_dump(),
                )
            elif climax_detected and arc_detected and (conflict_escalated or relationship_threshold_crossed):
                return SufficiencyReport(
                    required_beats_satisfied=False,
                    climax_detected=climax_detected,
                    arc_detected=arc_detected,
                    unsatisfied_beats=unsatisfied,
                    recommendation="PROCEED",
                    reason="Hard tick cap reached with emergent dramatic climax, character arc movement, and significant tension escalation.",
                    conflict_escalated=conflict_escalated,
                    relationship_threshold_crossed=relationship_threshold_crossed,
                    belief_or_secret_revealed=belief_or_secret_revealed,
                    arc_movement_detected=arc_movement_detected,
                    has_unresolved_tension=has_unresolved_tension,
                    dramatic_signals=signals.model_dump(),
                )
            else:
                return SufficiencyReport(
                    required_beats_satisfied=False,
                    climax_detected=climax_detected,
                    arc_detected=arc_detected,
                    unsatisfied_beats=unsatisfied,
                    recommendation="HALT_INSUFFICIENT",
                    reason=f"Hard tick cap ({hard_cap_ticks}) reached without satisfying required beats.",
                    conflict_escalated=conflict_escalated,
                    relationship_threshold_crossed=relationship_threshold_crossed,
                    belief_or_secret_revealed=belief_or_secret_revealed,
                    arc_movement_detected=arc_movement_detected,
                    has_unresolved_tension=has_unresolved_tension,
                    dramatic_signals=signals.model_dump(),
                )

        # Case 3: Need more time and budget extension is possible -> ADJUST_PRESSURE_AND_CONTINUE
        # Triggered when current budget expired, but hard cap allows extension
        if current_tick >= current_budget_ticks:
            if current_budget_ticks < hard_cap_ticks:
                ext = min(self.extension_increment_ticks, hard_cap_ticks - current_budget_ticks)
                if ext > 0:
                    drama_factors = []
                    if conflict_escalated:
                        drama_factors.append("active conflict escalation")
                    if relationship_threshold_crossed:
                        drama_factors.append("relationship threshold crossings")
                    if not drama_factors:
                        drama_factors.append("narrative pacing behind target")
                    reason_desc = f"Extending tick budget by {ext} ticks up to cap {hard_cap_ticks} due to {', '.join(drama_factors)}."
                    return SufficiencyReport(
                        required_beats_satisfied=all_required_satisfied,
                        climax_detected=climax_detected,
                        arc_detected=arc_detected,
                        unsatisfied_beats=unsatisfied,
                        recommendation="ADJUST_PRESSURE_AND_CONTINUE",
                        reason=reason_desc,
                        conflict_escalated=conflict_escalated,
                        relationship_threshold_crossed=relationship_threshold_crossed,
                        belief_or_secret_revealed=belief_or_secret_revealed,
                        arc_movement_detected=arc_movement_detected,
                        has_unresolved_tension=has_unresolved_tension,
                        dramatic_signals=signals.model_dump(),
                    )
            # Budget exhausted and cannot extend
            return SufficiencyReport(
                required_beats_satisfied=all_required_satisfied,
                climax_detected=climax_detected,
                arc_detected=arc_detected,
                unsatisfied_beats=unsatisfied,
                recommendation="HALT_INSUFFICIENT",
                reason=f"Budget exhausted ({current_budget_ticks} ticks) without satisfying required beats.",
                conflict_escalated=conflict_escalated,
                relationship_threshold_crossed=relationship_threshold_crossed,
                belief_or_secret_revealed=belief_or_secret_revealed,
                arc_movement_detected=arc_movement_detected,
                has_unresolved_tension=has_unresolved_tension,
                dramatic_signals=signals.model_dump(),
            )

        # Case 4: Beats currently pending within active window -> CONTINUE
        return SufficiencyReport(
            required_beats_satisfied=all_required_satisfied,
            climax_detected=climax_detected,
            arc_detected=arc_detected,
            unsatisfied_beats=unsatisfied,
            recommendation="CONTINUE",
            reason=f"{len(pending)} beats currently pending within active simulation window.",
            conflict_escalated=conflict_escalated,
            relationship_threshold_crossed=relationship_threshold_crossed,
            belief_or_secret_revealed=belief_or_secret_revealed,
            arc_movement_detected=arc_movement_detected,
            has_unresolved_tension=has_unresolved_tension,
            dramatic_signals=signals.model_dump(),
        )
