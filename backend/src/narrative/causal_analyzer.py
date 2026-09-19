"""Causal Continuity Analyzer for D3 Story Lab.

Evaluates narrative sequences using Trey Parker & Matt Stone's 'Therefore / But' vs
'And Then' causality framework.

CRITICAL RULE: NO RETROACTIVE CANONICAL REWRITE
This analyzer is strictly read-only and interpretive. It never mutates or rewrites historical
events or scenes. Weak causality scores may be used by the Director as a soft pacing signal only.
"""

from typing import List, Dict, Optional, Any, Set, Tuple
from collections import deque
from src.domain.event import Event, EventType
from src.domain.world import WorldState
from src.domain.goal import GoalStatus
from src.domain.story_structure import (
    CausalTransitionType,
    CausalTransitionReport,
    CausalContinuitySummary,
    Scene,
    SceneData,
    SceneLink,
    SceneLinkType,
)
from src.simulation.differ import StateSnapshotDiffer


class CausalContinuityAnalyzer:
    """Measures and flags consequential 'Therefore / But' transitions vs episodic 'And Then' sequences."""

    CONFRONTATION_KEYWORDS = {"confront", "threat", "gun", "accuse", "refuse", "deny", "lies", "shout", "stop"}
    REVELATION_KEYWORDS = {"discover", "found", "secret", "truth", "clue", "padlock", "dossier", "unmask", "reveals"}
    OBSTACLE_KEYWORDS = {"locked", "blocked", "barrier", "barricade", "checkpoint", "laser"}

    def _find_causal_path(
        self,
        start_id: str,
        target_ids: Set[str],
        events_by_id: Dict[str, Event],
        max_depth: int = 25,
    ) -> Optional[List[str]]:
        """Deterministically find a causal ancestry path from start_id backwards to any event in target_ids."""
        queue: deque[Tuple[str, List[str]]] = deque([(start_id, [start_id])])
        visited: Set[str] = {start_id}

        while queue:
            curr_id, path = queue.popleft()
            if len(path) > max_depth:
                continue
            curr_evt = events_by_id.get(curr_id)
            if not curr_evt:
                continue
            for parent_id in curr_evt.caused_by:
                if parent_id in target_ids:
                    # Reached target scene. Return ordered chain: [target_ancestor, ..., intermediate, ..., start_id]
                    chain = [parent_id] + list(reversed(path))
                    return list(dict.fromkeys(chain))
                if parent_id not in visited and parent_id in events_by_id:
                    visited.add(parent_id)
                    queue.append((parent_id, path + [parent_id]))
        return None

    def _check_reversal_goal_progress(
        self,
        scene_a: Scene,
        scene_b: Scene,
        events_by_id: Dict[str, Event],
        world: Optional[WorldState] = None,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> Tuple[bool, List[str]]:
        """Determine if Scene B blocks, reverses, or materially worsens the goal-progress outcome of Scene A.

        A valid BUT requires:
        1. Scene A established goal-progress or asset acquisition.
        2. Scene B blocks, reverses, or materially worsens that specific progress.
        An ordinary obstacle without reversal does NOT create a BUT.
        """
        a_obj = scene_a.objective
        b_obj = scene_b.objective

        focal_char = a_obj.pov_character_id if a_obj else (
            scene_a.characters_present[0] if scene_a.characters_present else None
        )

        # 1. Did Scene A establish positive advancement?
        a_advanced = False
        a_ev_id: Optional[str] = scene_a.turning_point_event_id or (
            scene_a.source_event_ids[-1] if scene_a.source_event_ids else None
        )

        if a_obj and a_obj.outcome in ("ACHIEVED", "PARTIAL", "ACHIEVED_AT_COST"):
            a_advanced = True

        # Check pickup or acquisition in Scene A
        a_events = [events_by_id[eid] for eid in scene_a.source_event_ids if eid in events_by_id]
        for evt in a_events:
            if evt.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_GIVEN):
                a_advanced = True
                a_ev_id = evt.id
                break
            elif evt.event_type in (EventType.BELIEF_FORMED, EventType.MEMORY_CREATED):
                a_advanced = True
                if not a_ev_id:
                    a_ev_id = evt.id

        # Check goal progress in world if available
        if world and focal_char:
            for g in world.goals.values():
                if g.character_id == focal_char:
                    if g.last_progress_tick is not None and scene_a.start_tick <= g.last_progress_tick <= scene_a.end_tick:
                        a_advanced = True
                    elif g.progress > 0.0 or g.status in (GoalStatus.ACHIEVED, GoalStatus.COMPLETED):
                        a_advanced = True

        if not a_advanced:
            return False, []

        # 2. Did Scene B genuinely reverse or block that advancement?
        b_reversed = False
        b_ev_id: Optional[str] = scene_b.turning_point_event_id or (
            scene_b.source_event_ids[0] if scene_b.source_event_ids else None
        )

        # Reversal via SceneObjective outcome
        if b_obj and b_obj.outcome == "DENIED":
            b_reversed = True

        # Reversal via possession loss
        b_events = [events_by_id[eid] for eid in scene_b.source_event_ids if eid in events_by_id]
        for evt in b_events:
            if evt.event_type == EventType.OBJECT_DROPPED:
                b_reversed = True
                b_ev_id = evt.id
                break
            elif evt.event_type == EventType.OBJECT_GIVEN:
                # If given to an opponent or lost
                if focal_char and focal_char in evt.actor_ids:
                    b_reversed = True
                    b_ev_id = evt.id
                    break

        # Reversal via goal status transition to BLOCKED, FAILED, or ABANDONED in Scene B
        if world and focal_char:
            for g in world.goals.values():
                if g.character_id == focal_char:
                    if g.status in (GoalStatus.BLOCKED, GoalStatus.FAILED, GoalStatus.ABANDONED):
                        # Goal was blocked or failed
                        if g.last_progress_tick is not None and scene_b.start_tick <= g.last_progress_tick <= scene_b.end_tick:
                            b_reversed = True
                        elif b_obj and b_obj.outcome == "DENIED":
                            b_reversed = True

        # Check differ possession change if available
        if differ and world and focal_char:
            if a_obj and a_obj.state_delta.get("inventory_added"):
                added_items = a_obj.state_delta.get("inventory_added", [])
                if b_obj and b_obj.state_delta.get("inventory_removed"):
                    removed_items = b_obj.state_delta.get("inventory_removed", [])
                    if set(added_items) & set(removed_items):
                        b_reversed = True

        if a_advanced and b_reversed:
            evidence: List[str] = []
            if a_ev_id:
                evidence.append(a_ev_id)
            if b_ev_id and b_ev_id not in evidence:
                evidence.append(b_ev_id)
            return True, evidence

        return False, []

    def _check_concurrency(
        self,
        scene_a: Scene,
        scene_b: Scene,
        events_by_id: Dict[str, Event],
    ) -> Tuple[bool, List[str]]:
        """Check whether Scene A -> Scene B represents demonstrably concurrent activity at a different location."""
        if scene_a.location_id == scene_b.location_id:
            return False, []

        # Check for disjoint characters present
        chars_a = set(scene_a.characters_present)
        chars_b = set(scene_b.characters_present)
        different_actors = chars_a.isdisjoint(chars_b) or (
            scene_a.objective is not None
            and scene_b.objective is not None
            and scene_a.objective.pov_character_id != scene_b.objective.pov_character_id
        )

        if not different_actors:
            return False, []

        # Check shared ticks among source events
        ticks_a = {events_by_id[eid].tick for eid in scene_a.source_event_ids if eid in events_by_id}
        ticks_b = {events_by_id[eid].tick for eid in scene_b.source_event_ids if eid in events_by_id}
        shared_ticks = ticks_a & ticks_b

        if shared_ticks:
            ev_a = [eid for eid in scene_a.source_event_ids if events_by_id.get(eid) and events_by_id[eid].tick in shared_ticks]
            ev_b = [eid for eid in scene_b.source_event_ids if events_by_id.get(eid) and events_by_id[eid].tick in shared_ticks]
            evidence = ev_a[:1] + ev_b[:1]
            return True, evidence

        # Check explicit framing or concurrent context
        if scene_b.time_context in ("CONCURRENT", "OVERLAPPING") or scene_b.framing_type in ("parallel_action", "meanwhile"):
            evidence = []
            if scene_a.source_event_ids:
                evidence.append(scene_a.source_event_ids[0])
            if scene_b.source_event_ids:
                evidence.append(scene_b.source_event_ids[0])
            if evidence:
                return True, evidence

        return False, []

    def classify_scene_transition(
        self,
        scene_a: Scene,
        scene_b: Scene,
        events_by_id: Dict[str, Event],
        world: Optional[WorldState] = None,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> SceneLink:
        """Deterministically classify the causal link between two sequential scenes backed by typed evidence."""
        # 1. Genuine Reversal / Blocking (BUT)
        is_reversal, reversal_evidence = self._check_reversal_goal_progress(
            scene_a, scene_b, events_by_id=events_by_id, world=world, differ=differ
        )
        if is_reversal and reversal_evidence:
            return SceneLink(
                from_scene_id=scene_a.scene_id,
                to_scene_id=scene_b.scene_id,
                type=SceneLinkType.BUT,
                evidence_event_ids=reversal_evidence,
                rationale=f"Scene {scene_b.scene_id} reverses or blocks goal advancement established in Scene {scene_a.scene_id} (BUT).",
            )

        # 2. Causal Ancestry via Event.caused_by (THEREFORE)
        target_ids = set(scene_a.source_event_ids)
        scene_b_events = [events_by_id[eid] for eid in scene_b.source_event_ids if eid in events_by_id]
        scene_b_events.sort(key=lambda e: (e.tick, e.id))

        initiating_candidates: List[Event] = []
        if scene_b_events:
            min_tick = scene_b_events[0].tick
            initiating_candidates = [e for e in scene_b_events if e.tick == min_tick]
            external_cause_events = [
                e for e in scene_b_events
                if any(c not in scene_b.source_event_ids for c in e.caused_by)
            ]
            for e in external_cause_events:
                if e not in initiating_candidates:
                    initiating_candidates.append(e)
            for e in scene_b_events:
                if e not in initiating_candidates:
                    initiating_candidates.append(e)

        for candidate in initiating_candidates:
            path = self._find_causal_path(candidate.id, target_ids, events_by_id)
            if path:
                return SceneLink(
                    from_scene_id=scene_a.scene_id,
                    to_scene_id=scene_b.scene_id,
                    type=SceneLinkType.THEREFORE,
                    evidence_event_ids=path,
                    rationale=f"Initiating event '{candidate.id}' in Scene {scene_b.scene_id} was caused by event '{path[0]}' in Scene {scene_a.scene_id} via causal ancestry chain (THEREFORE).",
                )

        # 3. Demonstrably concurrent activity at different location (MEANWHILE)
        is_concurrent, concurrent_evidence = self._check_concurrency(scene_a, scene_b, events_by_id)
        if is_concurrent and concurrent_evidence:
            return SceneLink(
                from_scene_id=scene_a.scene_id,
                to_scene_id=scene_b.scene_id,
                type=SceneLinkType.MEANWHILE,
                evidence_event_ids=concurrent_evidence,
                rationale=f"Scene {scene_b.scene_id} represents demonstrably concurrent activity at a different location than Scene {scene_a.scene_id} (MEANWHILE).",
            )

        # 4. Default fallback: AND_THEN
        return SceneLink(
            from_scene_id=scene_a.scene_id,
            to_scene_id=scene_b.scene_id,
            type=SceneLinkType.AND_THEN,
            evidence_event_ids=[],
            rationale=f"Sequential transition from Scene {scene_a.scene_id} to Scene {scene_b.scene_id} without direct causal link, reversal, or temporal concurrency (AND THEN).",
        )

    def analyze_scene_sequence(
        self,
        scenes: List[Scene],
        world: Optional[WorldState] = None,
        differ: Optional[StateSnapshotDiffer] = None,
        events: Optional[List[Event]] = None,
    ) -> CausalContinuitySummary:
        """Compute causal continuity across a sequence of scenes and detect consecutive AND_THEN runs."""
        if len(scenes) < 2:
            return CausalContinuitySummary(
                overall_causal_score=85.0,
                but_therefore_ratio=1.0,
                and_then_count=0,
                but_therefore_count=0,
                total_transitions=0,
                transitions=[],
                pressure_recommendation="Single scene or empty sequence; baseline macro causality.",
                scene_links=[],
                therefore_count=0,
                but_count=0,
                meanwhile_count=0,
                total_scene_links=0,
                and_then_ratio=0.0,
                consecutive_and_then_runs=[],
            )

        # Index all events for lookup
        events_by_id: Dict[str, Event] = {}
        if world:
            events_by_id.update(world.events)
        if events:
            for ev in events:
                events_by_id[ev.id] = ev

        links: List[SceneLink] = []
        for i in range(len(scenes) - 1):
            sc_a = scenes[i]
            sc_b = scenes[i + 1]
            link = self.classify_scene_transition(sc_a, sc_b, events_by_id=events_by_id, world=world, differ=differ)
            links.append(link)

        therefore_count = sum(1 for l in links if l.type == SceneLinkType.THEREFORE)
        but_count = sum(1 for l in links if l.type == SceneLinkType.BUT)
        meanwhile_count = sum(1 for l in links if l.type == SceneLinkType.MEANWHILE)
        and_then_count = sum(1 for l in links if l.type == SceneLinkType.AND_THEN)
        total_links = len(links)
        and_then_ratio = round(and_then_count / max(1, total_links), 2)

        # Detect any run of >= 2 consecutive AND_THEN links with involved scene IDs
        consecutive_and_then_runs: List[List[str]] = []
        current_run: List[str] = []

        for link in links:
            if link.type == SceneLinkType.AND_THEN:
                if not current_run:
                    current_run = [link.from_scene_id, link.to_scene_id]
                else:
                    current_run.append(link.to_scene_id)
            else:
                if len(current_run) >= 3:
                    consecutive_and_then_runs.append(list(current_run))
                current_run = []

        if len(current_run) >= 3:
            consecutive_and_then_runs.append(list(current_run))

        # Build legacy transitions for backward compatibility
        reports: List[CausalTransitionReport] = []
        for l in links:
            if l.type == SceneLinkType.THEREFORE:
                ttype = CausalTransitionType.THEREFORE
                score = 0.90
            elif l.type == SceneLinkType.BUT:
                ttype = CausalTransitionType.BUT
                score = 0.90
            elif l.type == SceneLinkType.MEANWHILE:
                ttype = CausalTransitionType.MEANWHILE
                score = 0.70
            else:
                ttype = CausalTransitionType.AND_THEN
                score = 0.40

            reports.append(
                CausalTransitionReport(
                    from_id=l.from_scene_id,
                    to_id=l.to_scene_id,
                    transition_type=ttype,
                    score=score,
                    rationale=l.rationale,
                    tension_delta=10.0 if l.type == SceneLinkType.BUT else 5.0 if l.type == SceneLinkType.THEREFORE else 0.0,
                )
            )

        bt_count = therefore_count + but_count
        bt_ratio = round(bt_count / max(1, total_links), 2)
        overall_score = round((sum(r.score for r in reports) / max(1, total_links)) * 100.0, 1)

        if and_then_ratio > 0.50:
            rec = (
                f"High episodic ratio ({and_then_ratio:.2f}): Narrative sequence contains excessive 'And-Then' "
                f"transitions ({and_then_count}/{total_links}). Recommend Director inject causal pressures."
            )
        else:
            rec = (
                f"Strong causal drive: Consequential transitions dominate (Therefore: {therefore_count}, "
                f"But: {but_count}, Meanwhile: {meanwhile_count}, And-Then: {and_then_count})."
            )

        return CausalContinuitySummary(
            overall_causal_score=overall_score,
            but_therefore_ratio=bt_ratio,
            and_then_count=and_then_count,
            but_therefore_count=bt_count,
            total_transitions=total_links,
            transitions=reports,
            pressure_recommendation=rec,
            scene_links=links,
            therefore_count=therefore_count,
            but_count=but_count,
            meanwhile_count=meanwhile_count,
            total_scene_links=total_links,
            and_then_ratio=and_then_ratio,
            consecutive_and_then_runs=consecutive_and_then_runs,
        )

    def analyze_event_causality(self, events: List[Event]) -> CausalContinuitySummary:
        """Score sequential causality between consecutive events in immutable history."""
        sorted_events = sorted(events, key=lambda e: (e.tick, e.id))
        if len(sorted_events) < 2:
            return CausalContinuitySummary(
                overall_causal_score=80.0,
                but_therefore_ratio=1.0,
                and_then_count=0,
                but_therefore_count=0,
                total_transitions=0,
                transitions=[],
                pressure_recommendation="Insufficient events for transition analysis.",
            )

        reports: List[CausalTransitionReport] = []
        but_therefore_count = 0
        and_then_count = 0

        for i in range(len(sorted_events) - 1):
            ev_a = sorted_events[i]
            ev_b = sorted_events[i + 1]

            desc_a = (ev_a.description or "").lower()
            desc_b = (ev_b.description or "").lower()

            actors_a = set(ev_a.actor_ids)
            actors_b = set(ev_b.actor_ids)

            is_reaction = bool(actors_a and actors_b and actors_a != actors_b)
            same_actor = bool(actors_a and actors_b and actors_a == actors_b)

            has_obstacle_a = any(w in desc_a for w in self.OBSTACLE_KEYWORDS)
            has_revelation_a = any(w in desc_a for w in self.REVELATION_KEYWORDS)
            has_confrontation_a = any(w in desc_a for w in self.CONFRONTATION_KEYWORDS)

            has_obstacle_b = any(w in desc_b for w in self.OBSTACLE_KEYWORDS)
            has_revelation_b = any(w in desc_b for w in self.REVELATION_KEYWORDS)
            has_confrontation_b = any(w in desc_b for w in self.CONFRONTATION_KEYWORDS)

            # Determine transition type and score
            if same_actor and ev_a.event_type == EventType.CHARACTER_MOVED and ev_b.event_type == EventType.CHARACTER_MOVED:
                trans_type = CausalTransitionType.AND_THEN
                score = 0.35
                rationale = f"Episodic movement by {list(actors_a)} without external obstacle (AND THEN)."
            elif (has_confrontation_a or has_revelation_a or has_obstacle_a) and (ev_b.event_type in (EventType.CHARACTER_MOVED, EventType.CHARACTER_SPOKE, EventType.OBJECT_PICKED_UP)):
                trans_type = CausalTransitionType.BUT_THEREFORE
                score = 0.85
                rationale = f"Friction/clue in prior event forced subsequent action (THEREFORE/BUT)."
            elif is_reaction and (has_confrontation_b or has_revelation_b):
                trans_type = CausalTransitionType.BUT_THEREFORE
                score = 0.80
                rationale = f"Opposing actor presence sparked confrontation or revelation (BUT)."
            elif same_actor and ev_a.event_type == EventType.CHARACTER_MOVED and ev_b.event_type == EventType.CHARACTER_MOVED:
                trans_type = CausalTransitionType.AND_THEN
                score = 0.40
                rationale = f"Episodic movement by {ev_a.actor_ids} without immediate obstacle (AND THEN)."
            elif ev_a.location_id != ev_b.location_id and not is_reaction:
                trans_type = CausalTransitionType.AND_THEN
                score = 0.45
                rationale = "Location change without explicit causal bridge (AND THEN)."
            else:
                trans_type = CausalTransitionType.BUT_THEREFORE if is_reaction else CausalTransitionType.AND_THEN
                score = 0.70 if is_reaction else 0.50
                rationale = "Interactive exchange (THEREFORE)" if is_reaction else "Sequential action progression (AND THEN)"

            if trans_type == CausalTransitionType.BUT_THEREFORE:
                but_therefore_count += 1
            else:
                and_then_count += 1

            reports.append(
                CausalTransitionReport(
                    from_id=ev_a.id,
                    to_id=ev_b.id,
                    transition_type=trans_type,
                    score=score,
                    rationale=rationale,
                    tension_delta=10.0 if trans_type == CausalTransitionType.BUT_THEREFORE else 0.0,
                )
            )

        total_trans = len(reports)
        bt_ratio = round(but_therefore_count / max(1, total_trans), 2)
        overall_score = round((sum(r.score for r in reports) / max(1, total_trans)) * 100.0, 1)

        if bt_ratio < 0.40:
            recommendation = (
                "Pacing signal for Director: Causal connectivity is predominantly episodic ('and-then'). "
                "Recommend injecting an obstacle, arrival, or deadline to force consequential choices."
            )
        else:
            recommendation = (
                "High causal coherence ('therefore/but'): Characters are acting in direct response to "
                "adversarial friction and revelations."
            )

        return CausalContinuitySummary(
            overall_causal_score=overall_score,
            but_therefore_ratio=bt_ratio,
            and_then_count=and_then_count,
            but_therefore_count=but_therefore_count,
            total_transitions=total_trans,
            transitions=reports,
            pressure_recommendation=recommendation,
        )

    def analyze_causal_continuity(
        self,
        events: List[Event],
        scenes: Optional[List[SceneData]] = None,
        world: Optional[WorldState] = None,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CausalContinuitySummary:
        """Analyze causality across both events and scenes, returning an integrated summary."""
        if scenes and len(scenes) >= 2:
            return self.analyze_scene_sequence(scenes, world=world, differ=differ, events=events)
        return self.analyze_event_causality(events)

    def analyze_scene_causality(
        self,
        scenes: List[SceneData],
        world: Optional[WorldState] = None,
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CausalContinuitySummary:
        """Score macro-causality between consecutive scenes."""
        return self.analyze_scene_sequence(scenes, world=world, differ=differ)
