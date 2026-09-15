"""Structure Analyzer for D3 Story Lab.

Measures how closely the autonomous simulation fulfilled or organically deviated from
the Story Blueprint's soft beat expectations.

CRITICAL RULE: NO RETROACTIVE CANONICAL REWRITE
This analyzer is purely observational. It reads immutable Event History and never alters
historical events. Simulation agency to deviate is preserved as a virtue of emergent narrative.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from src.domain.story_structure import (
    StoryBlueprint,
    StoryStructureType,
)
from src.domain.event import Event


class BeatFulfillmentAssessment(BaseModel):
    """Observation of an individual expected beat's realization in simulation history."""
    model_config = ConfigDict(extra="ignore")

    beat_id: str
    beat_name: str
    expected_dramatic_function: str
    target_position_pct: float
    fulfilled: bool
    confidence_score: float = Field(..., description="Observational match score 0.0 - 1.0")
    matched_event_ids: List[str] = Field(default_factory=list)
    observation_notes: str


class StructureAnalysisReport(BaseModel):
    """Assessment of blueprint fulfillment vs organic narrative deviation."""
    model_config = ConfigDict(extra="ignore")

    primary_structure: StoryStructureType
    total_expected_beats: int
    fulfilled_beats_count: int
    deviated_beats_count: int
    overall_alignment_score: float = Field(..., description="Observational score 0 - 100")
    beat_assessments: List[BeatFulfillmentAssessment] = Field(default_factory=list)
    deviation_summary: str
    is_purely_observational: bool = True  # strictly read-only, never mutates canonical events


class StructureAnalyzer:
    """Analyzes immutable simulation events against a soft StoryBlueprint."""

    def analyze_fulfillment(
        self,
        blueprint: StoryBlueprint,
        events: List[Event],
        max_ticks: Optional[int] = None,
    ) -> StructureAnalysisReport:
        """Measure beat fulfillment and organic narrative deviations."""
        sorted_events = sorted(events, key=lambda e: (e.tick, e.id))
        total_ticks = max_ticks or (max((e.tick for e in sorted_events), default=1) if sorted_events else 1)
        total_ticks = max(1, total_ticks)

        assessments: List[BeatFulfillmentAssessment] = []
        fulfilled_count = 0

        for beat in blueprint.expected_beats:
            target_tick = int(beat.target_position_pct * total_ticks)
            # Window around target tick (+- 25% of total ticks or minimum 2 ticks)
            window = max(2, int(total_ticks * 0.25))
            min_t = max(0, target_tick - window)
            max_t = target_tick + window

            window_events = [e for e in sorted_events if min_t <= e.tick <= max_t]

            # Check if any event in window corresponds to expected function
            matched_ids = []
            func_lower = beat.expected_dramatic_function.lower()
            keywords = [w for w in func_lower.split() if len(w) > 4]

            for ev in window_events:
                desc = (ev.description or "").lower()
                matches = sum(1 for kw in keywords if kw in desc)
                if matches >= 1:
                    matched_ids.append(ev.id)

            if matched_ids:
                is_fulfilled = True
                confidence = min(1.0, 0.5 + (0.15 * len(matched_ids)))
                notes = f"Fulfilled via {len(matched_ids)} event(s) around tick {target_tick}."
                fulfilled_count += 1
            elif window_events:
                # Emergent deviation occurred in this beat window
                is_fulfilled = False
                confidence = 0.3
                notes = (
                    f"Organic deviation: Simulation progressed autonomously around tick {target_tick} "
                    f"with alternative character actions ({len(window_events)} events observed)."
                )
            else:
                is_fulfilled = False
                confidence = 0.0
                notes = f"No simulation activity recorded in target window (ticks {min_t}-{max_t})."

            assessments.append(
                BeatFulfillmentAssessment(
                    beat_id=beat.beat_id,
                    beat_name=beat.name,
                    expected_dramatic_function=beat.expected_dramatic_function,
                    target_position_pct=beat.target_position_pct,
                    fulfilled=is_fulfilled,
                    confidence_score=round(confidence, 2),
                    matched_event_ids=matched_ids,
                    observation_notes=notes,
                )
            )

        total_beats = len(blueprint.expected_beats)
        alignment_score = round((fulfilled_count / max(1, total_beats)) * 100.0, 1)
        deviated_count = total_beats - fulfilled_count

        if alignment_score >= 70.0:
            summary = (
                f"Strong dramatic alignment ({alignment_score}/100). The autonomous simulation fulfilled "
                f"{fulfilled_count} of {total_beats} blueprint beat expectations."
            )
        elif alignment_score >= 40.0:
            summary = (
                f"Moderate dramatic alignment with organic divergence ({alignment_score}/100). "
                f"Characters adhered to early setup but adapted autonomously, diverging in {deviated_count} beats."
            )
        else:
            summary = (
                f"High narrative emergence / deviation ({alignment_score}/100). "
                f"Autonomous character agency drove the sequence off the initial beat outline."
            )

        return StructureAnalysisReport(
            primary_structure=blueprint.primary_structure,
            total_expected_beats=total_beats,
            fulfilled_beats_count=fulfilled_count,
            deviated_beats_count=deviated_count,
            overall_alignment_score=alignment_score,
            beat_assessments=assessments,
            deviation_summary=summary,
            is_purely_observational=True,
        )
