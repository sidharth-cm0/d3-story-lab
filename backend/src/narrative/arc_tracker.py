"""Character Arc Tracker for D3 Story Lab.

Reconstructs character arcs through strict post-hoc observation of immutable Event History.

CRITICAL RULES:
1. STRUCTURE WITHOUT PUPPETRY:
   - This tracker NEVER mutates WorldState, characters, emotions, or beliefs.
   - It has ZERO mutation methods.
2. NO RETROACTIVE CANONICAL REWRITE:
   - It interprets historical events purely as an observer.
   - Characters are free to remain unchanged, entrench, or transform based solely on simulation choices.
"""

from typing import Dict, List, Optional, Any
from src.domain.world import WorldState, Character
from src.domain.event import Event, EventType
from src.domain.story_structure import (
    CharacterArcTurn,
    CharacterArcReport,
)


class CharacterArcTracker:
    """Observational analyzer that traces a character's journey without mutating world state."""

    def trace_arc(
        self,
        character_id: str,
        world: WorldState,
        events: List[Event],
    ) -> CharacterArcReport:
        """Observe and synthesize the character arc from immutable events and world state."""
        char = world.characters.get(character_id)
        char_name = char.name if char else character_id

        sorted_events = sorted(events, key=lambda e: (e.tick, e.id))

        # 1. Starting State
        starting_state: Dict[str, Any] = {
            "name": char_name,
            "role": char.role if char else "Unknown",
            "personality_traits": list(char.personality_traits) if char and hasattr(char, "personality_traits") else [],
            "initial_location_id": char.current_location_id if char else None,
        }

        # 2. Extract Major Decisions (actions where character acted as prime mover)
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

        # 3. Extract Key Turns (emotional shifts, belief formations, relationship changes)
        key_turns: List[CharacterArcTurn] = []
        last_known_emotions: Dict[str, float] = {}

        for ev in sorted_events:
            if character_id in ev.actor_ids:
                if ev.event_type == EventType.EMOTION_CHANGED:
                    curr_emo = ev.metadata.get("emotional_state", {})
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

                elif ev.event_type == EventType.BELIEF_FORMED:
                    key_turns.append(
                        CharacterArcTurn(
                            tick=ev.tick,
                            event_id=ev.id,
                            turn_description=ev.description,
                            belief_delta=ev.description,
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

        # 4. Relationship Deltas
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
                relationship_deltas[target_name] = f"Affinity: {rel.affinity:+.1f}, Trust: {rel.trust:+.1f}"

        # 5. Ending State
        ending_state: Dict[str, Any] = {
            "current_location_id": char.current_location_id if char else None,
            "final_emotions": dict(last_known_emotions),
            "total_decisions_made": len(major_decisions),
            "total_turns_observed": len(key_turns),
        }

        # 6. Observational Trajectory Classification
        # NEVER forces a transformation; merely categorizes what organically occurred
        if len(key_turns) == 0 and len(major_decisions) <= 1:
            trajectory = "OBSERVED_STABLE"
        elif any("betrayal" in t.turn_description.lower() or "suspicion" in t.turn_description.lower() for t in key_turns):
            trajectory = "DISILLUSIONMENT"
        elif any(t.belief_delta is not None for t in key_turns):
            trajectory = "REVELATION"
        elif len(key_turns) >= 2:
            trajectory = "TRANSFORMATION"
        else:
            trajectory = "ENTRENCHMENT"

        return CharacterArcReport(
            character_id=character_id,
            character_name=char_name,
            starting_state=starting_state,
            major_decisions=major_decisions[:8],  # Keep concise
            key_turns=key_turns,
            relationship_deltas=relationship_deltas,
            ending_state=ending_state,
            arc_trajectory=trajectory,
            is_observed_only=True,
        )

    def trace_all_arcs(
        self,
        world: WorldState,
        events: List[Event],
    ) -> Dict[str, CharacterArcReport]:
        """Observe arcs for all characters in the world without any mutation."""
        return {
            cid: self.trace_arc(cid, world, events)
            for cid in world.characters.keys()
        }

    # Alias for tracker interface
    track_character_arcs = trace_all_arcs

