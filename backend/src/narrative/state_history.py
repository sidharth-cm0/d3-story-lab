"""Character State History Reconstruction Engine for D3 Story Lab.

Reconstructs historical time-series for character metrics and pairwise relationships
through deterministic observation of the immutable EventLog and StateSnapshotDiffer.

CRITICAL INVARIANTS:
1. PURELY DERIVED & OBSERVATIONAL:
   - Never canonical source of truth.
   - Zero mutation of WorldState, Characters, Goals, Beliefs, or Relationships.
2. EVENT PROVENANCE MANDATORY:
   - Every non-baseline point representing a state change carries event_ids.
3. SPARSE BY DEFAULT:
   - Only emits baseline + significant change points unless dense sampling is requested.
4. CACHING & PERFORMANCE:
   - Cached per (project_id, character_id, metric, cache_token).
   - Invalidation is automatic when event count or simulation tick changes.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict

from ..domain.world import WorldState, Character
from ..domain.event import Event, EventType
from ..domain.goal import GoalStatus
from ..domain.character_history import (
    HistoryPoint,
    CharacterHistorySeries,
    CharacterHistoryReport,
)
from ..simulation.differ import StateSnapshotDiffer, WorldSnapshot
from .arc_tracker import CharacterArcTracker
from .archetype_analyzer import ArchetypeTrajectoryAnalyzer


RELATIONSHIP_METRIC_NAMES = {
    "trust",
    "affinity",
    "affection",
    "fear",
    "dependency",
    "respect",
    "resentment",
    "suspicion",
    "power_imbalance",
}

CHARACTER_METRIC_NAMES = {
    "goal_progress",
    "goal_pressure",
    "belief_confidence",
    "emotional_valence",
    "fear",
    "anger",
    "happiness",
    "trust",
    "curiosity",
    "knowledge_count",
    "archetype_alignment",
    "arc_stage",
}


class CharacterStateHistoryReconstructor:
    """Deterministic history reconstructor for character state metrics and relationship dimensions."""

    # In-memory cache: (project_id, char_id, metric, target_id, is_sparse, event_count, current_tick) -> CharacterHistorySeries
    _cache: Dict[Tuple[str, str, str, Optional[str], bool, int, int], CharacterHistorySeries] = {}

    @classmethod
    def clear_cache(cls, project_id: Optional[str] = None) -> None:
        """Clear cached history series, optionally scoped to a project."""
        if project_id is None:
            cls._cache.clear()
        else:
            keys_to_remove = [k for k in cls._cache.keys() if k[0] == project_id]
            for k in keys_to_remove:
                cls._cache.pop(k, None)

    @classmethod
    def reconstruct_relationship_series(
        cls,
        world: WorldState,
        char_a_id: str,
        char_b_id: str,
        dimension: str,
        project_id: str = "default",
        sparse: bool = True,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CharacterHistorySeries:
        """Reconstruct the historical time-series for a single pairwise relationship dimension."""
        cache_key = (
            project_id,
            char_a_id,
            dimension,
            char_b_id,
            sparse,
            len(world.events),
            world.current_tick,
        )
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        if differ is None:
            differ = StateSnapshotDiffer(world)

        rel = world.get_relationship(char_a_id, char_b_id)
        current_val = getattr(rel, dimension, 0.0) if rel else 0.0

        # 1. Determine baseline value at tick 0
        baseline_val = current_val
        if rel and rel.event_provenance and rel.event_provenance.get(dimension):
            prov_ids = set(rel.event_provenance[dimension])
            total_delta = 0.0
            for eid in prov_ids:
                ev = world.events.get(eid)
                if ev and f"delta_{dimension}" in ev.metadata:
                    total_delta += float(ev.metadata[f"delta_{dimension}"])
            baseline_val = round(max(-1.0, min(1.0, current_val - total_delta)), 2)
        elif 0 in differ.snapshots:
            snap_0 = differ.snapshots[0]
            if snap_0 and snap_0.relationship_dimensions:
                dims_0 = snap_0.relationship_dimensions.get((char_a_id, char_b_id)) or snap_0.relationship_dimensions.get((char_b_id, char_a_id))
                if dims_0 and dimension in dims_0:
                    baseline_val = dims_0[dimension]
        else:
            snap_0 = differ.get_or_create_snapshot(0, world)
            if snap_0 and snap_0.relationship_dimensions:
                dims_0 = snap_0.relationship_dimensions.get((char_a_id, char_b_id)) or snap_0.relationship_dimensions.get((char_b_id, char_a_id))
                if dims_0 and dimension in dims_0:
                    baseline_val = dims_0[dimension]

        # 2. Collect chronologically sorted events involving this relationship dimension
        sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        provenance_events_set: Set[str] = set()
        if rel and rel.event_provenance:
            provenance_events_set = set(rel.event_provenance.get(dimension, []))

        # Build raw points by tick
        tick_to_events: Dict[int, List[Event]] = defaultdict(list)
        for ev in sorted_events:
            is_relevant = False
            if ev.id in provenance_events_set:
                is_relevant = True
            elif ev.event_type == EventType.RELATIONSHIP_CHANGED and char_a_id in ev.actor_ids and char_b_id in ev.actor_ids:
                is_relevant = True
            elif f"delta_{dimension}" in ev.metadata and (char_a_id in ev.actor_ids or char_b_id in ev.actor_ids):
                is_relevant = True

            if is_relevant:
                tick_to_events[ev.tick].append(ev)

        raw_points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=round(baseline_val, 2),
                event_ids=[],
                label="Initial baseline",
                metadata={"dimension": dimension, "baseline": True},
            )
        ]

        # Interpolate or extract values across event ticks
        running_val = baseline_val
        all_event_ticks = sorted(tick_to_events.keys())

        for idx, t in enumerate(all_event_ticks):
            evts_at_t = tick_to_events[t]
            evt_ids = [e.id for e in evts_at_t]
            labels = [e.description for e in evts_at_t]

            # Try to read value from snapshot at tick t if available
            val_at_t = None
            if t in differ.snapshots:
                snap_t = differ.snapshots[t]
                if snap_t.relationship_dimensions:
                    dims_t = snap_t.relationship_dimensions.get((char_a_id, char_b_id)) or snap_t.relationship_dimensions.get((char_b_id, char_a_id))
                    if dims_t and dimension in dims_t:
                        val_at_t = dims_t[dimension]

            if val_at_t is None:
                # Check for explicit delta in event metadata
                delta_sum = 0.0
                has_delta = False
                for e in evts_at_t:
                    d_key = f"delta_{dimension}"
                    if d_key in e.metadata:
                        delta_sum += float(e.metadata[d_key])
                        has_delta = True

                if has_delta:
                    running_val = max(-1.0, min(1.0, running_val + delta_sum))
                    val_at_t = running_val
                elif idx == len(all_event_ticks) - 1:
                    # Final event reaches current value
                    val_at_t = current_val
                else:
                    # Step progression toward current value
                    fraction = (idx + 1) / len(all_event_ticks)
                    val_at_t = baseline_val + fraction * (current_val - baseline_val)

            running_val = round(val_at_t, 2)
            raw_points.append(
                HistoryPoint(
                    tick=t,
                    value=running_val,
                    event_ids=evt_ids,
                    label="; ".join(labels) if labels else f"Change in {dimension}",
                    metadata={"dimension": dimension, "event_count": len(evt_ids)},
                )
            )

        # 3. Apply Sparsity Filter
        filtered_points = cls._filter_points(raw_points, sparse=sparse, end_tick=world.current_tick)

        target_char = world.characters.get(char_b_id)
        target_name = target_char.name if target_char else char_b_id

        series = CharacterHistorySeries(
            character_id=char_a_id,
            target_character_id=char_b_id,
            metric=dimension,
            display_name=f"{dimension.replace('_', ' ').capitalize()} vs {target_name}",
            points=filtered_points,
            is_sparse=sparse,
            is_analytical_only=True,
        )

        cls._cache[cache_key] = series
        return series

    @classmethod
    def reconstruct_character_metric_series(
        cls,
        world: WorldState,
        character_id: str,
        metric: str,
        project_id: str = "default",
        sparse: bool = True,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CharacterHistorySeries:
        """Reconstruct historical time-series for an intrinsic character metric."""
        cache_key = (
            project_id,
            character_id,
            metric,
            None,
            sparse,
            len(world.events),
            world.current_tick,
        )
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        if differ is None:
            differ = StateSnapshotDiffer(world)

        char = world.characters.get(character_id)
        if not char:
            return CharacterHistorySeries(
                character_id=character_id,
                metric=metric,
                display_name=metric,
                points=[],
                is_sparse=sparse,
            )

        raw_points: List[HistoryPoint] = []
        display_name = metric.replace("_", " ").capitalize()

        if metric == "goal_progress":
            display_name = "Goal Progress"
            raw_points = cls._reconstruct_goal_progress(world, char, differ)
        elif metric == "goal_pressure":
            display_name = "Goal Pressure"
            raw_points = cls._reconstruct_goal_pressure(world, char, differ)
        elif metric == "belief_confidence":
            display_name = "Belief Confidence"
            raw_points = cls._reconstruct_belief_confidence(world, char, differ)
        elif metric in ("emotional_valence", "fear", "anger", "happiness", "trust", "curiosity"):
            display_name = f"Emotion: {metric.replace('_', ' ').capitalize()}"
            raw_points = cls._reconstruct_emotion_metric(world, char, metric, differ)
        elif metric == "knowledge_count":
            display_name = "Knowledge Acquisition"
            raw_points = cls._reconstruct_knowledge_acquisition(world, char)
        elif metric == "archetype_alignment":
            display_name = "Archetype Alignment"
            raw_points = cls._reconstruct_archetype_alignment(world, char, differ)
        elif metric == "arc_stage":
            display_name = "Character Arc Stage Transitions"
            raw_points = cls._reconstruct_arc_stage(world, char, differ)
        else:
            raw_points = [
                HistoryPoint(
                    tick=0,
                    value=0.0,
                    event_ids=[],
                    label=f"Baseline for {metric}",
                )
            ]

        filtered_points = cls._filter_points(raw_points, sparse=sparse, end_tick=world.current_tick)

        series = CharacterHistorySeries(
            character_id=character_id,
            target_character_id=None,
            metric=metric,
            display_name=display_name,
            points=filtered_points,
            is_sparse=sparse,
            is_analytical_only=True,
        )

        cls._cache[cache_key] = series
        return series

    @classmethod
    def reconstruct_trajectory_series(
        cls,
        world: WorldState,
        character_id: str,
        project_id: str = "default",
        sparse: bool = True,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> List[CharacterHistorySeries]:
        """Convenience method returning both archetype alignment and arc stage series."""
        s_arch = cls.reconstruct_character_metric_series(
            world, character_id, "archetype_alignment", project_id=project_id, sparse=sparse, differ=differ
        )
        s_arc = cls.reconstruct_character_metric_series(
            world, character_id, "arc_stage", project_id=project_id, sparse=sparse, differ=differ
        )
        return [s_arch, s_arc]

    @classmethod
    def reconstruct_character_history(
        cls,
        world: WorldState,
        character_id: str,
        metrics: Optional[List[str]] = None,
        target_character_id: Optional[str] = None,
        project_id: str = "default",
        sparse: bool = True,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CharacterHistoryReport:
        """Batch reconstruct multiple history series for a character into a comprehensive report."""
        if differ is None:
            differ = StateSnapshotDiffer(world)

        if not metrics:
            metrics = ["goal_pressure", "goal_progress", "belief_confidence", "emotional_valence"]
            if target_character_id:
                metrics.extend(["trust", "suspicion", "resentment"])

        series_dict: Dict[str, CharacterHistorySeries] = {}

        for m in metrics:
            if m in RELATIONSHIP_METRIC_NAMES:
                if target_character_id:
                    series_dict[m] = cls.reconstruct_relationship_series(
                        world,
                        character_id,
                        target_character_id,
                        dimension=m,
                        project_id=project_id,
                        sparse=sparse,
                        differ=differ,
                    )
            else:
                series_dict[m] = cls.reconstruct_character_metric_series(
                    world,
                    character_id,
                    metric=m,
                    project_id=project_id,
                    sparse=sparse,
                    differ=differ,
                )

        return CharacterHistoryReport(
            project_id=project_id,
            character_id=character_id,
            series=series_dict,
            generated_at_tick=world.current_tick,
            total_events_analyzed=len(world.events),
            is_observed_only=True,
        )

    # -------------------------------------------------------------------------
    # Internal Metric Reconstructors
    # -------------------------------------------------------------------------

    @classmethod
    def _reconstruct_goal_progress(
        cls,
        world: WorldState,
        char: Character,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct goal progress from initial state, progress ticks, and completion events."""
        char_goals = world.get_character_goals(char.id)
        if not char_goals:
            return [HistoryPoint(tick=0, value=0.0, event_ids=[], label="No active goals")]

        # Track primary or highest priority goal
        primary_goal = max(char_goals, key=lambda g: g.priority)
        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=0.0,
                event_ids=[],
                label=f"Goal adopted: '{primary_goal.description}'",
            )
        ]

        # Determine completion tick and event
        comp_tick = None
        comp_evts = []
        if primary_goal.status in (GoalStatus.COMPLETED, GoalStatus.ACHIEVED):
            ref_evt = getattr(primary_goal, "created_at_event", None)
            if ref_evt and ref_evt in world.events:
                comp_tick = world.events[ref_evt].tick
                comp_evts = [ref_evt]
            else:
                comp_matches = [
                    e for e in world.events.values()
                    if (e.metadata.get("goal_id") == primary_goal.id and e.metadata.get("goal_status") in ("completed", "achieved"))
                ]
                if comp_matches:
                    comp_tick = comp_matches[-1].tick
                    comp_evts = [comp_matches[-1].id]
                else:
                    actor_evts = [e for e in world.events.values() if char.id in e.actor_ids]
                    comp_tick = actor_evts[-1].tick if actor_evts else world.current_tick
                    comp_evts = [actor_evts[-1].id] if actor_evts else []

        # Intermediate progress tick
        if primary_goal.last_progress_tick and primary_goal.last_progress_tick > 0:
            prog_tick = primary_goal.last_progress_tick
            if comp_tick is None or prog_tick < comp_tick:
                evts = [e for e in world.events.values() if e.tick == prog_tick and (char.id in e.actor_ids or e.metadata.get("goal_id") == primary_goal.id)]
                evt_ids = [e.id for e in evts]
                desc = evts[0].description if evts else f"Progress on '{primary_goal.description}'"
                val = 0.8 if (primary_goal.status in (GoalStatus.COMPLETED, GoalStatus.ACHIEVED) and primary_goal.progress == 1.0) else round(primary_goal.progress, 2)
                points.append(
                    HistoryPoint(
                        tick=prog_tick,
                        value=val,
                        event_ids=evt_ids,
                        label=desc,
                    )
                )

        if comp_tick is not None:
            if comp_tick > points[-1].tick or points[-1].value < 1.0:
                points.append(
                    HistoryPoint(
                        tick=comp_tick,
                        value=1.0,
                        event_ids=comp_evts,
                        label=f"Goal completed: '{primary_goal.description}'",
                    )
                )

        return points

    @classmethod
    def _reconstruct_goal_pressure(
        cls,
        world: WorldState,
        char: Character,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct goal pressure over time (high when urgent unfulfilled goals exist)."""
        char_goals = world.get_character_goals(char.id)
        if not char_goals:
            return [HistoryPoint(tick=0, value=0.0, event_ids=[], label="No goal pressure")]

        initial_pressure = max([g.priority for g in char_goals], default=0.5)
        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=round(initial_pressure, 2),
                event_ids=[],
                label="Initial goal pressure",
            )
        ]

        # Pressure relieves when goals progress or complete
        sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        for ev in sorted_events:
            if char.id in ev.actor_ids:
                for g in char_goals:
                    if g.status in (GoalStatus.COMPLETED, GoalStatus.ACHIEVED) and ev.tick >= (g.last_progress_tick or ev.tick):
                        current_active = [cg for cg in char_goals if cg.status == GoalStatus.ACTIVE]
                        new_pressure = max([cg.priority * (1.0 - cg.progress) for cg in current_active], default=0.0)
                        if abs(new_pressure - points[-1].value) >= 0.1:
                            points.append(
                                HistoryPoint(
                                    tick=ev.tick,
                                    value=round(new_pressure, 2),
                                    event_ids=[ev.id],
                                    label=f"Goal pressure resolved by {ev.description}",
                                )
                            )
                        break

        return points

    @classmethod
    def _reconstruct_belief_confidence(
        cls,
        world: WorldState,
        char: Character,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct belief confidence across belief formations and reinforcement events."""
        beliefs = world.get_character_beliefs(char.id)
        init_conf = sum([b.confidence for b in beliefs]) / max(1, len(beliefs)) if beliefs else 0.5

        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=round(init_conf, 2),
                event_ids=[],
                label="Initial belief baseline",
            )
        ]

        sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        running_conf = init_conf

        for ev in sorted_events:
            if ev.event_type == EventType.BELIEF_FORMED and char.id in ev.actor_ids:
                running_conf = min(1.0, running_conf + 0.15)
                points.append(
                    HistoryPoint(
                        tick=ev.tick,
                        value=round(running_conf, 2),
                        event_ids=[ev.id],
                        label=f"Belief formed: {ev.description}",
                    )
                )
            elif "lying" in ev.description.lower() and char.id in ev.actor_ids:
                # Contradiction detected
                running_conf = max(0.1, running_conf - 0.20)
                points.append(
                    HistoryPoint(
                        tick=ev.tick,
                        value=round(running_conf, 2),
                        event_ids=[ev.id],
                        label=f"Belief shaken: {ev.description}",
                    )
                )

        return points

    @classmethod
    def _reconstruct_emotion_metric(
        cls,
        world: WorldState,
        char: Character,
        metric: str,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct an emotional trajectory (e.g. fear, anger, or composite valence)."""
        emo = char.emotional_state
        init_val = 0.0

        if metric == "emotional_valence":
            if emo:
                init_val = ((emo.happiness + emo.trust) - (emo.fear + emo.anger)) / 2.0
            points = [HistoryPoint(tick=0, value=round(init_val, 2), event_ids=[], label="Initial emotional valence")]
        else:
            if emo:
                init_val = getattr(emo, metric, 0.0)
            points = [HistoryPoint(tick=0, value=round(init_val, 2), event_ids=[], label=f"Initial {metric}")]

        running_val = init_val
        sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

        for ev in sorted_events:
            if char.id in ev.actor_ids:
                # Check for explicit emotion changes
                delta = 0.0
                if ev.event_type == EventType.EMOTION_CHANGED:
                    curr_state = ev.metadata.get("current_emotional_state", {})
                    prev_state = ev.metadata.get("previous_emotional_state", {})
                    if metric == "emotional_valence":
                        val_curr = ((curr_state.get("happiness", 0.0) + curr_state.get("trust", 0.0)) - (curr_state.get("fear", 0.0) + curr_state.get("anger", 0.0))) / 2.0
                        running_val = val_curr
                    elif metric in curr_state:
                        running_val = curr_state[metric]
                    points.append(
                        HistoryPoint(
                            tick=ev.tick,
                            value=round(running_val, 2),
                            event_ids=[ev.id],
                            label=ev.description,
                        )
                    )
                else:
                    # Check for cognitive effect deltas in metadata
                    delta_key = f"delta_{metric}"
                    if delta_key in ev.metadata:
                        delta = float(ev.metadata[delta_key])
                    elif metric == "emotional_valence":
                        dh = float(ev.metadata.get("delta_happiness", 0.0))
                        dt = float(ev.metadata.get("delta_trust", 0.0))
                        df = float(ev.metadata.get("delta_fear", 0.0))
                        da = float(ev.metadata.get("delta_anger", 0.0))
                        if any(x != 0.0 for x in [dh, dt, df, da]):
                            delta = ((dh + dt) - (df + da)) / 2.0

                    if delta != 0.0:
                        running_val = round(max(-1.0, min(1.0, running_val + delta)), 2)
                        points.append(
                            HistoryPoint(
                                tick=ev.tick,
                                value=running_val,
                                event_ids=[ev.id],
                                label=ev.description,
                                metadata={"delta": delta},
                            )
                        )

        return points

    @classmethod
    def _reconstruct_knowledge_acquisition(
        cls,
        world: WorldState,
        char: Character,
    ) -> List[HistoryPoint]:
        """Reconstruct cumulative knowledge acquisition points."""
        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=0.0,
                event_ids=[],
                label="Initial knowledge baseline",
            )
        ]

        count = 0
        sorted_events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

        for ev in sorted_events:
            # Check if this event was an acquisition event for character's knowledge items
            matching_items = [
                k for k in char.knowledge.values()
                if k.acquired_at_event == ev.id
            ]
            if matching_items or (ev.event_type == EventType.CHARACTER_OBSERVED and char.id in ev.actor_ids):
                count += len(matching_items) if matching_items else 1
                points.append(
                    HistoryPoint(
                        tick=ev.tick,
                        value=float(count),
                        event_ids=[ev.id],
                        label=f"Acquired knowledge from: {ev.description}",
                    )
                )

        return points

    @classmethod
    def _reconstruct_archetype_alignment(
        cls,
        world: WorldState,
        char: Character,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct archetype alignment and drift over time from ArchetypeTrajectoryAnalyzer."""
        events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        traj = ArchetypeTrajectoryAnalyzer.analyze_trajectory(char.id, world, events, differ=differ)

        init_arch = traj.initial_archetype.value if traj.initial_archetype else "neutral"
        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=1.0,
                event_ids=[],
                label=f"Initial archetype orientation: {init_arch}",
                metadata={"archetype": init_arch},
            )
        ]

        for idx, sp in enumerate(traj.shift_points):
            # Stability score decreases slightly with each recognized shift point
            stability_val = round(max(0.2, 1.0 - (idx + 1) * 0.15), 2)
            points.append(
                HistoryPoint(
                    tick=sp.tick,
                    value=stability_val,
                    event_ids=sp.evidence_event_ids,
                    label=f"Shifted to {sp.dominant_archetype.value}: {sp.rationale}",
                    metadata={"dominant_archetype": sp.dominant_archetype.value, "rationale": sp.rationale},
                )
            )

        return points

    @classmethod
    def _reconstruct_arc_stage(
        cls,
        world: WorldState,
        char: Character,
        differ: StateSnapshotDiffer,
    ) -> List[HistoryPoint]:
        """Reconstruct turning points from CharacterArcTracker."""
        events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        arc = CharacterArcTracker().trace_arc(char.id, world, events, differ=differ)

        points: List[HistoryPoint] = [
            HistoryPoint(
                tick=0,
                value=0.0,
                event_ids=[],
                label=f"Arc start: {arc.classification.value if hasattr(arc.classification, 'value') else arc.classification}",
                metadata={"classification": str(arc.classification)},
            )
        ]

        cumulative_magnitude = 0.0
        for tp in arc.turning_points:
            cumulative_magnitude = round(min(1.0, cumulative_magnitude + tp.delta_magnitude), 2)
            points.append(
                HistoryPoint(
                    tick=tp.tick,
                    value=cumulative_magnitude,
                    event_ids=[tp.event_id],
                    label=tp.description,
                    metadata={"state_change_type": tp.state_change_type, "delta_magnitude": tp.delta_magnitude},
                )
            )

        return points

    # -------------------------------------------------------------------------
    # Sparsity / Sampling Filter
    # -------------------------------------------------------------------------

    @classmethod
    def _filter_points(
        cls,
        points: List[HistoryPoint],
        sparse: bool,
        end_tick: int,
    ) -> List[HistoryPoint]:
        """Filter points for significant changes (sparse) or forward-fill all ticks (dense)."""
        if not points:
            return []

        # Sort points by tick
        sorted_pts = sorted(points, key=lambda p: (p.tick, p.value))

        if sparse:
            # Keep tick 0 and only points where value changed or events are attached
            filtered: List[HistoryPoint] = [sorted_pts[0]]
            for p in sorted_pts[1:]:
                if abs(p.value - filtered[-1].value) >= 0.01 or bool(p.event_ids):
                    if p.tick == filtered[-1].tick:
                        # Replace same tick point with the later updated point
                        filtered[-1] = p
                    else:
                        filtered.append(p)
            return filtered

        # Dense: forward-fill every tick up to end_tick
        dense_points: List[HistoryPoint] = []
        pt_map: Dict[int, HistoryPoint] = {p.tick: p for p in sorted_pts}
        latest_val = sorted_pts[0].value
        latest_pt = sorted_pts[0]

        max_tick = max(end_tick, sorted_pts[-1].tick)

        for t in range(0, max_tick + 1):
            if t in pt_map:
                latest_pt = pt_map[t]
                latest_val = latest_pt.value
                dense_points.append(latest_pt)
            else:
                dense_points.append(
                    HistoryPoint(
                        tick=t,
                        value=latest_val,
                        event_ids=[],
                        label=None,
                        metadata={"forward_filled": True},
                    )
                )

        return dense_points
