"""Narrative Sufficiency Gate measuring dramatic shape satisfaction before downstream handoff."""
from __future__ import annotations
from typing import List, Optional, Tuple, Literal

from ..domain import WorldState
from ..story.models import (
    StoryBlueprint,
    BeatPressure,
    SufficiencyReport,
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
    ) -> SufficiencyReport:
        """Evaluate simulation against the blueprint and budget constraints."""
        required_beats = [b for b in blueprint.beats if getattr(b, "required", True)]
        satisfied_required = [b for b in required_beats if b.status == "SATISFIED"]
        all_required_satisfied = len(satisfied_required) == len(required_beats) and len(required_beats) > 0

        # Climax detection: any beat with dramatic function CLIMAX is satisfied
        climax_beats = [b for b in blueprint.beats if b.dramatic_function == "CLIMAX"]
        climax_detected = any(b.status == "SATISFIED" for b in climax_beats)
        if not climax_beats and any(b.status == "SATISFIED" for b in blueprint.beats if b.dramatic_function in ("CRISIS", "REVERSAL")):
            climax_detected = True

        # Arc detection: at least one character experienced belief/relationship change or completed goal
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

        if not arc_detected and len(world.events) >= 5:
            arc_detected = True  # emergent activity occurred

        unsatisfied = [b for b in blueprint.beats if b.status == "UNSATISFIED"]
        pending = [b for b in blueprint.beats if b.status in ("PENDING", "PARTIAL")]

        # Case 1: All required beats satisfied & climax detected -> PROCEED
        if all_required_satisfied and climax_detected:
            return SufficiencyReport(
                required_beats_satisfied=True,
                climax_detected=True,
                arc_detected=arc_detected,
                unsatisfied_beats=unsatisfied,
                recommendation="PROCEED",
                reason="All required narrative beats satisfied and dramatic climax detected.",
            )

        # Case 2: Hard tick cap reached
        if current_tick >= hard_cap_ticks:
            if all_required_satisfied:
                return SufficiencyReport(
                    required_beats_satisfied=True,
                    climax_detected=climax_detected,
                    arc_detected=arc_detected,
                    unsatisfied_beats=unsatisfied,
                    recommendation="PROCEED",
                    reason="Hard tick cap reached with required beats satisfied.",
                )
            else:
                return SufficiencyReport(
                    required_beats_satisfied=False,
                    climax_detected=climax_detected,
                    arc_detected=arc_detected,
                    unsatisfied_beats=unsatisfied,
                    recommendation="HALT_INSUFFICIENT",
                    reason=f"Hard tick cap ({hard_cap_ticks}) reached without satisfying required beats.",
                )

        # Case 3: Need more time and budget extension is possible -> ADJUST_PRESSURE_AND_CONTINUE
        # Triggered when current budget expired, but hard cap allows extension
        if current_tick >= current_budget_ticks:
            if current_budget_ticks < hard_cap_ticks:
                ext = min(self.extension_increment_ticks, hard_cap_ticks - current_budget_ticks)
                if ext > 0:
                    return SufficiencyReport(
                        required_beats_satisfied=all_required_satisfied,
                        climax_detected=climax_detected,
                        arc_detected=arc_detected,
                        unsatisfied_beats=unsatisfied,
                        recommendation="ADJUST_PRESSURE_AND_CONTINUE",
                        reason=f"Narrative pacing behind target. Extending tick budget by {ext} ticks up to cap {hard_cap_ticks}.",
                    )
            # Budget exhausted and cannot extend
            return SufficiencyReport(
                required_beats_satisfied=all_required_satisfied,
                climax_detected=climax_detected,
                arc_detected=arc_detected,
                unsatisfied_beats=unsatisfied,
                recommendation="HALT_INSUFFICIENT",
                reason=f"Budget exhausted ({current_budget_ticks} ticks) without satisfying required beats.",
            )

        # Case 4: Beats currently pending within active window -> CONTINUE
        return SufficiencyReport(
            required_beats_satisfied=all_required_satisfied,
            climax_detected=climax_detected,
            arc_detected=arc_detected,
            unsatisfied_beats=unsatisfied,
            recommendation="CONTINUE",
            reason=f"{len(pending)} beats currently pending within active simulation window.",
        )
