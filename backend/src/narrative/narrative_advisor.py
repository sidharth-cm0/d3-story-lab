"""Narrative Advisor for D3 Story Lab.

Translates abstract NarrativeAnalysisResult and Genome patterns into explainable,
advisory NarrativeRecommendations.

CRITICAL INVARIANTS:
1. STRUCTURE WITHOUT PUPPETRY:
   - Recommendations describe WORLD PRESSURE and DRAMATIC OPPORTUNITY only.
   - Recommendations NEVER dictate character choices, dialogue, or actions.
   - canonical_mutation_allowed is strictly False on every recommendation.
2. EXPLAINABILITY:
   - Every recommendation provides explicit rationale, matched genome pattern IDs,
     related canonical event IDs, and projected dramatic effect.
"""

from __future__ import annotations
import uuid
from typing import List, Optional, Dict, Any, Set

from ..domain.story_structure import StoryBlueprint
from ..domain.narrative_genome import (
    NarrativeAnalysisResult,
    NarrativeRecommendation,
    DramaticFunction,
    InformationPattern,
)
from .genome_store import NarrativeGenomeRepository, LocalJsonGenomeRepository


class NarrativeAdvisor:
    """Generates explainable dramatic pressure recommendations from narrative analysis."""

    def __init__(self, repository: Optional[NarrativeGenomeRepository] = None):
        self.repository = repository or LocalJsonGenomeRepository()

    def advise(
        self,
        analysis: NarrativeAnalysisResult,
        blueprint: Optional[StoryBlueprint] = None,
        world: Optional[Any] = None,
        director: Optional[Any] = None,
        executed_recommendation_ids: Optional[Set[str]] = None,
    ) -> List[NarrativeRecommendation]:
        """Synthesize 0..N explainable dramatic recommendations grounded in analysis."""
        recommendations: List[NarrativeRecommendation] = []
        pacing = analysis.pacing_assessment
        tension_lvl = pacing.get("tension_level", 0.0)

        # 0. Identify previously executed recommendations to prevent duplicate loops
        past_executed_ids: Set[str] = set(executed_recommendation_ids or set())
        if world and hasattr(world, "events"):
            for ev in world.events.values():
                rec_id = ev.metadata.get("recommendation_id")
                if rec_id:
                    past_executed_ids.add(rec_id)

        # Director constraint checking
        director_counter_conditions: List[str] = []
        director_limitations: List[str] = []
        if director:
            cur_tick = getattr(world, "current_tick", 0) if world else 0
            if cur_tick < 2:
                director_counter_conditions.append(
                    f"Simulation is in initial scene establishment period (tick {cur_tick}); Director will block interventions."
                )
            if hasattr(director, "is_in_cooldown") and director.is_in_cooldown(cur_tick):
                director_counter_conditions.append(
                    f"Director cooldown active until tick {director.last_intervention_tick + director.min_ticks_between_interventions}."
                )
            if hasattr(director, "interventions_history") and len(director.interventions_history) >= getattr(director, "max_interventions_total", 5):
                director_limitations.append(
                    f"Director intervention budget exhausted ({len(director.interventions_history)}/{director.max_interventions_total})."
                )

        # 1. Check for Concealed Information / Dramatic Irony (Pattern NG-001, NG-002, NG-012)
        irony_items = [
            item for item in analysis.information_state
            if item.get("pattern") in (InformationPattern.DRAMATIC_IRONY.value, InformationPattern.CONCEALMENT.value)
        ]
        rec1_id = f"rec_{analysis.id}_reveal_clue"
        if irony_items and rec1_id not in past_executed_ids:
            item = irony_items[0]
            matched_patterns = self.repository.search(
                dramatic_function=DramaticFunction.REVELATION,
                query="concealed information revelation",
                limit=2,
            )
            matched_ids = [p.id for p in matched_patterns] or ["NG-001", "NG-002"]

            holder = item.get("holder_id")
            unaware = item.get("unaware_character_ids", [])
            rel_chars = [holder] + unaware if holder else unaware

            recommendations.append(
                NarrativeRecommendation(
                    id=rec1_id,
                    source_analysis_id=analysis.id,
                    recommendation_type="opportunity_creation",
                    observed_issue=f"Active secret '{item.get('secret_id')}' remains concealed while characters {rel_chars} occupy adjacent space.",
                    dramatic_goal="Create an environmental catalyst for concealed information to become discoverable.",
                    rationale=(
                        f"Active secret '{item.get('secret_id')}' is concealed while characters {rel_chars} "
                        f"occupy adjacent space. Matched pattern {matched_ids[0]} suggests discovery catalyst."
                    ),
                    target_pressure="REVEAL_CLUE",
                    relevant_character_ids=[c for c in rel_chars if c],
                    related_event_ids=analysis.event_ids[-3:],
                    matched_genome_ids=matched_ids,
                    expected_narrative_effect="Provides characters with physical clues to uncover or confront hidden truth.",
                    priority=0.75,
                    confidence=1.0,
                    relevance_score=0.85,
                    counter_conditions=list(director_counter_conditions),
                    limitations=["Clues must be placed in accessible locations without forcing character pickup.", *director_limitations],
                    canonical_mutation_allowed=False,
                )
            )

        # 2. Check for Stalled Relationships or Stagnation (Pattern NG-004, NG-010)
        rec2_id = f"rec_{analysis.id}_deadline"
        if pacing.get("pacing_state") in ("stalled", "idle") and rec2_id not in past_executed_ids:
            matched_patterns = self.repository.search(
                dramatic_function=DramaticFunction.CRISIS,
                query="deadline urgency constraint",
                limit=2,
            )
            matched_ids = [p.id for p in matched_patterns] or ["NG-004"]

            stalled_chars: List[str] = []
            for conf in analysis.active_conflicts:
                stalled_chars.extend([conf.get("source_character_id", ""), conf.get("target_character_id", "")])
            stalled_chars = sorted(list(set(c for c in stalled_chars if c)))

            recommendations.append(
                NarrativeRecommendation(
                    id=rec2_id,
                    source_analysis_id=analysis.id,
                    recommendation_type="pacing_acceleration",
                    observed_issue=f"Pacing flagged as '{pacing.get('pacing_state')}' with {pacing.get('stalled_relationships_count', 0)} stalled relationship(s).",
                    dramatic_goal="Apply external time pressure to resolve interpersonal stagnation.",
                    rationale=(
                        f"Simulation pacing is flagged as '{pacing.get('pacing_state')}' with {pacing.get('stalled_relationships_count', 0)} "
                        f"stalled relationship(s). Matched pattern {matched_ids[0]} suggests introducing temporal urgency."
                    ),
                    target_pressure="ANNOUNCE_DEADLINE",
                    relevant_character_ids=stalled_chars,
                    related_event_ids=analysis.event_ids[-3:],
                    matched_genome_ids=matched_ids,
                    expected_narrative_effect="Forces autonomous agents to prioritize decisive choices over idle waiting.",
                    priority=0.85,
                    confidence=1.0,
                    relevance_score=0.95,
                    counter_conditions=list(director_counter_conditions),
                    limitations=["Time pressure cannot puppet character responses.", *director_limitations],
                    canonical_mutation_allowed=False,
                )
            )

        # 3. Check for Overheated Tension (Pattern NG-009 Tension Release)
        rec3_id = f"rec_{analysis.id}_decompression"
        if (pacing.get("pacing_state") == "overheated" or tension_lvl >= 0.85) and rec3_id not in past_executed_ids:
            matched_patterns = self.repository.search(
                dramatic_function=DramaticFunction.TRANSITION,
                query="tension release decompression",
                limit=2,
            )
            matched_ids = [p.id for p in matched_patterns] or ["NG-009"]

            recommendations.append(
                NarrativeRecommendation(
                    id=rec3_id,
                    source_analysis_id=analysis.id,
                    recommendation_type="tension_modulation",
                    observed_issue=f"Dramatic tension at near-peak ceiling ({tension_lvl:.2f}) without narrative release.",
                    dramatic_goal="Allow an interval of calm or physical transition following peak tension.",
                    rationale=(
                        f"Unresolved dramatic tension has reached {tension_lvl:.2f} (near ceiling). "
                        f"Matched pattern {matched_ids[0]} advises a brief decompression interval to prevent dramatic numbness."
                    ),
                    target_pressure="QUIET_INTERVAL",
                    relevant_character_ids=[],
                    related_event_ids=analysis.event_ids[-2:],
                    matched_genome_ids=matched_ids,
                    expected_narrative_effect="Allows characters to process recent dramatic revelations and re-anchor objectives.",
                    priority=0.60,
                    confidence=1.0,
                    relevance_score=0.75,
                    counter_conditions=list(director_counter_conditions),
                    limitations=["Decompression should not prematurely collapse ongoing investigative momentum.", *director_limitations],
                    canonical_mutation_allowed=False,
                )
            )

        # 4. Check for Unresolved Competing Goals (Pattern NG-003, NG-005, NG-010)
        rec4_id = f"rec_{analysis.id}_obstacle"
        if analysis.active_conflicts and not recommendations and rec4_id not in past_executed_ids:
            top_conf = analysis.active_conflicts[0]
            matched_patterns = self.repository.search(
                dramatic_function=DramaticFunction.CONFRONTATION,
                query="competing goals relationship test",
                limit=2,
            )
            matched_ids = [p.id for p in matched_patterns] or ["NG-003", "NG-010"]

            c_a = top_conf.get("source_character_id", "")
            c_b = top_conf.get("target_character_id", "")
            chars = [c for c in [c_a, c_b] if c]

            recommendations.append(
                NarrativeRecommendation(
                    id=rec4_id,
                    source_analysis_id=analysis.id,
                    recommendation_type="obstacle_injection",
                    observed_issue=f"Active conflict deadlock ({top_conf.get('intensity', 0):.2f}) between {c_a} and {c_b}.",
                    dramatic_goal="Introduce an environmental obstacle that tests the existing deadlock.",
                    rationale=(
                        f"High-intensity conflict ({top_conf.get('intensity', 0):.2f}) active between {c_a} and {c_b}. "
                        f"Matched pattern {matched_ids[0]} advises introducing external constraint."
                    ),
                    target_pressure="INTRODUCE_OBSTACLE",
                    relevant_character_ids=chars,
                    related_event_ids=analysis.event_ids[-3:],
                    matched_genome_ids=matched_ids,
                    expected_narrative_effect="Compels characters to adapt their strategies or test mutual alliances.",
                    priority=0.70,
                    confidence=1.0,
                    relevance_score=0.80,
                    counter_conditions=list(director_counter_conditions),
                    limitations=["Obstacles must respect spatial reachability.", *director_limitations],
                    canonical_mutation_allowed=False,
                )
            )

        # Ensure recommendation genome IDs are also tracked on the analysis result
        all_matched_ids: Set[str] = set()
        for rec in recommendations:
            all_matched_ids.update(rec.matched_genome_ids)
        analysis.matched_genome_ids = sorted(list(all_matched_ids))

        return recommendations
