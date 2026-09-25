"""Observational Archetype Trajectory Analyzer for D3 Story Lab.

Reconstructs character archetype alignment drift through strict post-hoc observation
of immutable Event History and StateSnapshotDiffer state transitions.

CRITICAL INVARIANTS:
1. READ-ONLY OBSERVATION:
   - This analyzer NEVER mutates WorldState, characters, emotions, or beliefs.
   - It has ZERO mutation methods.
2. NO RETROACTIVE REWRITE & NO FORCED BEHAVIOR:
   - Interprets historical events purely as an external dramatic observer.
   - Characters are free to remain steady or shift orientation based on simulation choices.
3. GROUNDED IN EVIDENCE:
   - Every detected orientation shift point is evidenced by concrete event_ids.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from ..domain.world import WorldState, Character
from ..domain.event import Event, EventType
from ..domain.archetype import ArchetypeType, ArchetypeShiftPoint, ArchetypeTrajectory
from ..simulation.differ import StateSnapshotDiffer


class ArchetypeTrajectoryAnalyzer:
    """Strictly observational analyzer for character archetype alignment and trajectory."""

    @classmethod
    def analyze_trajectory(
        cls,
        character_id: str,
        world: WorldState,
        events: List[Event],
        differ: Optional[StateSnapshotDiffer] = None,
    ) -> ArchetypeTrajectory:
        """Observe historical events and derive the archetype trajectory without mutating world state."""
        char = world.characters.get(character_id)
        char_name = char.name if char else character_id
        initial_archetype = char.dynamics.primary_archetype if (char and char.dynamics) else None

        # Filter events where the character is a prime mover or participant
        char_events = [
            e for e in sorted(events, key=lambda ev: (ev.tick, ev.id))
            if character_id in e.actor_ids or (hasattr(e, "metadata") and e.metadata.get("speaker_id") == character_id)
        ]

        if not char_events:
            summary = (
                f"{char_name} maintains an initial orientation of {initial_archetype.value if initial_archetype else 'unassigned'} "
                "with no recorded active events."
            )
            return ArchetypeTrajectory(
                character_id=character_id,
                character_name=char_name,
                initial_archetype=initial_archetype,
                current_dominant_archetype=initial_archetype,
                shift_points=[],
                trajectory_summary=summary,
                stability_score=1.0,
                is_observed_only=True,
            )

        # 1. Bucket events into sequential windows by tick (e.g. 5-tick intervals or clusters)
        tick_windows: Dict[int, List[Event]] = defaultdict(list)
        for ev in char_events:
            window_key = (ev.tick // 5) * 5
            tick_windows[window_key].append(ev)

        shift_points: List[ArchetypeShiftPoint] = []
        window_dominant_archetypes: List[ArchetypeType] = []
        last_dominant: Optional[ArchetypeType] = initial_archetype

        for window_tick in sorted(tick_windows.keys()):
            window_events = tick_windows[window_tick]
            scores: Dict[ArchetypeType, float] = defaultdict(float)
            event_evidence: Dict[ArchetypeType, List[str]] = defaultdict(list)

            for ev in window_events:
                # Classify event archetype manifestations
                detected_archetype = cls._classify_event_archetype(ev, character_id)
                if detected_archetype:
                    scores[detected_archetype] += 1.0
                    event_evidence[detected_archetype].append(ev.id)

            if not scores:
                continue

            # Identify dominant archetype for this window
            top_arch, top_score = max(scores.items(), key=lambda item: (item[1], item[0].value))
            window_dominant_archetypes.append(top_arch)

            # Detect shift if different from previous dominant and sustained with >= 1.5 signal weight
            if last_dominant and top_arch != last_dominant and top_score >= 1.0:
                rationale = (
                    f"Observed behavioral shift from {last_dominant.value} to {top_arch.value} "
                    f"evidenced by actions in window tick {window_tick}."
                )
                shift_points.append(
                    ArchetypeShiftPoint(
                        tick=window_tick,
                        dominant_archetype=top_arch,
                        confidence=min(1.0, 0.5 + 0.15 * top_score),
                        evidence_event_ids=list(event_evidence[top_arch]),
                        rationale=rationale,
                    )
                )
                last_dominant = top_arch

        # Current dominant is the last recorded dominant, or initial if none observed
        current_dominant = last_dominant or initial_archetype

        # Compute stability score
        if initial_archetype and window_dominant_archetypes:
            matches = sum(1 for a in window_dominant_archetypes if a == initial_archetype)
            stability_score = round(matches / len(window_dominant_archetypes), 2)
        else:
            stability_score = 1.0 if not shift_points else 0.5

        # Build trajectory summary
        if not shift_points:
            summary = (
                f"{char_name} consistently expressed the {initial_archetype.value if initial_archetype else 'unassigned'} "
                f"archetype across all {len(char_events)} observed actions with high stability ({stability_score:.0%})."
            )
        else:
            shifts_str = " -> ".join([initial_archetype.value if initial_archetype else "INITIAL"] + [sp.dominant_archetype.value for sp in shift_points])
            summary = (
                f"{char_name} exhibited dynamic orientation shifts ({shifts_str}) over {len(char_events)} events, "
                f"transitioning into a dominant {current_dominant.value if current_dominant else 'unassigned'} expression."
            )

        return ArchetypeTrajectory(
            character_id=character_id,
            character_name=char_name,
            initial_archetype=initial_archetype,
            current_dominant_archetype=current_dominant,
            shift_points=shift_points,
            trajectory_summary=summary,
            stability_score=stability_score,
            is_observed_only=True,
        )

    @classmethod
    def _classify_event_archetype(cls, event: Event, character_id: str) -> Optional[ArchetypeType]:
        """Observational classification of an event into an archetype manifestation."""
        ev_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)

        # Speech actions
        if ev_type in ("character_spoke", "dialogue"):
            social_intent = (event.metadata.get("social_intent") or "").lower()
            speech_act = (event.metadata.get("speech_act") or "").lower()
            intent = social_intent or speech_act

            if intent in ("question", "inquire", "analyze", "advise"):
                return ArchetypeType.SAGE
            if intent in ("command", "demand", "direct", "interrogate"):
                return ArchetypeType.RULER
            if intent in ("comfort", "reassure", "help", "support", "plead"):
                return ArchetypeType.CAREGIVER
            if intent in ("challenge", "defy", "threaten", "taunt", "accuse"):
                return ArchetypeType.OUTLAW
            if intent in ("confide", "connect", "reconcile"):
                return ArchetypeType.LOVER
            if intent in ("joke", "defuse"):
                return ArchetypeType.JESTER

            # Check dialogue content for keywords
            dialogue = (event.metadata.get("dialogue") or event.description or "").lower()
            if any(w in dialogue for w in ("evidence", "truth", "facts", "analyze", "data", "clue")):
                return ArchetypeType.SAGE
            if any(w in dialogue for w in ("rule", "order", "my authority", "control")):
                return ArchetypeType.RULER
            if any(w in dialogue for w in ("safe", "care", "protect", "help you")):
                return ArchetypeType.CAREGIVER
            if any(w in dialogue for w in ("won't listen", "break", "liar", "defy")):
                return ArchetypeType.OUTLAW

        # Object actions
        elif ev_type in ("object_inspected", "inspect_object"):
            return ArchetypeType.SAGE
        elif ev_type in ("object_given", "give_object"):
            return ArchetypeType.CAREGIVER
        elif ev_type in ("object_taken", "take_object", "pickup", "object_picked_up"):
            return ArchetypeType.HERO

        # Locomotion / exploration
        elif ev_type in ("character_moved", "move"):
            return ArchetypeType.EXPLORER

        # Secret revealed
        elif ev_type in ("secret_revealed",):
            return ArchetypeType.SAGE

        # Default fallback: if character was active mover pursuing goals
        if character_id in event.actor_ids:
            return ArchetypeType.HERO

        return None
