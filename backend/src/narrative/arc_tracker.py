"""Character Arc Tracker for D3 Story Lab.

Reconstructs character arcs through strict post-hoc observation of immutable Event History
and StateSnapshotDiffer state transitions.

CRITICAL RULES:
1. STRUCTURE WITHOUT PUPPETRY:
   - This tracker NEVER mutates WorldState, characters, emotions, or beliefs.
   - It has ZERO mutation methods.
2. NO RETROACTIVE CANONICAL REWRITE:
   - It interprets historical events purely as an observer.
   - Characters are free to remain unchanged, be tested, entrench, or transform based solely on simulation choices.
3. TYPED KNOWLEDGE AUTHORITATIVE:
   - Uses typed Character.knowledge and PropositionRegistry. Never uses legacy known_facts or beliefs as authoritative.
4. DETERMINISTIC THRESHOLDS & PERSISTENCE:
   - Distinguishes persistent transformations from transient emotional spikes.
   - No AI in classification.
"""

import re
from typing import Dict, List, Optional, Any, Set
from src.domain.world import WorldState, Character
from src.domain.event import Event, EventType
from src.domain.goal import GoalStatus
from src.domain.story_structure import (
    ArcClassification,
    TurningPoint,
    CharacterArcTurn,
    CharacterArc,
    CharacterArcReport,
)
from src.simulation.differ import StateSnapshotDiffer


class CharacterArcTracker:
    """Observational analyzer that traces a character's journey without mutating world state."""

    BELIEF_FLIP_WEIGHT = 0.40
    GOAL_STATUS_WEIGHT = 0.35
    RELATIONSHIP_SHIFT_THRESHOLD = 0.30
    EMOTION_PERSISTENT_SHIFT_THRESHOLD = 0.30

    def trace_arc(
        self,
        character_id: str,
        world: WorldState,
        events: List[Event],
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> CharacterArc:
        """Observe and synthesize the character arc from immutable events and world state."""
        char = world.characters.get(character_id)
        if not char:
            return CharacterArc(
                character_id=character_id,
                character_name=character_id,
                classification=ArcClassification.NO_ARC_DETECTED,
                reason_if_none="Character not found in world state.",
                is_observed_only=True,
            )

        char_name = char.name
        sorted_events = sorted(events, key=lambda e: (e.tick, e.id))
        start_tick = sorted_events[0].tick if sorted_events else 0
        end_tick = world.current_tick if world.current_tick > 0 else (sorted_events[-1].tick if sorted_events else 0)

        # 1. State Differ initialization (use existing StateSnapshotDiffer, never duplicate)
        if differ is None:
            differ = StateSnapshotDiffer(world)

        snap_start = differ.get_or_create_snapshot(start_tick, world)
        snap_end = differ.get_or_create_snapshot(end_tick, world)

        # 2. Extract Starting State
        initial_emotions: Dict[str, float] = {}
        if hasattr(char, "emotional_state") and char.emotional_state:
            initial_emotions = {
                "fear": getattr(char.emotional_state, "fear", 0.0),
                "anger": getattr(char.emotional_state, "anger", 0.0),
                "trust": getattr(char.emotional_state, "trust", 0.0),
                "curiosity": getattr(char.emotional_state, "curiosity", 0.0),
            }

        # Check for first EMOTION_CHANGED event if available
        for ev in sorted_events:
            if ev.event_type == EventType.EMOTION_CHANGED and character_id in ev.actor_ids:
                prev_emo = ev.metadata.get("previous_emotional_state")
                if prev_emo:
                    initial_emotions = dict(prev_emo)
                break

        starting_state: Dict[str, Any] = {
            "name": char_name,
            "role": getattr(char, "role", "Unknown"),
            "initial_location_id": snap_start.character_locations.get(character_id, char.current_location_id),
            "initial_emotions": dict(initial_emotions),
            "initial_goals": list(snap_start.character_goals.get(character_id, [])),
            "initial_beliefs_count": len([k for (cid, pid), k in snap_start.character_beliefs.items() if cid == character_id]),
        }

        # 3. Extract Major Decisions (actions where character was prime mover)
        major_decisions: List[str] = []
        for ev in sorted_events:
            if ev.actor_ids and ev.actor_ids[0] == character_id:
                if ev.event_type in (
                    EventType.CHARACTER_SPOKE,
                    EventType.OBJECT_PICKED_UP,
                    EventType.OBJECT_GIVEN,
                    EventType.CHARACTER_MOVED,
                ):
                    major_decisions.append(f"[Tick {ev.tick}] {ev.description}")

        # 4. Extract Key Turns & Grounded Turning Points
        key_turns: List[CharacterArcTurn] = []
        turning_points: List[TurningPoint] = []
        last_known_emotions: Dict[str, float] = dict(initial_emotions)

        # Track final emotion from world character or last EMOTION_CHANGED event
        final_emotions: Dict[str, float] = {}
        if hasattr(char, "emotional_state") and char.emotional_state:
            final_emotions = {
                "fear": getattr(char.emotional_state, "fear", 0.0),
                "anger": getattr(char.emotional_state, "anger", 0.0),
                "trust": getattr(char.emotional_state, "trust", 0.0),
                "curiosity": getattr(char.emotional_state, "curiosity", 0.0),
            }
        for ev in reversed(sorted_events):
            if ev.event_type == EventType.EMOTION_CHANGED and character_id in ev.actor_ids:
                end_emo = ev.metadata.get("emotional_state")
                if end_emo:
                    final_emotions.update(end_emo)
                    break

        for ev in sorted_events:
            if character_id in ev.actor_ids:
                if ev.event_type == EventType.EMOTION_CHANGED:
                    curr_emo = ev.metadata.get("emotional_state", {})
                    # Check persistence: does this emotion shift reflect a persistent difference to ending state
                    # and persist for at least 2 subsequent ticks?
                    # Transient emotion spikes that revert to baseline do NOT count as turning points.
                    is_persistent_shift = False
                    for emo_key, target_val in curr_emo.items():
                        start_val = initial_emotions.get(emo_key, 0.0)
                        end_val = final_emotions.get(emo_key, target_val)
                        if abs(target_val - start_val) >= self.EMOTION_PERSISTENT_SHIFT_THRESHOLD:
                            # Verify it did not revert within 2 subsequent ticks
                            reverted_early = False
                            for next_ev in sorted_events:
                                if ev.tick < next_ev.tick <= ev.tick + 2:
                                    if next_ev.event_type == EventType.EMOTION_CHANGED and character_id in next_ev.actor_ids:
                                        next_emo = next_ev.metadata.get("emotional_state", {})
                                        if emo_key in next_emo and abs(next_emo[emo_key] - start_val) < 0.15:
                                            reverted_early = True
                                            break
                            if not reverted_early and abs(end_val - start_val) >= self.EMOTION_PERSISTENT_SHIFT_THRESHOLD:
                                is_persistent_shift = True
                                break

                    key_turns.append(
                        CharacterArcTurn(
                            tick=ev.tick,
                            event_id=ev.id,
                            turn_description=ev.description,
                            emotional_state_before=dict(last_known_emotions),
                            emotional_state_after=dict(curr_emo),
                        )
                    )
                    last_known_emotions = dict(curr_emo)

                    if is_persistent_shift:
                        turning_points.append(
                            TurningPoint(
                                event_id=ev.id,
                                delta_magnitude=self.EMOTION_PERSISTENT_SHIFT_THRESHOLD,
                                description=f"Persistent emotional shift: {ev.description}",
                                tick=ev.tick,
                                state_change_type="EMOTION_SHIFT",
                            )
                        )

                elif ev.event_type == EventType.BELIEF_FORMED:
                    key_turns.append(
                        CharacterArcTurn(
                            tick=ev.tick,
                            event_id=ev.id,
                            turn_description=ev.description,
                            belief_delta=ev.description,
                        )
                    )
                    turning_points.append(
                        TurningPoint(
                            event_id=ev.id,
                            delta_magnitude=self.BELIEF_FLIP_WEIGHT,
                            description=f"Belief formed: {ev.description}",
                            tick=ev.tick,
                            state_change_type="BELIEF_FORMED",
                        )
                    )

                elif ev.event_type == EventType.RELATIONSHIP_CHANGED:
                    key_turns.append(
                        CharacterArcTurn(
                            tick=ev.tick,
                            event_id=ev.id,
                            turn_description=ev.description,
                            relationship_delta=ev.description,
                        )
                    )
                    turning_points.append(
                        TurningPoint(
                            event_id=ev.id,
                            delta_magnitude=self.RELATIONSHIP_SHIFT_THRESHOLD,
                            description=f"Relationship shift: {ev.description}",
                            tick=ev.tick,
                            state_change_type="RELATIONSHIP_SHIFT",
                        )
                    )

        # Also check goal status transitions from world goals
        for goal in world.goals.values():
            if getattr(goal, "character_id", None) == character_id:
                if goal.status in (GoalStatus.COMPLETED, GoalStatus.ACHIEVED, GoalStatus.BLOCKED, GoalStatus.FAILED):
                    # Check if there is an event associated with this goal update
                    ref_evt_id = getattr(goal, "created_at_event", None)
                    if ref_evt_id and ref_evt_id in world.events:
                        evt = world.events[ref_evt_id]
                        if not any(tp.event_id == evt.id for tp in turning_points):
                            turning_points.append(
                                TurningPoint(
                                    event_id=evt.id,
                                    delta_magnitude=self.GOAL_STATUS_WEIGHT,
                                    description=f"Goal {goal.status.value}: {goal.description}",
                                    tick=evt.tick,
                                    state_change_type="GOAL_TRANSITION",
                                )
                            )

        # 5. Relationship Deltas between start and end
        relationship_deltas: Dict[str, str] = {}
        for rel in world.relationships.values():
            other_id = None
            if hasattr(rel, "character_a_id") and rel.character_a_id == character_id:
                other_id = rel.character_b_id
            elif hasattr(rel, "character_b_id") and rel.character_b_id == character_id:
                other_id = rel.character_a_id
            elif getattr(rel, "source_character_id", None) == character_id:
                other_id = getattr(rel, "target_character_id", None)

            if other_id:
                target_name = world.characters[other_id].name if other_id in world.characters else other_id
                aff = getattr(rel, "affinity", 0.0)
                trust = getattr(rel, "trust", 0.0)
                relationship_deltas[target_name] = f"Affinity: {aff:+.1f}, Trust: {trust:+.1f}"

        # 6. Extract Ending State
        ending_state: Dict[str, Any] = {
            "current_location_id": snap_end.character_locations.get(character_id, char.current_location_id),
            "final_emotions": dict(final_emotions or last_known_emotions),
            "final_goals": list(snap_end.character_goals.get(character_id, [])),
            "final_beliefs_count": len([k for (cid, pid), k in snap_end.character_beliefs.items() if cid == character_id]),
            "total_decisions_made": len(major_decisions),
            "total_turns_observed": len(key_turns),
        }

        # 7. Arc Semantics & Trajectory Classification
        classification = ArcClassification.NO_ARC_DETECTED
        reason_if_none: Optional[str] = None

        if len(turning_points) == 0:
            classification = ArcClassification.NO_ARC_DETECTED
            reason_if_none = "Character maintained baseline state with no persistent belief, goal, or relationship transformation."
        else:
            # Check for specific arc trajectories using word boundaries
            betrayal_pattern = r"\b(betrayal|betrayed|suspicion|suspicious|lies|lied|lying|conceal|concealed|deceit|deceived)\b"
            has_betrayal_or_suspicion = any(
                re.search(betrayal_pattern, t.description.lower())
                for t in turning_points
            ) or any(
                re.search(betrayal_pattern, t.turn_description.lower())
                for t in key_turns
            )

            # Disillusionment: Starting belief/trust was positive/trusting, ended negative, trust drop >= 0.4
            start_trust = initial_emotions.get("trust", 0.0)
            end_trust = final_emotions.get("trust", start_trust)
            trust_drop_magnitude = start_trust - end_trust

            rel_trust_drop = False
            for rel in world.relationships.values():
                if (hasattr(rel, "character_a_id") and rel.character_a_id == character_id) or \
                   (hasattr(rel, "character_b_id") and rel.character_b_id == character_id):
                    if getattr(rel, "trust", 0.0) <= -0.30:
                        rel_trust_drop = True
                        break

            is_disillusionment = (
                (has_betrayal_or_suspicion and rel_trust_drop)
                or (
                    (start_trust >= 0.20 or (has_betrayal_or_suspicion and start_trust >= 0.0))
                    and (trust_drop_magnitude >= 0.40 or (rel_trust_drop and trust_drop_magnitude >= 0.20))
                    and end_trust < 0.0
                )
            )

            # Fall: Moral alignment degraded, active goal abandoned or failed, hostility/anger/fear increased
            has_failed_goal = any(
                g.status in (GoalStatus.FAILED, GoalStatus.BLOCKED)
                for g in world.goals.values()
                if getattr(g, "character_id", None) == character_id
            )
            is_fall = (final_emotions.get("anger", 0.0) >= 0.70 or final_emotions.get("fear", 0.0) >= 0.85 or has_failed_goal) and not is_disillusionment

            # Positive change: constructive belief or goal achieved or positive trust increase
            has_positive_goal = any(
                g.status in (GoalStatus.ACHIEVED, GoalStatus.COMPLETED)
                for g in world.goals.values()
                if getattr(g, "character_id", None) == character_id
            )
            has_positive_trust = any(
                getattr(rel, "trust", 0.0) >= 0.30 or getattr(rel, "affinity", 0.0) >= 0.30
                for rel in world.relationships.values()
                if (hasattr(rel, "character_a_id") and rel.character_a_id == character_id) or \
                   (hasattr(rel, "character_b_id") and rel.character_b_id == character_id)
            ) or (end_trust - start_trust >= 0.30 and end_trust > 0.2)

            if is_disillusionment:
                classification = ArcClassification.DISILLUSIONMENT
            elif is_fall:
                classification = ArcClassification.FALL
            elif has_positive_goal or has_positive_trust:
                classification = ArcClassification.POSITIVE_CHANGE
            elif len(major_decisions) >= 2 and len(turning_points) >= 1:
                # Materially tested through pressure/events, but core stance held steady
                classification = ArcClassification.FLAT_TESTING
            else:
                classification = ArcClassification.NO_ARC_DETECTED
                reason_if_none = "Events occurred but produced no persistent shift in beliefs, goals, or relationships."

        evidence_event_ids = [tp.event_id for tp in turning_points] if classification != ArcClassification.NO_ARC_DETECTED else []

        return CharacterArc(
            character_id=character_id,
            character_name=char_name,
            classification=classification,
            starting_state=starting_state,
            ending_state=ending_state,
            turning_points=turning_points,
            evidence_event_ids=evidence_event_ids,
            reason_if_none=reason_if_none,
            major_decisions=major_decisions[:8],
            key_turns=key_turns,
            relationship_deltas=relationship_deltas,
            is_observed_only=True,
        )

    def trace_all_arcs(
        self,
        world: WorldState,
        events: List[Event],
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> Dict[str, CharacterArc]:
        """Observe arcs for all characters in the world without any mutation."""
        return {
            cid: self.trace_arc(cid, world, events, differ=differ)
            for cid in world.characters.keys()
        }

    # Alias for tracker interface
    track_character_arcs = trace_all_arcs
