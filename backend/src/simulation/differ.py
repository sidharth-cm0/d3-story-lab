"""StateSnapshotDiffer utility for deterministic state-diffing over event replay.

NOTE: This utility is intended for reuse by CharacterArcTracker in Phase 6.
The arc tracker needs exactly the same before/after-state-diff operation.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field

from ..domain import (
    WorldState,
    Event,
    EventType,
    KnowledgeItem,
    Goal,
)
from ..story.models import PredicateClause


@dataclass
class WorldSnapshot:
    """State snapshot at a discrete tick."""
    tick: int
    object_holders: Dict[str, Optional[str]] = field(default_factory=dict)
    object_locations: Dict[str, Optional[str]] = field(default_factory=dict)
    character_locations: Dict[str, Optional[str]] = field(default_factory=dict)
    character_goals: Dict[str, List[str]] = field(default_factory=dict)
    character_beliefs: Dict[Tuple[str, str], bool] = field(default_factory=dict)  # (char_id, prop_id) -> val
    relationships: Dict[Tuple[str, str], float] = field(default_factory=dict)      # (char_a, char_b) -> affinity


class StateSnapshotDiffer:
    """Utility that captures and diffs world states across simulation windows.
    
    Operates directly over the event-sourced simulation history without requiring
    a separate snapshot database.
    """

    def __init__(self, world: Optional[WorldState] = None):
        self.snapshots: Dict[int, WorldSnapshot] = {}
        if world:
            self.capture_snapshot(world.current_tick, world)

    def capture_snapshot(self, tick: int, world: WorldState) -> WorldSnapshot:
        """Capture an instantaneous snapshot of the world at `tick`."""
        obj_holders = {oid: obj.holder_id for oid, obj in world.objects.items()}
        obj_locs = {oid: obj.location_id for oid, obj in world.objects.items()}
        char_locs = {cid: char.current_location_id for cid, char in world.characters.items()}
        
        char_goals: Dict[str, List[str]] = {}
        char_beliefs: Dict[Tuple[str, str], bool] = {}
        relationships: Dict[Tuple[str, str], float] = {}

        for cid, char in world.characters.items():
            char_goals[cid] = [g.id if hasattr(g, "id") else str(g) for g in char.goals]
            for prop_id, k_item in char.knowledge.items():
                char_beliefs[(cid, prop_id)] = k_item.believed_truth_value
            if isinstance(char.relationships, dict):
                for target_id, rel in char.relationships.items():
                    relationships[(cid, target_id)] = getattr(rel, "affinity", 0.0)
            elif isinstance(char.relationships, list):
                for rel in char.relationships:
                    if isinstance(rel, str) and hasattr(world, "relationships") and rel in world.relationships:
                        rel_obj = world.relationships[rel]
                        tid = rel_obj.character_b_id if rel_obj.character_a_id == cid else rel_obj.character_a_id
                        relationships[(cid, tid)] = getattr(rel_obj, "affinity", 0.0)
                    else:
                        tid = getattr(rel, "target_character_id", None) or getattr(rel, "target_id", None)
                        if not tid and hasattr(rel, "character_a_id") and hasattr(rel, "character_b_id"):
                            tid = rel.character_b_id if rel.character_a_id == cid else rel.character_a_id
                        if tid:
                            relationships[(cid, tid)] = getattr(rel, "affinity", 0.0)

        # Also register world-level relationships
        if hasattr(world, "relationships") and isinstance(world.relationships, dict):
            for rel in world.relationships.values():
                ca = getattr(rel, "character_a_id", None)
                cb = getattr(rel, "character_b_id", None)
                aff = getattr(rel, "affinity", 0.0)
                if ca and cb:
                    relationships.setdefault((ca, cb), aff)
                    relationships.setdefault((cb, ca), aff)

        snap = WorldSnapshot(
            tick=tick,
            object_holders=obj_holders,
            object_locations=obj_locs,
            character_locations=char_locs,
            character_goals=char_goals,
            character_beliefs=char_beliefs,
            relationships=relationships,
        )
        self.snapshots[tick] = snap
        return snap

    def get_or_create_snapshot(self, tick: int, world: WorldState) -> WorldSnapshot:
        """Get snapshot at `tick`, or construct from current world/events if not cached."""
        if tick in self.snapshots:
            return self.snapshots[tick]
        if tick == world.current_tick:
            return self.capture_snapshot(tick, world)
        # Construct approximate historical snapshot using event reconstruction
        return self._reconstruct_snapshot(tick, world)

    def _reconstruct_snapshot(self, target_tick: int, world: WorldState) -> WorldSnapshot:
        """Reconstruct snapshot at target_tick by analyzing events up to target_tick."""
        snap = self.capture_snapshot(world.current_tick, world)
        # Adjust snapshot by rolling back events that occurred after target_tick
        events_after = [
            e for e in world.events.values()
            if getattr(e, "tick", 0) > target_tick
        ]
        # Sort descending by tick to reverse effects
        events_after.sort(key=lambda e: e.tick, reverse=True)

        for evt in events_after:
            if evt.event_type == EventType.OBJECT_PICKED_UP:
                oid = evt.metadata.get("object_id")
                if oid and oid in snap.object_holders:
                    # Before pickup, it was not held by this actor
                    snap.object_holders[oid] = None
                    snap.object_locations[oid] = evt.location_id
            elif evt.event_type == EventType.OBJECT_DROPPED:
                oid = evt.metadata.get("object_id")
                actor_id = evt.actor_ids[0] if evt.actor_ids else None
                if oid and actor_id:
                    snap.object_holders[oid] = actor_id
                    snap.object_locations[oid] = None
            elif evt.event_type == EventType.OBJECT_GIVEN:
                oid = evt.metadata.get("object_id")
                giver_id = evt.metadata.get("giver_id")
                if oid and giver_id:
                    snap.object_holders[oid] = giver_id

        snap.tick = target_tick
        return snap

    # Predicate Clause Evaluators
    def evaluate_goal_adopted(
        self,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        character_id: Optional[str] = None,
    ) -> bool:
        """Evaluates GOAL_ADOPTED: whether a new goal was adopted within the window.

        For opening beat windows starting at tick 0 (start_tick == 0), initial-state
        goals established at world initialization count as adopted for the opening setup.
        For later windows (start_tick > 0), only goals newly adopted within the window qualify.
        """
        snap_start = self.get_or_create_snapshot(start_tick, world)
        snap_end = self.get_or_create_snapshot(end_tick, world)

        # Check for any character or specific character
        chars_to_check = [character_id] if character_id else list(world.characters.keys())
        for cid in chars_to_check:
            start_goals = set(snap_start.character_goals.get(cid, []))
            end_goals = set(snap_end.character_goals.get(cid, []))
            if end_goals - start_goals:
                return True
            # For opening beats starting at tick 0, initial-state goals held at tick 0 count as adopted
            if start_tick == 0 and end_goals:
                return True

        # Also check world goals for created_at_event falling in window
        for goal in world.goals.values():
            if character_id and getattr(goal, "character_id", None) != character_id:
                continue
            if getattr(goal, "created_at_event", None):
                evt = world.events.get(goal.created_at_event)
                if evt and start_tick <= evt.tick <= end_tick:
                    return True
            elif start_tick == 0:
                return True

        return False

    def evaluate_belief_flip(
        self,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        proposition_id: Optional[str] = None,
        character_id: Optional[str] = None,
    ) -> bool:
        """Evaluates BELIEF_FLIP: whether believed_truth_value changed in the window."""
        snap_start = self.get_or_create_snapshot(start_tick, world)
        snap_end = self.get_or_create_snapshot(end_tick, world)

        chars_to_check = [character_id] if character_id else list(world.characters.keys())
        props_to_check = [proposition_id] if proposition_id else list(world.propositions.keys())

        for cid in chars_to_check:
            for pid in props_to_check:
                key = (cid, pid)
                val_start = snap_start.character_beliefs.get(key)
                val_end = snap_end.character_beliefs.get(key)
                if val_start is not None and val_end is not None and val_start != val_end:
                    return True
                # If newly formed belief in the window with opposing objective truth
                if val_start is None and val_end is not None:
                    # check if acquired in window
                    char = world.characters.get(cid)
                    if char:
                        k_item = char.knows(pid)
                        if k_item and k_item.acquired_at_event:
                            evt = world.events.get(k_item.acquired_at_event)
                            if evt and start_tick <= evt.tick <= end_tick:
                                return True
        return False

    def evaluate_possession_change(
        self,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        object_id: Optional[str] = None,
        character_id: Optional[str] = None,
    ) -> bool:
        """Evaluates POSSESSION_CHANGE: whether object holder or location changed in window."""
        snap_start = self.get_or_create_snapshot(start_tick, world)
        snap_end = self.get_or_create_snapshot(end_tick, world)

        objs_to_check = [object_id] if object_id else list(world.objects.keys())
        for oid in objs_to_check:
            holder_start = snap_start.object_holders.get(oid)
            holder_end = snap_end.object_holders.get(oid)
            if holder_start != holder_end:
                if character_id:
                    if holder_end == character_id or holder_start == character_id:
                        return True
                else:
                    return True

            loc_start = snap_start.object_locations.get(oid)
            loc_end = snap_end.object_locations.get(oid)
            if loc_start != loc_end:
                return True

        # Check events in window for explicit pickup / drop / give
        for evt in world.events.values():
            if start_tick <= evt.tick <= end_tick:
                if evt.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED, EventType.OBJECT_GIVEN):
                    evt_oid = evt.metadata.get("object_id")
                    if not object_id or evt_oid == object_id:
                        if not character_id or character_id in evt.actor_ids:
                            return True
        return False

    def evaluate_relationship_threshold_crossed(
        self,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        threshold: float,
        character_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> bool:
        """Evaluates RELATIONSHIP_THRESHOLD_CROSSED: genuine crossing during window.
        
        Must distinguish 'already above threshold at window start' from 'crossed during window'.
        """
        snap_start = self.get_or_create_snapshot(start_tick, world)
        snap_end = self.get_or_create_snapshot(end_tick, world)

        pairs = []
        if character_id and target_id:
            pairs.append((character_id, target_id))
        else:
            all_keys = set(snap_start.relationships.keys()) | set(snap_end.relationships.keys())
            for cid, tid in all_keys:
                if character_id and cid != character_id:
                    continue
                if target_id and tid != target_id:
                    continue
                pairs.append((cid, tid))

        for cid, tid in pairs:
            val_start = snap_start.relationships.get((cid, tid), 0.0)
            val_end = snap_end.relationships.get((cid, tid), 0.0)

            # Upward crossing: was <= threshold at start, strictly > threshold at end
            upward = (val_start <= threshold) and (val_end > threshold)
            # Downward crossing: was >= threshold at start, strictly < threshold at end
            downward = (val_start >= threshold) and (val_end < threshold)

            if upward or downward:
                return True

        return False

    def evaluate_secret_learned(
        self,
        world: WorldState,
        start_tick: int,
        end_tick: int,
        proposition_id: Optional[str] = None,
        character_id: Optional[str] = None,
    ) -> bool:
        """Evaluates SECRET_LEARNED: any KnowledgeItem for an is_secret proposition acquired in window."""
        chars_to_check = [world.characters[character_id]] if character_id and character_id in world.characters else list(world.characters.values())

        for char in chars_to_check:
            for pid, k_item in char.knowledge.items():
                if proposition_id and pid != proposition_id:
                    continue
                # Check if proposition is a secret
                prop = world.propositions.get(pid)
                if not prop or not getattr(prop, "is_secret", False):
                    continue

                # Check if acquired at an event within [start_tick, end_tick]
                if k_item.acquired_at_event and k_item.acquired_at_event in world.events:
                    evt = world.events[k_item.acquired_at_event]
                    if start_tick <= evt.tick <= end_tick:
                        return True

        return False

    def evaluate_clause(
        self,
        world: WorldState,
        clause: PredicateClause,
        start_tick: int,
        end_tick: int,
    ) -> bool:
        """Dispatch evaluation of an individual PredicateClause."""
        ctype = clause.type
        if ctype == "GOAL_ADOPTED":
            return self.evaluate_goal_adopted(
                world, start_tick, end_tick, character_id=clause.character
            )
        elif ctype == "BELIEF_FLIP":
            return self.evaluate_belief_flip(
                world, start_tick, end_tick, proposition_id=clause.subject, character_id=clause.character
            )
        elif ctype == "POSSESSION_CHANGE":
            return self.evaluate_possession_change(
                world, start_tick, end_tick, object_id=clause.object, character_id=clause.character
            )
        elif ctype == "RELATIONSHIP_THRESHOLD_CROSSED":
            thresh = clause.threshold if clause.threshold is not None else 0.5
            return self.evaluate_relationship_threshold_crossed(
                world, start_tick, end_tick, threshold=thresh, character_id=clause.character, target_id=clause.subject
            )
        elif ctype == "SECRET_LEARNED":
            return self.evaluate_secret_learned(
                world, start_tick, end_tick, proposition_id=clause.subject, character_id=clause.character
            )
        elif ctype == "WORLD_FACT_CHANGED":
            # Reserved for future phases per §B.4: evaluates to False
            return False

        return False
