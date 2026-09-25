"""Deterministic dramatic signal extraction service for D3 Story Lab.

Extracts pure, read-only dramatic signals (unresolved conflicts, relationship threshold
crossings, archetype shifts, dramatic need opportunities, secret revelations, and belief flips)
for use by Director Agent, Sufficiency Gate, and Observer without mutating state or violating
character autonomy.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from ..domain.world import WorldState
from ..domain.character import Character
from ..domain.relationship import Relationship
from ..domain.event import Event, EventType
from ..domain.conflict import ConflictEdge, ConflictGraph, ConflictDimension
from ..domain.archetype import ArchetypeType, ArchetypeShiftPoint
from ..narrative.conflict_engine import ConflictEngine
from ..narrative.archetype_analyzer import ArchetypeTrajectoryAnalyzer


class DramaticSignalsReport(BaseModel):
    """Immutable report of current dramatic signals derived from canonical world state and event history."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    unresolved_conflicts: List[ConflictEdge] = Field(default_factory=list)
    threshold_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    stalled_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    archetype_shifts: List[Dict[str, Any]] = Field(default_factory=list)
    dramatic_need_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    secret_revelations: List[Dict[str, Any]] = Field(default_factory=list)
    belief_flips: List[Dict[str, Any]] = Field(default_factory=list)

    has_major_conflict_escalation: bool = False
    has_relationship_threshold_crossing: bool = False
    has_secret_revelation: bool = False
    has_belief_flip: bool = False
    has_arc_movement: bool = False
    unresolved_tension_level: float = 0.0  # Normalized 0.0 .. 1.0


def get_unresolved_conflicts(
    world: WorldState,
    min_intensity: float = 0.5,
    existing_graph: Optional[ConflictGraph] = None,
) -> List[ConflictEdge]:
    """Derive pairwise conflicts and filter for high-intensity unresolved conflict edges.

    Analytical and read-only.
    """
    graph = ConflictEngine.derive_conflict_graph(
        world=world,
        project_id=world.id,
        existing_graph=existing_graph,
    )
    unresolved = [
        edge for edge in graph.edges
        if edge.aggregate_intensity >= min_intensity
    ]
    return unresolved


def get_relationship_threshold_crossings(
    world: WorldState,
    events: Optional[List[Event]] = None,
    differ: Optional[Any] = None,
    threshold_abs: float = 0.6,
) -> List[Dict[str, Any]]:
    """Detect relationships where multidimensional attributes have reached significant dramatic thresholds.

    Examines trust, respect, resentment, suspicion, fear, affection, affinity, and power imbalance.
    """
    crossings: List[Dict[str, Any]] = []

    # 1. Current state dimension inspection
    dimensions_to_check = [
        "trust", "affection", "fear", "dependency", "respect",
        "resentment", "suspicion", "affinity", "power_imbalance"
    ]

    for rel_id, rel in world.relationships.items():
        for dim in dimensions_to_check:
            val = getattr(rel, dim, 0.0)
            if abs(val) >= threshold_abs or (dim in ("resentment", "suspicion", "fear") and val >= 0.5):
                crossings.append({
                    "relationship_id": rel_id,
                    "character_a_id": rel.character_a_id,
                    "character_b_id": rel.character_b_id,
                    "dimension": dim,
                    "value": val,
                    "threshold_type": "extreme_magnitude" if abs(val) >= threshold_abs else "high_negative_tension",
                    "provenance_event_id": rel.dimension_provenance.get(dim) if hasattr(rel, "dimension_provenance") else None,
                })

    # 2. Event-based threshold crossing markers
    if events:
        for ev in events:
            if ev.event_type == EventType.RELATIONSHIP_CHANGED:
                meta = ev.metadata or {}
                if meta.get("threshold_crossing") or meta.get("major_shift"):
                    crossings.append({
                        "relationship_id": meta.get("relationship_id", f"rel_{ev.id}"),
                        "character_a_id": ev.actor_ids[0] if ev.actor_ids else "unknown",
                        "character_b_id": ev.actor_ids[1] if len(ev.actor_ids) > 1 else "unknown",
                        "dimension": meta.get("dimension", "affinity"),
                        "value": meta.get("new_value", 0.0),
                        "threshold_type": "event_threshold_crossing",
                        "provenance_event_id": ev.id,
                    })

    return crossings


def get_stalled_relationships(
    world: WorldState,
    inactivity_ticks: int = 3,
) -> List[Dict[str, Any]]:
    """Detect co-located characters with high latent tension (suspicion/resentment) but no resolution."""
    stalled: List[Dict[str, Any]] = []

    chars = list(world.characters.values())
    for i in range(len(chars)):
        for j in range(i + 1, len(chars)):
            char_a = chars[i]
            char_b = chars[j]

            # Co-location check
            if char_a.current_location_id and char_a.current_location_id == char_b.current_location_id:
                # Find relationship
                rel_ab = None
                for rel in world.relationships.values():
                    if (rel.character_a_id == char_a.id and rel.character_b_id == char_b.id) or \
                       (rel.character_a_id == char_b.id and rel.character_b_id == char_a.id):
                        rel_ab = rel
                        break

                if rel_ab:
                    high_tension = (
                        getattr(rel_ab, "suspicion", 0.0) >= 0.4 or
                        getattr(rel_ab, "resentment", 0.0) >= 0.4 or
                        getattr(rel_ab, "trust", 0.0) <= -0.4 or
                        getattr(rel_ab, "fear", 0.0) >= 0.4
                    )
                    if high_tension:
                        stalled.append({
                            "character_a_id": char_a.id,
                            "character_b_id": char_b.id,
                            "location_id": char_a.current_location_id,
                            "tension_dimension": "suspicion" if getattr(rel_ab, "suspicion", 0.0) >= 0.4 else "resentment",
                            "severity": round(max(
                                getattr(rel_ab, "suspicion", 0.0),
                                getattr(rel_ab, "resentment", 0.0),
                                getattr(rel_ab, "fear", 0.0),
                            ), 2),
                        })

    return stalled


def get_archetype_movements(
    world: WorldState,
    events: Optional[List[Event]] = None,
    differ: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Detect characters who have undergone archetype shifts or significant drift."""
    if not events:
        events = list(world.events.values())

    movements: List[Dict[str, Any]] = []
    for char_id, char in world.characters.items():
        if not char.dynamics or not char.dynamics.primary_archetype:
            continue

        traj = ArchetypeTrajectoryAnalyzer.analyze_trajectory(
            character_id=char_id,
            world=world,
            events=events,
            differ=differ,
        )
        if traj.shift_points:
            for sp in traj.shift_points:
                movements.append({
                    "character_id": char_id,
                    "character_name": char.name,
                    "tick": sp.tick,
                    "dominant_archetype": sp.dominant_archetype.value if hasattr(sp.dominant_archetype, "value") else str(sp.dominant_archetype),
                    "confidence": getattr(sp, "confidence", 1.0),
                    "evidence_event_ids": getattr(sp, "evidence_event_ids", []),
                    "reason": getattr(sp, "rationale", ""),
                })
        elif traj.current_dominant_archetype and traj.current_dominant_archetype != traj.initial_archetype:
            movements.append({
                "character_id": char_id,
                "character_name": char.name,
                "tick": world.current_tick,
                "dominant_archetype": traj.current_dominant_archetype.value if hasattr(traj.current_dominant_archetype, "value") else str(traj.current_dominant_archetype),
                "confidence": getattr(traj, "stability_score", 1.0),
                "evidence_event_ids": [],
                "reason": "Dominant archetype drift observed over simulation trajectory.",
            })

    return movements


def get_dramatic_need_opportunities(
    world: WorldState,
) -> List[Dict[str, Any]]:
    """Identify analytical dramatic_need signals that suggest world-level thematic challenges.

    CRITICAL INVARIANT:
    dramatic_need remains analytical only. It must NEVER be projected to a Goal or force character actions.
    Director uses this only to introduce environmental context (clues, objects, deadlines) that
    gives characters thematic opportunities to grow or confront flaws.
    """
    opportunities: List[Dict[str, Any]] = []

    for char_id, char in world.characters.items():
        if not char.dynamics or not char.dynamics.dramatic_need:
            continue

        need_text = char.dynamics.dramatic_need.lower()
        theme = "general"
        suggested_pressure = "NEW_INFORMATION"

        if any(w in need_text for w in ["truth", "culpability", "honesty", "admit", "confess"]):
            theme = "truth_revelation"
            suggested_pressure = "REVEAL_CLUE"
        elif any(w in need_text for w in ["trust", "ally", "allies", "vulnerability", "depend"]):
            theme = "trust_test"
            suggested_pressure = "INTRODUCE_OBSTACLE"
        elif any(w in need_text for w in ["risk", "safety", "courage", "danger", "cowardice"]):
            theme = "courage_test"
            suggested_pressure = "ENVIRONMENTAL_EVENT"
        elif any(w in need_text for w in ["ambition", "cost", "greed", "moral"]):
            theme = "moral_cost"
            suggested_pressure = "ANNOUNCE_DEADLINE"
        elif any(w in need_text for w in ["identity", "deception", "mask", "pretend"]):
            theme = "identity_confrontation"
            suggested_pressure = "NEW_INFORMATION"

        opportunities.append({
            "character_id": char_id,
            "character_name": char.name,
            "dramatic_need": char.dynamics.dramatic_need,
            "theme": theme,
            "suggested_pressure": suggested_pressure,
            "location_id": char.current_location_id,
        })

    return opportunities


def detect_secret_revelations(
    world: WorldState,
    events: Optional[List[Event]] = None,
) -> List[Dict[str, Any]]:
    """Detect secrets or secret propositions that have been revealed to others."""
    revelations: List[Dict[str, Any]] = []

    # 1. World secrets model
    for sec_id, secret in world.secrets.items():
        if secret.known_by:
            revelations.append({
                "secret_id": sec_id,
                "statement": secret.statement,
                "holder_id": secret.character_id,
                "revealed_to": list(secret.known_by),
                "source": "secret_model",
            })

    # 2. Canonical propositions
    for prop_id, prop in world.propositions.items():
        if getattr(prop, "is_secret", False):
            # Check characters who know it
            knowers = []
            for char_id, char in world.characters.items():
                if prop_id in getattr(char, "knowledge", {}):
                    knowers.append(char_id)
            if len(knowers) > 1:
                revelations.append({
                    "secret_id": prop_id,
                    "statement": f"{prop.subject} {prop.predicate} {prop.object}",
                    "holder_id": knowers[0],
                    "revealed_to": knowers[1:],
                    "source": "proposition_knowledge",
                })

    # 3. Events with secret_revealed metadata or keywords
    if events:
        for ev in events:
            desc = (ev.description or "").lower()
            meta = ev.metadata or {}
            if meta.get("secret_revealed") or meta.get("speech_act") == "reveal" or \
               ("reveal" in desc and any(w in desc for w in ["secret", "truth", "clue", "ledger", "dossier"])):
                revelations.append({
                    "secret_id": meta.get("secret_id", f"sec_event_{ev.id}"),
                    "statement": ev.description,
                    "holder_id": ev.actor_ids[0] if ev.actor_ids else "unknown",
                    "revealed_to": ev.actor_ids[1:] if len(ev.actor_ids) > 1 else [],
                    "provenance_event_id": ev.id,
                    "source": "event_log",
                })

    return revelations


def detect_belief_flips(
    world: WorldState,
    events: Optional[List[Event]] = None,
) -> List[Dict[str, Any]]:
    """Detect significant changes or reversals in character beliefs."""
    flips: List[Dict[str, Any]] = []

    if events:
        for ev in events:
            desc = (ev.description or "").lower()
            meta = ev.metadata or {}
            if meta.get("belief_flip") or "believes" in desc and "now" in desc:
                flips.append({
                    "event_id": ev.id,
                    "character_id": ev.actor_ids[0] if ev.actor_ids else meta.get("character_id", "unknown"),
                    "statement": meta.get("statement", ev.description),
                    "old_confidence": meta.get("old_confidence", 0.8),
                    "new_confidence": meta.get("new_confidence", 0.2),
                })
            elif ev.event_type == EventType.BELIEF_FORMED and meta.get("inverted"):
                flips.append({
                    "event_id": ev.id,
                    "character_id": ev.actor_ids[0] if ev.actor_ids else "unknown",
                    "statement": ev.description,
                    "old_confidence": meta.get("old_confidence", 0.9),
                    "new_confidence": meta.get("new_confidence", 0.1),
                })

    return flips


def extract_dramatic_signals(
    world: WorldState,
    events: Optional[List[Event]] = None,
    differ: Optional[Any] = None,
    existing_graph: Optional[ConflictGraph] = None,
) -> DramaticSignalsReport:
    """Central pure function to extract all dramatic signals for Director, Sufficiency Gate, and Observer."""
    if events is None:
        events = list(world.events.values())

    unresolved_conflicts = get_unresolved_conflicts(world, min_intensity=0.5, existing_graph=existing_graph)
    threshold_rels = get_relationship_threshold_crossings(world, events=events, differ=differ)
    stalled_rels = get_stalled_relationships(world)
    archetype_shifts = get_archetype_movements(world, events=events, differ=differ)
    dramatic_needs = get_dramatic_need_opportunities(world)
    secrets_revealed = detect_secret_revelations(world, events=events)
    belief_flips = detect_belief_flips(world, events=events)

    # Escalation detection
    has_conflict_escalation = any(edge.aggregate_intensity >= 0.7 for edge in unresolved_conflicts)
    if not has_conflict_escalation and events:
        for ev in events[-5:]:
            desc = (ev.description or "").lower()
            if any(w in desc for w in ["confront", "accuse", "threat", "draws weapon", "standoff"]):
                has_conflict_escalation = True
                break

    has_rel_threshold = len(threshold_rels) > 0
    has_secrets = len(secrets_revealed) > 0
    has_beliefs = len(belief_flips) > 0
    has_arc = len(archetype_shifts) > 0

    # Calculate aggregate unresolved tension level (0.0 to 1.0)
    max_conflict = max([edge.aggregate_intensity for edge in unresolved_conflicts], default=0.0)
    rel_tension = min(1.0, len(stalled_rels) * 0.25)
    unresolved_tension = round(min(1.0, max_conflict * 0.7 + rel_tension * 0.3), 2)

    return DramaticSignalsReport(
        unresolved_conflicts=unresolved_conflicts,
        threshold_relationships=threshold_rels,
        stalled_relationships=stalled_rels,
        archetype_shifts=archetype_shifts,
        dramatic_need_opportunities=dramatic_needs,
        secret_revelations=secrets_revealed,
        belief_flips=belief_flips,
        has_major_conflict_escalation=has_conflict_escalation,
        has_relationship_threshold_crossing=has_rel_threshold,
        has_secret_revelation=has_secrets,
        has_belief_flip=has_beliefs,
        has_arc_movement=has_arc,
        unresolved_tension_level=unresolved_tension,
    )
