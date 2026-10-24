"""Temporal Character Graph Projector.

Reconstructs graph snapshots and diffs at any simulation tick deterministically
using canonical WorldState, EventLog, and StateSnapshotDiffer.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict
from datetime import datetime, timezone

from ...domain.world import WorldState, Character
from ...domain.event import Event, EventType
from ...domain.conflict import ConflictGraph, ConflictEdge
from ...simulation.differ import StateSnapshotDiffer, WorldSnapshot
from .models import (
    TemporalGraphNode,
    TemporalGraphEdge,
    TemporalGraphSnapshot,
    TemporalGraphDiff,
)

ALL_RELATIONSHIP_DIMENSIONS = [
    "affinity",
    "trust",
    "affection",
    "fear",
    "dependency",
    "respect",
    "resentment",
    "suspicion",
    "power_imbalance",
]


class TemporalGraphProjector:
    """Deterministic projector for temporal character graphs and relationship evolution."""

    _cache: Dict[Tuple[str, int, str], TemporalGraphSnapshot] = {}

    @classmethod
    def clear_cache(cls, project_id: Optional[str] = None) -> None:
        """Clear cached graph projections."""
        if project_id is None:
            cls._cache.clear()
        else:
            to_del = [k for k in cls._cache.keys() if k[0] == project_id]
            for k in to_del:
                cls._cache.pop(k, None)

    @classmethod
    def project_at_tick(
        cls,
        project_id: str,
        world: WorldState,
        tick: Optional[int] = None,
        conflict_graph: Optional[ConflictGraph] = None,
        use_cache: bool = True,
    ) -> TemporalGraphSnapshot:
        """Project the character relationship graph at a specific discrete simulation tick."""
        import hashlib
        max_tick = getattr(world, "current_tick", 0)
        target_tick = max_tick if tick is None else max(0, min(tick, max_tick))

        # Compute collision-proof state digest sensitive to event modifications,
        # re-timings, additions/removals, character locations, and relationship dimensions
        history_tokens = [
            (eid, getattr(e, "tick", 0), getattr(e, "description", ""), getattr(e, "event_type", ""), tuple(sorted(getattr(e, "metadata", {}).items())))
            for eid, e in sorted(world.events.items())
        ]
        char_tokens = [
            (cid, getattr(c, "current_location_id", None), tuple(sorted(getattr(c, "knowledge", {}).keys())))
            for cid, c in sorted(world.characters.items())
        ]
        rel_tokens = [
            (rid, getattr(r, "affinity", 0.0), getattr(r, "trust", 0.0), getattr(r, "suspicion", 0.0), getattr(r, "fear", 0.0))
            for rid, r in sorted(world.relationships.items())
        ]
        state_digest = hashlib.sha256(
            repr((project_id, target_tick, max_tick, history_tokens, char_tokens, rel_tokens)).encode("utf-8")
        ).hexdigest()[:24]

        cache_key = (project_id, target_tick, state_digest)
        if use_cache and cache_key in cls._cache:
            return cls._cache[cache_key]

        differ = StateSnapshotDiffer(world)
        snap = differ.get_or_create_snapshot(target_tick, world)

        # Historical events strictly at or prior to target_tick
        events_up_to_tick = {
            eid: e for eid, e in world.events.items()
            if getattr(e, "tick", 0) <= target_tick
        }

        # 1. Build Nodes
        nodes: List[TemporalGraphNode] = []
        for cid, char in world.characters.items():
            # Determine character location at target_tick using historical move events
            past_moves = [
                e for e in world.events.values()
                if getattr(e, "event_type", None) == EventType.CHARACTER_MOVED
                and cid in getattr(e, "actor_ids", [])
                and getattr(e, "tick", 0) <= target_tick
            ]
            future_moves = [
                e for e in world.events.values()
                if getattr(e, "event_type", None) == EventType.CHARACTER_MOVED
                and cid in getattr(e, "actor_ids", [])
                and getattr(e, "tick", 0) > target_tick
            ]

            loc_id = None
            if past_moves:
                past_moves.sort(key=lambda e: getattr(e, "tick", 0))
                latest_move = past_moves[-1]
                loc_id = latest_move.location_id or latest_move.metadata.get("to_location")
            elif future_moves:
                future_moves.sort(key=lambda e: getattr(e, "tick", 0))
                earliest_future = future_moves[0]
                loc_id = earliest_future.metadata.get("from_location")

            if not loc_id:
                loc_id = snap.character_locations.get(cid) or char.current_location_id

            loc_name = world.locations[loc_id].name if loc_id and loc_id in world.locations else None

            emotions = dict(snap.character_emotions.get(cid, {}))
            if not emotions and hasattr(char, "emotional_state") and char.emotional_state:
                emotions = {
                    "happiness": getattr(char.emotional_state, "happiness", 0.0),
                    "fear": getattr(char.emotional_state, "fear", 0.0),
                    "anger": getattr(char.emotional_state, "anger", 0.0),
                    "trust": getattr(char.emotional_state, "trust", 0.0),
                    "curiosity": getattr(char.emotional_state, "curiosity", 0.0),
                }

            char_beliefs: Dict[str, bool] = {}
            for (bcid, prop_id), truth in snap.character_beliefs.items():
                if bcid == cid:
                    char_beliefs[prop_id] = truth

            # If snapshot had no beliefs yet, fallback to character's current knowledge items acquired on or before target_tick
            if not char_beliefs and hasattr(char, "knowledge"):
                for prop_id, k_item in char.knowledge.items():
                    acq_evt_id = getattr(k_item, "acquired_at_event", "")
                    if acq_evt_id:
                        acq_evt = world.events.get(acq_evt_id)
                        if acq_evt and getattr(acq_evt, "tick", 0) > target_tick:
                            continue
                    char_beliefs[prop_id] = getattr(k_item, "believed_truth_value", True)

            goals = list(snap.character_goals.get(cid, []))
            if not goals and hasattr(char, "goals"):
                goals = [g.id if hasattr(g, "id") else str(g) for g in char.goals]

            # Find active conflicts involving this character
            char_conflicts: List[Dict[str, Any]] = []
            if conflict_graph and hasattr(conflict_graph, "edges"):
                edge_iter = conflict_graph.edges.values() if isinstance(conflict_graph.edges, dict) else conflict_graph.edges
                for edge in edge_iter:
                    if edge.source_character_id == cid or edge.target_character_id == cid:
                        char_conflicts.append({
                            "peer_id": edge.target_character_id if edge.source_character_id == cid else edge.source_character_id,
                            "aggregate_intensity": edge.aggregate_intensity,
                            "dimensions": {d.value if hasattr(d, "value") else str(d): score for d, score in edge.dimensions.items()},
                        })

            secrets_count = sum(1 for s in world.secrets.values() if getattr(s, "character_id", None) == cid)
            inv_count = len(getattr(char, "inventory", []))

            nodes.append(
                TemporalGraphNode(
                    id=cid,
                    name=char.name,
                    role=char.role,
                    location_id=loc_id,
                    location_name=loc_name,
                    goals=goals,
                    beliefs=char_beliefs,
                    emotional_state=emotions,
                    active_conflicts=char_conflicts,
                    secrets_count=secrets_count,
                    inventory_count=inv_count,
                )
            )

        # 2. Build Edges
        edges: List[TemporalGraphEdge] = []
        registered_pairs: Set[Tuple[str, str]] = set()

        # Iterate over canonical relationships in world
        for rel in world.relationships.values():
            ca = rel.character_a_id
            cb = rel.character_b_id
            pair = (ca, cb)
            pair_rev = (cb, ca)

            if pair in registered_pairs or pair_rev in registered_pairs:
                continue
            registered_pairs.add(pair)

            char_a = world.characters.get(ca)
            char_b = world.characters.get(cb)
            source_name = char_a.name if char_a else ca
            target_name = char_b.name if char_b else cb

            # Extract dimensions from snapshot if present, else fallback to rel model
            snap_dims = snap.relationship_dimensions.get(pair) or snap.relationship_dimensions.get(pair_rev)
            dimensions: Dict[str, float] = {}
            for d in ALL_RELATIONSHIP_DIMENSIONS:
                if snap_dims and d in snap_dims:
                    dimensions[d] = float(snap_dims[d])
                else:
                    dimensions[d] = float(getattr(rel, d, 0.0))

            # Filter evidence events: provenance event IDs that occurred at or before target_tick
            all_prov_ids: Set[str] = set()
            for d, eids in getattr(rel, "event_provenance", {}).items():
                for eid in eids:
                    if eid in events_up_to_tick:
                        all_prov_ids.add(eid)

            # Also include direct events between ca and cb that occurred up to target_tick
            for eid, evt in events_up_to_tick.items():
                actors = set(getattr(evt, "actor_ids", []))
                if ca in actors and cb in actors:
                    all_prov_ids.add(eid)

            evidence_event_ids = sorted(
                list(all_prov_ids),
                key=lambda eid: events_up_to_tick[eid].tick if eid in events_up_to_tick else 0,
            )

            recent_event_id = evidence_event_ids[-1] if evidence_event_ids else None
            first_tick = events_up_to_tick[evidence_event_ids[0]].tick if evidence_event_ids else 0
            last_tick = events_up_to_tick[evidence_event_ids[-1]].tick if evidence_event_ids else 0

            # Compute aggregate intensity (0.0 - 1.0)
            dim_values = list(dimensions.values())
            aggregate_intensity = round(sum(abs(v) for v in dim_values) / max(len(dim_values), 1), 3)

            # Derive high-level relationship type
            rel_type = cls._classify_relationship_type(dimensions)

            edges.append(
                TemporalGraphEdge(
                    id=rel.id if hasattr(rel, "id") and rel.id else f"rel_{ca}_{cb}",
                    source_id=ca,
                    target_id=cb,
                    source_name=source_name,
                    target_name=target_name,
                    relationship_type=rel_type,
                    dimensions=dimensions,
                    aggregate_intensity=aggregate_intensity,
                    directionality="mutual",
                    evidence_event_ids=evidence_event_ids,
                    recent_event_id=recent_event_id,
                    first_observed_tick=first_tick,
                    last_changed_tick=last_tick,
                )
            )

        summary = (
            f"Projection at Tick {target_tick} / {max_tick}: {len(nodes)} character node(s), "
            f"{len(edges)} relationship edge(s) established. "
            f"Observed {len(events_up_to_tick)} historical event(s)."
        )

        snapshot = TemporalGraphSnapshot(
            project_id=project_id,
            tick=target_tick,
            max_tick=max_tick,
            nodes=nodes,
            edges=edges,
            event_count=len(events_up_to_tick),
            summary=summary,
        )

        if use_cache:
            cls._cache[cache_key] = snapshot

        return snapshot

    @classmethod
    def compute_diff(
        cls,
        snapshot_a: TemporalGraphSnapshot,
        snapshot_b: TemporalGraphSnapshot,
        world: Optional[WorldState] = None,
    ) -> TemporalGraphDiff:
        """Compute state and relationship differences between two snapshots."""
        start_tick = min(snapshot_a.tick, snapshot_b.tick)
        end_tick = max(snapshot_a.tick, snapshot_b.tick)

        # Match snapshots chronologically: earlier -> later
        earlier = snapshot_a if snapshot_a.tick <= snapshot_b.tick else snapshot_b
        later = snapshot_b if snapshot_b.tick >= snapshot_a.tick else snapshot_a

        # 1. Causal events strictly between start_tick and end_tick
        causal_event_ids: List[str] = []
        if world:
            causal_event_ids = sorted(
                [
                    eid for eid, e in world.events.items()
                    if start_tick < getattr(e, "tick", 0) <= end_tick
                ],
                key=lambda eid: world.events[eid].tick,
            )

        # 2. Node Changes
        node_changes: List[Dict[str, Any]] = []
        earlier_nodes = {n.id: n for n in earlier.nodes}
        later_nodes = {n.id: n for n in later.nodes}

        for cid, node_l in later_nodes.items():
            if cid not in earlier_nodes:
                node_changes.append({
                    "character_id": cid,
                    "change_type": "node_added",
                    "description": f"{node_l.name} introduced to simulation",
                })
                continue

            node_e = earlier_nodes[cid]
            # Location change
            if node_e.location_id != node_l.location_id:
                node_changes.append({
                    "character_id": cid,
                    "change_type": "location_changed",
                    "from_location": node_e.location_name or node_e.location_id,
                    "to_location": node_l.location_name or node_l.location_id,
                    "description": f"{node_l.name} moved from {node_e.location_name or 'unknown'} to {node_l.location_name or 'unknown'}",
                })

            # Emotion shifts
            emotion_deltas: Dict[str, float] = {}
            for em, val_l in node_l.emotional_state.items():
                val_e = node_e.emotional_state.get(em, 0.0)
                delta = round(val_l - val_e, 3)
                if abs(delta) >= 0.05:
                    emotion_deltas[em] = delta

            if emotion_deltas:
                node_changes.append({
                    "character_id": cid,
                    "change_type": "emotions_shifted",
                    "deltas": emotion_deltas,
                    "description": f"{node_l.name} experienced emotional shifts: " + ", ".join(f"{k} ({v:+0.2f})" for k, v in emotion_deltas.items()),
                })

            # Belief changes
            changed_beliefs: List[str] = []
            for prop_id, truth_l in node_l.beliefs.items():
                if prop_id in node_e.beliefs and node_e.beliefs[prop_id] != truth_l:
                    changed_beliefs.append(f"{prop_id}: was {node_e.beliefs[prop_id]} -> now {truth_l}")
                elif prop_id not in node_e.beliefs:
                    changed_beliefs.append(f"{prop_id}: newly acquired (believed={truth_l})")

            if changed_beliefs:
                node_changes.append({
                    "character_id": cid,
                    "change_type": "beliefs_changed",
                    "details": changed_beliefs,
                    "description": f"{node_l.name} updated beliefs: " + "; ".join(changed_beliefs),
                })

        # 3. Edge Changes
        edge_changes: List[Dict[str, Any]] = []
        earlier_edges = {e.id: e for e in earlier.edges}
        later_edges = {e.id: e for e in later.edges}

        for edge_id, edge_l in later_edges.items():
            if edge_id not in earlier_edges:
                edge_changes.append({
                    "edge_id": edge_id,
                    "source_id": edge_l.source_id,
                    "target_id": edge_l.target_id,
                    "change_type": "edge_formed",
                    "description": f"Relationship established between {edge_l.source_name} and {edge_l.target_name}",
                })
                continue

            edge_e = earlier_edges[edge_id]
            dim_deltas: Dict[str, float] = {}
            for d in ALL_RELATIONSHIP_DIMENSIONS:
                val_e = edge_e.dimensions.get(d, 0.0)
                val_l = edge_l.dimensions.get(d, 0.0)
                delta = round(val_l - val_e, 3)
                if abs(delta) >= 0.05:
                    dim_deltas[d] = delta

            new_events = [eid for eid in edge_l.evidence_event_ids if eid not in edge_e.evidence_event_ids]

            if dim_deltas or edge_e.relationship_type != edge_l.relationship_type:
                edge_changes.append({
                    "edge_id": edge_id,
                    "source_id": edge_l.source_id,
                    "target_id": edge_l.target_id,
                    "source_name": edge_l.source_name,
                    "target_name": edge_l.target_name,
                    "change_type": "dimensions_shifted",
                    "previous_type": edge_e.relationship_type,
                    "new_type": edge_l.relationship_type,
                    "deltas": dim_deltas,
                    "new_evidence_events": new_events,
                    "description": (
                        f"Relationship between {edge_l.source_name} and {edge_l.target_name} shifted ({edge_e.relationship_type} -> {edge_l.relationship_type}): "
                        + ", ".join(f"{k} ({v:+0.2f})" for k, v in dim_deltas.items())
                    ),
                })

        summary = (
            f"Temporal Diff from Tick {start_tick} to {end_tick}: "
            f"{len(node_changes)} character delta(s), {len(edge_changes)} relationship shift(s), "
            f"{len(causal_event_ids)} intervening causal event(s)."
        )

        return TemporalGraphDiff(
            project_id=later.project_id,
            from_tick=start_tick,
            to_tick=end_tick,
            node_changes=node_changes,
            edge_changes=edge_changes,
            causal_event_ids=causal_event_ids,
            summary=summary,
        )

    @staticmethod
    def _classify_relationship_type(dimensions: Dict[str, float]) -> str:
        """Deterministically classify high-level relationship archetype based on multidimensional values."""
        affinity = dimensions.get("affinity", 0.0)
        trust = dimensions.get("trust", 0.0)
        resentment = dimensions.get("resentment", 0.0)
        suspicion = dimensions.get("suspicion", 0.0)
        fear = dimensions.get("fear", 0.0)
        affection = dimensions.get("affection", 0.0)

        if affinity >= 0.4 and trust >= 0.3:
            return "allies"
        if affinity <= -0.3 or resentment >= 0.4:
            return "hostile"
        if suspicion >= 0.4 or fear >= 0.4:
            return "guarded"
        if affection >= 0.4 and trust < 0.2:
            return "conflicted"
        if abs(affinity) < 0.2 and abs(trust) < 0.2 and abs(resentment) < 0.2:
            return "neutral"
        return "complex"
