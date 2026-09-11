"""Narrative evaluation and quantitative simulation metrics for D3 Story Lab."""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState
from src.domain.event import EventType
from src.narrative.observer import NarrativeEventSelection


class SimulationReport(BaseModel):
    """Quantitative report assessing emergent narrative quality."""
    model_config = ConfigDict(frozen=True)

    total_ticks: int
    total_events: int
    action_diversity_score: float = Field(ge=0.0, le=1.0)
    character_autonomy_ratio: float = Field(ge=0.0, le=1.0)
    tension_curve: List[float] = Field(default_factory=list)
    peak_tension: float = Field(ge=0.0, le=1.0)
    repetition_count: int = Field(ge=0)
    narrative_coherence_score: float = Field(ge=0.0, le=1.0)
    unique_locations_visited: int
    dialogue_ratio: float = Field(ge=0.0, le=1.0)
    repeated_action_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    wait_percentage: float = Field(default=0.0, ge=0.0, le=1.0)
    meaningful_interaction_count: int = Field(default=0, ge=0)
    information_discoveries: int = Field(default=0, ge=0)
    belief_changes_count: int = Field(default=0, ge=0)
    relationship_changes_count: int = Field(default=0, ge=0)

    # Narrative Coherence Pass additions
    semantic_repetition_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    new_information_count: int = Field(default=0, ge=0)
    goal_progress_events: int = Field(default=0, ge=0)
    contradiction_count: int = Field(default=0, ge=0)
    object_oscillation_count: int = Field(default=0, ge=0)
    location_consistency_errors: int = Field(default=0, ge=0)
    conversation_topic_repetition: float = Field(default=0.0, ge=0.0, le=1.0)
    scene_resolution_status: Optional[str] = Field(default=None)

    quality_warnings: List[str] = Field(default_factory=list)
    summary: str


class NarrativeEvaluator:
    """Computes objective and dramatic quality metrics on simulation runs."""

    def evaluate_simulation(
        self,
        world: WorldState,
        selection: NarrativeEventSelection,
    ) -> SimulationReport:
        events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        total_events = len(events)
        total_ticks = world.current_tick

        if total_events == 0:
            return SimulationReport(
                total_ticks=total_ticks,
                total_events=0,
                action_diversity_score=0.0,
                character_autonomy_ratio=1.0,
                tension_curve=[],
                peak_tension=0.0,
                repetition_count=0,
                narrative_coherence_score=0.0,
                unique_locations_visited=0,
                dialogue_ratio=0.0,
                repeated_action_rate=0.0,
                wait_percentage=0.0,
                meaningful_interaction_count=0,
                information_discoveries=0,
                belief_changes_count=0,
                relationship_changes_count=0,
                semantic_repetition_rate=0.0,
                new_information_count=0,
                goal_progress_events=0,
                contradiction_count=0,
                object_oscillation_count=0,
                location_consistency_errors=0,
                conversation_topic_repetition=0.0,
                scene_resolution_status=None,
                quality_warnings=["WARNING: Empty simulation trace with 0 events."],
                summary="Simulation yielded zero events.",
            )

        # 1. Action type counts & diversity (Shannon entropy normalized)
        type_counts: Dict[str, int] = {}
        wait_events = 0
        meaningful_count = 0
        info_discoveries = 0

        for ev in events:
            t = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
            type_counts[t] = type_counts.get(t, 0) + 1

            desc_lower = ev.description.lower()
            if "wait" in desc_lower or ev.metadata.get("action") == "wait":
                wait_events += 1
            else:
                meaningful_count += 1

            if (
                ev.event_type in (EventType.CHARACTER_OBSERVED, EventType.BELIEF_FORMED)
                or "inspect" in desc_lower
                or "examined" in desc_lower
                or ev.metadata.get("fact_discovered")
            ):
                info_discoveries += 1

        k = len(type_counts)
        if k <= 1:
            diversity = 0.1
        else:
            entropy = -sum((cnt / total_events) * math.log2(cnt / total_events) for cnt in type_counts.values())
            max_entropy = math.log2(k)
            diversity = round(min(1.0, entropy / max_entropy), 3)

        # 2. Character autonomy vs Director interventions
        director_events = sum(1 for e in events if "incident_type" in e.metadata)
        character_events = total_events - director_events
        autonomy_ratio = round(character_events / total_events, 3)

        # 3. Tension curve & peak tension from narrative beats
        tension_curve = [b.dramatic_score for b in selection.filtered_beats]
        peak_tension = max(tension_curve) if tension_curve else 0.0

        # 4. Repetition detection
        repetition_count = 0
        for i in range(1, len(events)):
            if events[i].description == events[i - 1].description and events[i].event_type != EventType.CHARACTER_SPOKE:
                repetition_count += 1

        repeated_action_rate = round(repetition_count / max(1, total_events - 1), 3)
        wait_percentage = round(wait_events / total_events, 3)

        # 5. Unique locations visited
        locations_visited = len({e.location_id for e in events if e.location_id})

        # 6. Spoken dialogue ratio
        dialogue_events = sum(1 for e in events if e.event_type == EventType.CHARACTER_SPOKE)
        dialogue_ratio = round(dialogue_events / total_events, 3)

        # 7. Belief & relationship changes count
        belief_changes = len(world.beliefs)
        relationship_changes = sum(len(c.relationships) for c in world.characters.values())

        # 8. New Information & Facts
        new_info_count = len(world.facts)

        # 9. Goal progress events
        goal_progress_events = sum(
            1 for g in world.goals.values()
            if getattr(g, "progress", 0.0) > 0.0 or g.status.value in ("achieved", "completed")
        )

        # 10. Contradiction count
        contradiction_count = sum(
            1 for b in world.beliefs.values()
            if "lying" in b.statement.lower() or "contradict" in b.statement.lower()
        )

        # 11. Object oscillation count (take then drop in same room without move)
        oscillation_count = 0
        recent_pickups: Dict[str, Dict[str, Any]] = {}
        for ev in events:
            actor = ev.actor_ids[0] if ev.actor_ids else ""
            if ev.event_type == EventType.OBJECT_PICKED_UP:
                obj_id = ev.metadata.get("object_id")
                recent_pickups[f"{actor}:{obj_id}"] = {"loc": ev.location_id, "moved": False}
            elif ev.event_type == EventType.CHARACTER_MOVED:
                for k_pair in recent_pickups:
                    if k_pair.startswith(f"{actor}:"):
                        recent_pickups[k_pair]["moved"] = True
            elif ev.event_type == EventType.OBJECT_DROPPED:
                obj_id = ev.metadata.get("object_id")
                record = recent_pickups.get(f"{actor}:{obj_id}")
                if record and not record["moved"] and record["loc"] == ev.location_id:
                    oscillation_count += 1

        # 12. Spatial consistency check
        spatial_errors = 0
        actor_loc_track: Dict[str, str] = {}
        for ev in events:
            if ev.event_type == EventType.CHARACTER_MOVED:
                actor = ev.actor_ids[0] if ev.actor_ids else ""
                from_loc = ev.metadata.get("from_location")
                to_loc = ev.metadata.get("to_location")
                if actor in actor_loc_track:
                    if from_loc and actor_loc_track[actor] != from_loc:
                        spatial_errors += 1
                if to_loc:
                    actor_loc_track[actor] = to_loc

        # 13. Conversation topic repetition
        topic_repeats = 0
        last_topic_by_pair: Dict[str, str] = {}
        for ev in events:
            if ev.event_type == EventType.CHARACTER_SPOKE:
                speaker = ev.metadata.get("speaker_id", "")
                target = ev.metadata.get("target_id", "")
                topic = ev.metadata.get("topic", "")
                pair_key = f"{speaker}->{target}"
                if topic and last_topic_by_pair.get(pair_key) == topic:
                    topic_repeats += 1
                if topic:
                    last_topic_by_pair[pair_key] = topic

        conversation_topic_rep = round(topic_repeats / max(1, dialogue_events), 3)
        semantic_repetition_rate = round(max(repeated_action_rate, conversation_topic_rep), 3)

        # 14. Scene resolution status
        scene_resolution_status = None
        for g in world.goals.values():
            if g.status.value in ("achieved", "completed"):
                actor_name = world.characters[g.character_id].name if g.character_id in world.characters else g.character_id
                scene_resolution_status = f"ACHIEVED: {actor_name} resolved '{g.description}'"
                break

        # 15. Quality warnings
        quality_warnings: List[str] = []
        if wait_percentage > 0.25:
            quality_warnings.append(f"WARNING: High character passivity detected (WAIT rate: {wait_percentage * 100:.1f}%).")
        if semantic_repetition_rate > 0.25:
            quality_warnings.append(f"HIGH_SEMANTIC_REPETITION: Semantic repetition rate {semantic_repetition_rate * 100:.1f}%.")
        if oscillation_count > 0:
            quality_warnings.append(f"OBJECT_OSCILLATION: {oscillation_count} immediate drop cycles detected.")
        if goal_progress_events == 0 and total_ticks >= 10:
            quality_warnings.append("NO_GOAL_PROGRESS: No progress on active goals.")
        if new_info_count == 0 and total_ticks >= 5:
            quality_warnings.append("NO_INFORMATION_GAIN: Zero facts discovered.")
        if spatial_errors > 0:
            quality_warnings.append(f"SPATIAL_INCONSISTENCY: {spatial_errors} spatial inconsistencies detected.")

        # 16. Narrative coherence score
        coherence = (
            0.30
            + (0.20 * diversity)
            + (0.15 * min(1.0, len(selection.filtered_beats) / 3))
            + (0.15 * min(1.0, meaningful_count / max(1, total_events)))
            + (0.10 * min(1.0, new_info_count / 2))
            + (0.10 * min(1.0, goal_progress_events / max(1, len(world.goals))))
            - (0.15 * semantic_repetition_rate)
            - (0.20 * wait_percentage)
            - (0.20 * min(1.0, oscillation_count))
        )
        coherence_score = round(max(0.1, min(1.0, coherence)), 3)

        summary = (
            f"Evaluated {total_ticks} ticks ({total_events} events). "
            f"Diversity: {diversity}, Coherence: {coherence_score:.2f}, "
            f"Facts: {new_info_count}, Goals progressed: {goal_progress_events}, "
            f"Contradictions: {contradiction_count}, Oscillations: {oscillation_count}."
        )

        return SimulationReport(
            total_ticks=total_ticks,
            total_events=total_events,
            action_diversity_score=diversity,
            character_autonomy_ratio=autonomy_ratio,
            tension_curve=tension_curve,
            peak_tension=peak_tension,
            repetition_count=repetition_count,
            narrative_coherence_score=coherence_score,
            unique_locations_visited=locations_visited,
            dialogue_ratio=dialogue_ratio,
            repeated_action_rate=repeated_action_rate,
            wait_percentage=wait_percentage,
            meaningful_interaction_count=meaningful_count,
            information_discoveries=info_discoveries,
            belief_changes_count=belief_changes,
            relationship_changes_count=relationship_changes,
            semantic_repetition_rate=semantic_repetition_rate,
            new_information_count=new_info_count,
            goal_progress_events=goal_progress_events,
            contradiction_count=contradiction_count,
            object_oscillation_count=oscillation_count,
            location_consistency_errors=spatial_errors,
            conversation_topic_repetition=conversation_topic_rep,
            scene_resolution_status=scene_resolution_status,
            quality_warnings=quality_warnings,
            summary=summary,
        )
