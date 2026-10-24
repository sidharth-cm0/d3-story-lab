"""Comprehensive tests for the Temporal Character Graph System.

Verifies:
1. Snapshot reconstruction at discrete simulation ticks.
2. Invariant: Replay continuity and determinism (same inputs -> identical graph snapshot).
3. Invariant: Non-mutating (purely derived/observational, zero world state changes).
4. Invariant: Event provenance (verifiable event IDs attached to edges and diffs).
5. Multidimensional relationship edge modeling.
6. Temporal graph diff calculation (node shifts, edge deltas, intervening causal events).
7. Caching and invalidation.
"""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.domain.relationship import Relationship
from src.domain.event import Event, EventType
from src.domain.secret import Secret
from src.domain.conflict import ConflictGraph, ConflictEdge, ConflictDimension
from src.narrative.temporal_graph.models import (
    TemporalGraphNode,
    TemporalGraphEdge,
    TemporalGraphSnapshot,
    TemporalGraphDiff,
)
from src.narrative.temporal_graph.projector import TemporalGraphProjector


@pytest.fixture
def sample_world_with_timeline():
    """Create a realistic world with simulated events across multiple ticks."""
    loc_dock = Location(id="loc_dock", name="Docks", description="Foggy docks", connected_locations=["loc_warehouse"])
    loc_wh = Location(id="loc_warehouse", name="Warehouse", description="Old warehouse", connected_locations=["loc_dock"])

    char_cross = Character(
        id="char_cross",
        name="Evelyn Cross",
        role="Detective",
        current_location_id="loc_warehouse",
        emotional_state=EmotionalState(trust=0.2, fear=0.1, anger=0.3),
    )
    char_vane = Character(
        id="char_vane",
        name="Vincent Vane",
        role="Smuggler",
        current_location_id="loc_warehouse",
        emotional_state=EmotionalState(trust=-0.2, fear=0.4, anger=0.5),
    )

    rel_cv = Relationship(
        id="rel_cross_vane",
        character_a_id="char_cross",
        character_b_id="char_vane",
        affinity=-0.4,
        trust=-0.3,
        suspicion=0.8,
        fear=0.2,
        resentment=0.5,
        event_provenance={
            "suspicion": ["evt_01"],
            "resentment": ["evt_02"],
        },
    )

    events = {
        "evt_01": Event(
            id="evt_01",
            tick=1,
            event_type=EventType.CHARACTER_MOVED,
            actor_ids=["char_cross"],
            location_id="loc_warehouse",
            description="Cross arrives at warehouse",
        ),
        "evt_02": Event(
            id="evt_02",
            tick=3,
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_cross", "char_vane"],
            location_id="loc_warehouse",
            description="Cross interrogates Vane regarding stolen manifests",
            metadata={"delta_suspicion": 0.3, "delta_resentment": 0.4},
        ),
        "evt_03": Event(
            id="evt_03",
            tick=5,
            event_type=EventType.CHARACTER_MOVED,
            actor_ids=["char_vane"],
            location_id="loc_dock",
            description="Vane flees to the docks",
            metadata={"from_location": "loc_warehouse", "to_location": "loc_dock"},
        ),
    }

    world = WorldState(
        id="world_test",
        name="Test World",
        current_tick=5,
        locations={"loc_dock": loc_dock, "loc_warehouse": loc_wh},
        characters={"char_cross": char_cross, "char_vane": char_vane},
        relationships={"rel_cross_vane": rel_cv},
        events=events,
    )
    return world


def test_temporal_graph_snapshot_projection(sample_world_with_timeline):
    """Verify projection at discrete ticks filters events and reconstructs state correctly."""
    TemporalGraphProjector.clear_cache()

    snap_tick_1 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=1)
    assert snap_tick_1.tick == 1
    assert snap_tick_1.max_tick == 5
    assert snap_tick_1.event_count == 1
    assert len(snap_tick_1.nodes) == 2
    assert len(snap_tick_1.edges) == 1

    # At tick 1, evt_02 (tick 3) and evt_03 (tick 5) should NOT be in edge evidence
    edge_t1 = snap_tick_1.edges[0]
    assert "evt_02" not in edge_t1.evidence_event_ids
    assert "evt_03" not in edge_t1.evidence_event_ids

    # At tick 5 (latest tick)
    snap_tick_5 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=5)
    assert snap_tick_5.tick == 5
    assert snap_tick_5.event_count == 3
    edge_t5 = snap_tick_5.edges[0]
    assert "evt_01" in edge_t5.evidence_event_ids
    assert "evt_02" in edge_t5.evidence_event_ids
    assert edge_t5.recent_event_id in ("evt_02", "evt_01")


def test_determinism_and_replay_continuity(sample_world_with_timeline):
    """Verify that multiple projections at the exact same tick produce identical output."""
    TemporalGraphProjector.clear_cache()

    snap_a = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=3, use_cache=False)
    snap_b = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=3, use_cache=False)

    assert snap_a.tick == snap_b.tick
    assert snap_a.event_count == snap_b.event_count
    assert len(snap_a.nodes) == len(snap_b.nodes)
    for n1, n2 in zip(snap_a.nodes, snap_b.nodes):
        assert n1.id == n2.id
        assert n1.location_id == n2.location_id
        assert n1.emotional_state == n2.emotional_state

    for e1, e2 in zip(snap_a.edges, snap_b.edges):
        assert e1.id == e2.id
        assert e1.dimensions == e2.dimensions
        assert e1.relationship_type == e2.relationship_type
        assert e1.evidence_event_ids == e2.evidence_event_ids


def test_temporal_graph_diff_calculation(sample_world_with_timeline):
    """Verify diff calculation between tick 1 and tick 5 captures node movements and intervening causal events."""
    TemporalGraphProjector.clear_cache()

    snap_1 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=1)
    snap_5 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=5)

    diff = TemporalGraphProjector.compute_diff(snap_1, snap_5, world=sample_world_with_timeline)

    assert diff.from_tick == 1
    assert diff.to_tick == 5
    # Causal events between tick 1 and 5 are evt_02 (tick 3) and evt_03 (tick 5)
    assert "evt_02" in diff.causal_event_ids
    assert "evt_03" in diff.causal_event_ids
    assert "evt_01" not in diff.causal_event_ids

    # Character Vane moved to docks
    vane_loc_change = [
        nc for nc in diff.node_changes
        if nc.get("character_id") == "char_vane" and nc.get("change_type") == "location_changed"
    ]
    assert len(vane_loc_change) >= 1
    assert "Docks" in vane_loc_change[0]["to_location"] or "loc_dock" in vane_loc_change[0]["to_location"]


def test_zero_mutation_sovereignty(sample_world_with_timeline):
    """Temporal graph must NEVER mutate canonical WorldState or EventLog."""
    TemporalGraphProjector.clear_cache()
    initial_event_count = len(sample_world_with_timeline.events)
    initial_char_count = len(sample_world_with_timeline.characters)
    initial_tick = sample_world_with_timeline.current_tick

    snap = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=2)
    _ = TemporalGraphProjector.compute_diff(snap, snap, world=sample_world_with_timeline)

    assert len(sample_world_with_timeline.events) == initial_event_count
    assert len(sample_world_with_timeline.characters) == initial_char_count
    assert sample_world_with_timeline.current_tick == initial_tick


def test_multidimensional_edges_and_conflict_enrichment(sample_world_with_timeline):
    """Verify edge contains all 9 dimensions and merges analytical conflict data."""
    TemporalGraphProjector.clear_cache()

    conflict_graph = ConflictGraph(
        project_id="proj_test",
        edges=[
            ConflictEdge(
                source_character_id="char_cross",
                target_character_id="char_vane",
                dimensions={ConflictDimension.GOAL_OPPOSITION: 0.85},
            )
        ],
    )

    snap = TemporalGraphProjector.project_at_tick(
        "proj_test",
        sample_world_with_timeline,
        tick=5,
        conflict_graph=conflict_graph,
    )

    edge = snap.edges[0]
    assert "affinity" in edge.dimensions
    assert "trust" in edge.dimensions
    assert "fear" in edge.dimensions
    assert "suspicion" in edge.dimensions
    assert "resentment" in edge.dimensions
    assert edge.aggregate_intensity > 0.0

    # Node has active conflicts populated
    node_cross = next(n for n in snap.nodes if n.id == "char_cross")
    assert len(node_cross.active_conflicts) == 1
    assert node_cross.active_conflicts[0]["peer_id"] == "char_vane"


def test_temporal_graph_api_endpoints():
    """Verify temporal graph endpoints function through FastAPI TestClient."""
    import tempfile
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)

        create_res = client.post(
            "/api/projects",
            json={
                "seed_prompt": "Two rival couriers race across an abandoned space station to claim a forgotten cargo capsule.",
                "title": "Station Orbit",
            },
        )
        assert create_res.status_code == 200
        proj_id = create_res.json()["id"]

        client.post(f"/api/projects/{proj_id}/step", json={"ticks": 2})

        # 1. Graph snapshot endpoint at default (current) tick
        graph_res = client.get(f"/api/projects/{proj_id}/graph")
        assert graph_res.status_code == 200
        snapshot_data = graph_res.json()
        assert "nodes" in snapshot_data
        assert "edges" in snapshot_data
        assert "tick" in snapshot_data
        assert snapshot_data["max_tick"] >= 2

        # 2. Graph snapshot endpoint at specific tick 0
        graph_t0 = client.get(f"/api/projects/{proj_id}/graph?tick=0")
        assert graph_t0.status_code == 200
        assert graph_t0.json()["tick"] == 0

        # 3. Graph diff endpoint between tick 0 and tick 2
        diff_res = client.get(f"/api/projects/{proj_id}/graph/diff?from_tick=0&to_tick=2")
        assert diff_res.status_code == 200
        diff_data = diff_res.json()
        assert diff_data["from_tick"] == 0
        assert diff_data["to_tick"] == 2
        assert "node_changes" in diff_data
        assert "edge_changes" in diff_data
        assert "summary" in diff_data


def test_cache_invalidation_on_event_content_modification(sample_world_with_timeline):
    """Event changes with same event count MUST invalidate the projection cache via SHA-256 state digest."""
    TemporalGraphProjector.clear_cache()
    proj_id = "proj_cache_test"

    snap_before = TemporalGraphProjector.project_at_tick(proj_id, sample_world_with_timeline, tick=3)
    edge_before = snap_before.edges[0]

    # Mutate event without changing event count
    sample_world_with_timeline.events["evt_02"].metadata["delta_suspicion"] = 0.95
    sample_world_with_timeline.relationships["rel_cross_vane"].suspicion = 0.95

    snap_after = TemporalGraphProjector.project_at_tick(proj_id, sample_world_with_timeline, tick=3)
    edge_after = snap_after.edges[0]

    # New projection must reflect the updated suspicion and not return stale cached snapshot
    assert edge_after.dimensions["suspicion"] == 0.95


def test_cache_isolation_across_different_projects(sample_world_with_timeline):
    """Projections with same ticks across different project IDs must never collide or cross-contaminate."""
    TemporalGraphProjector.clear_cache()

    snap_a = TemporalGraphProjector.project_at_tick("proj_alpha", sample_world_with_timeline, tick=3)
    snap_b = TemporalGraphProjector.project_at_tick("proj_beta", sample_world_with_timeline, tick=3)

    assert snap_a.project_id == "proj_alpha"
    assert snap_b.project_id == "proj_beta"

    # Clearing one project must not clear the other
    TemporalGraphProjector.clear_cache(project_id="proj_alpha")
    cache_keys = list(TemporalGraphProjector._cache.keys())
    assert any(k[0] == "proj_beta" for k in cache_keys)
    assert not any(k[0] == "proj_alpha" for k in cache_keys)


def test_diff_boundaries_exact_half_open_interval(sample_world_with_timeline):
    """Causal events between start_tick and end_tick must strictly be in (start_tick, end_tick]."""
    TemporalGraphProjector.clear_cache()

    snap_1 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=1)
    snap_3 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=3)
    snap_5 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=5)

    diff_1_to_3 = TemporalGraphProjector.compute_diff(snap_1, snap_3, world=sample_world_with_timeline)
    # evt_01 is at tick 1 -> EXCLUDED
    # evt_02 is at tick 3 -> INCLUDED
    assert "evt_01" not in diff_1_to_3.causal_event_ids
    assert "evt_02" in diff_1_to_3.causal_event_ids
    assert "evt_03" not in diff_1_to_3.causal_event_ids

    diff_3_to_5 = TemporalGraphProjector.compute_diff(snap_3, snap_5, world=sample_world_with_timeline)
    # evt_02 is at tick 3 -> EXCLUDED
    # evt_03 is at tick 5 -> INCLUDED
    assert "evt_02" not in diff_3_to_5.causal_event_ids
    assert "evt_03" in diff_3_to_5.causal_event_ids

    diff_same = TemporalGraphProjector.compute_diff(snap_1, snap_1, world=sample_world_with_timeline)
    assert diff_same.causal_event_ids == []


def test_unknown_values_remain_unknown_instead_of_defaulting(sample_world_with_timeline):
    """Unset character location or emotions must remain None / empty rather than fabricating 0 or placeholder."""
    from src.domain.character import Character

    # Create character without location or emotional_state
    ghost_char = Character(
        id="char_ghost",
        name="Ghost Informant",
        role="Watcher",
        current_location_id=None,
        emotional_state=None,
    )
    sample_world_with_timeline.characters["char_ghost"] = ghost_char

    snap = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=1, use_cache=False)
    ghost_node = next(n for n in snap.nodes if n.id == "char_ghost")

    assert ghost_node.location_id is None
    assert ghost_node.location_name is None
    assert ghost_node.emotional_state == {}


def test_character_belief_historical_boundaries(sample_world_with_timeline):
    """Character beliefs learned in future ticks must NOT appear in earlier historical snapshots."""
    from src.domain.proposition import KnowledgeItem

    # Add a knowledge item acquired at evt_03 (tick 5)
    sample_world_with_timeline.characters["char_cross"].knowledge["prop_smuggler_route"] = KnowledgeItem(
        proposition_id="prop_smuggler_route",
        holder_id="char_cross",
        acquired_at_event="evt_03",
        believed_truth_value=True,
    )

    # At tick 1, the event hasn't happened yet -> cross should NOT have this belief
    snap_t1 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=1, use_cache=False)
    cross_t1 = next(n for n in snap_t1.nodes if n.id == "char_cross")
    assert "prop_smuggler_route" not in cross_t1.beliefs

    # At tick 5, the event has occurred -> cross should have this belief
    snap_t5 = TemporalGraphProjector.project_at_tick("proj_test", sample_world_with_timeline, tick=5, use_cache=False)
    cross_t5 = next(n for n in snap_t5.nodes if n.id == "char_cross")
    assert cross_t5.beliefs.get("prop_smuggler_route") is True
