"""Causal Continuity Analyzer for D3 Story Lab.

Evaluates narrative sequences using Trey Parker & Matt Stone's 'Therefore / But' vs
'And Then' causality framework.

CRITICAL RULE: NO RETROACTIVE CANONICAL REWRITE
This analyzer is strictly read-only and interpretive. It never mutates or rewrites historical
events. Weak causality scores may be used by the Director as a soft pacing signal only.
"""

from typing import List, Dict, Optional, Any
from src.domain.event import Event, EventType
from src.domain.story_structure import (
    CausalTransitionType,
    CausalTransitionReport,
    CausalContinuitySummary,
    SceneData,
)


class CausalContinuityAnalyzer:
    """Measures and flags consequential 'Therefore / But' transitions vs episodic 'And Then' sequences."""

    CONFRONTATION_KEYWORDS = {"confront", "threat", "gun", "accuse", "refuse", "deny", "lies", "shout", "stop"}
    REVELATION_KEYWORDS = {"discover", "found", "secret", "truth", "clue", "padlock", "dossier", "unmask", "reveals"}
    OBSTACLE_KEYWORDS = {"locked", "blocked", "barrier", "barricade", "checkpoint", "laser"}

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
                # Sequential moves without friction: classic AND THEN
                trans_type = CausalTransitionType.AND_THEN
                score = 0.35
                rationale = f"Episodic movement by {list(actors_a)} without external obstacle (AND THEN)."
            elif (has_confrontation_a or has_revelation_a or has_obstacle_a) and (ev_b.event_type in (EventType.CHARACTER_MOVED, EventType.CHARACTER_SPOKE, EventType.OBJECT_PICKED_UP)):
                # Friction creates action
                trans_type = CausalTransitionType.BUT_THEREFORE
                score = 0.85
                rationale = f"Friction/clue in prior event forced subsequent action (THEREFORE/BUT)."
            elif is_reaction and (has_confrontation_b or has_revelation_b):
                trans_type = CausalTransitionType.BUT_THEREFORE
                score = 0.80
                rationale = f"Opposing actor presence sparked confrontation or revelation (BUT)."
            elif same_actor and ev_a.event_type == EventType.CHARACTER_MOVED and ev_b.event_type == EventType.CHARACTER_MOVED:
                # Sequential moves without friction
                trans_type = CausalTransitionType.AND_THEN
                score = 0.40
                rationale = f"Episodic movement by {ev_a.actor_ids} without immediate obstacle (AND THEN)."
            elif ev_a.location_id != ev_b.location_id and not is_reaction:
                trans_type = CausalTransitionType.AND_THEN
                score = 0.45
                rationale = "Location change without explicit causal bridge (AND THEN)."
            else:
                # General action sequence
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

        recommendation: Optional[str] = None
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
    ) -> CausalContinuitySummary:
        """Analyze causality across both events and scenes, returning an integrated summary."""
        if scenes and len(scenes) >= 2:
            return self.analyze_scene_causality(scenes)
        return self.analyze_event_causality(events)

    def analyze_scene_causality(self, scenes: List[SceneData]) -> CausalContinuitySummary:
        """Score macro-causality between consecutive scenes."""
        if len(scenes) < 2:
            return CausalContinuitySummary(
                overall_causal_score=85.0,
                but_therefore_ratio=1.0,
                and_then_count=0,
                but_therefore_count=0,
                total_transitions=0,
                transitions=[],
                pressure_recommendation="Single scene; baseline macro causality.",
            )

        reports: List[CausalTransitionReport] = []
        bt_count = 0
        at_count = 0

        for i in range(len(scenes) - 1):
            sc_a = scenes[i]
            sc_b = scenes[i + 1]

            # Compare purpose escalation
            # SETUP -> INVESTIGATION -> DISCOVERY -> CONFRONTATION is high causality
            is_escalating = (
                sc_a.scene_purpose != sc_b.scene_purpose
                and sc_b.dramatic_tension >= sc_a.dramatic_tension
            )

            if is_escalating:
                trans_type = CausalTransitionType.BUT_THEREFORE
                score = 0.85
                rationale = f"Scene {sc_a.scene_number} ({sc_a.scene_purpose.value}) escalated to {sc_b.scene_purpose.value} with higher stakes (THEREFORE)."
                bt_count += 1
            else:
                trans_type = CausalTransitionType.AND_THEN
                score = 0.50
                rationale = f"Scene transition without purpose escalation (AND THEN)."
                at_count += 1

            reports.append(
                CausalTransitionReport(
                    from_id=sc_a.scene_id,
                    to_id=sc_b.scene_id,
                    transition_type=trans_type,
                    score=score,
                    rationale=rationale,
                    tension_delta=sc_b.dramatic_tension - sc_a.dramatic_tension,
                )
            )

        total_trans = len(reports)
        bt_ratio = round(bt_count / max(1, total_trans), 2)
        overall_score = round((sum(r.score for r in reports) / max(1, total_trans)) * 100.0, 1)

        return CausalContinuitySummary(
            overall_causal_score=overall_score,
            but_therefore_ratio=bt_ratio,
            and_then_count=at_count,
            but_therefore_count=bt_count,
            total_transitions=total_trans,
            transitions=reports,
            pressure_recommendation="High macro-scene causal drive." if bt_ratio >= 0.5 else "Episodic scene pacing.",
        )
