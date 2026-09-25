"""Comprehensive tests for Phase E: Character State History & Graph Reconstruction Engine.

Tests cover:
1. Reconstructible time-series for relationship dimensions with event provenance
2. Reconstructible time-series for goal progress and goal pressure
3. Reconstructible time-series for belief confidence
4. Reconstructible time-series for emotional valence and specific emotions
5. Reconstructible time-series for archetype alignment and character arc turns
6. Significant-change detection & sparse vs dense emission
7. Critical Invariant: Event provenance mandatory on all non-baseline change points
8. Critical Invariant: Reconstruction NEVER mutates WorldState, characters, or relationships
9. Caching and automatic invalidation on new events / ticks
10. Backward compatibility with legacy projects
11. Read-only API endpoints for character history and relationship dimension history
"""

import pytest
from typing import Dict, List

from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.goal import Goal, GoalStatus
from src.domain.belief import Belief
from src.domain.secret import Secret
from src.domain.relationship import Relationship
from src.domain.event import Event, EventType
from src.domain.character_dynamics import CharacterDynamicsProfile
from src.domain.archetype import ArchetypeType
from src.domain.character_history import (
    HistoryPoint,
    CharacterHistorySeries,
    CharacterHistoryReport,
)
from src.evolution.relationship import RelationshipUpdater
from src.simulation.differ import StateSnapshotDiffer
from src.narrative.state_history import CharacterStateHistoryReconstructor
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from fastapi.testclient import TestClient
from src.api.app import app, create_app


# =============================================================================
# Helper Fixtures
# =============================================================================

def build_test_history_world() -> WorldState:
    loc = Location(id="loc_office", name="Corner Office")
    char_arjun = Character(
        id="char_arjun",
        name="Arjun",
        role="Investigator",
        personality_traits={"analytical": 0.9, "cautious": 0.8},
        current_location_id="loc_office",
        goals=["goal_arjun_1"],
        secrets=[],
        beliefs=["bel_arjun_1"],
        emotional_state=EmotionalState(happiness=0.2, fear=0.1, anger=0.1, trust=0.0, curiosity=0.8),
        dynamics=CharacterDynamicsProfile(
            core_value="truth",
            primary_archetype=ArchetypeType.SAGE,
        ),
    )
    char_maya = Character(
        id="char_maya",
        name="Maya",
        role="Executive",
        personality_traits={"ambitious": 0.9, "secretive": 0.8},
        current_location_id="loc_office",
        goals=["goal_maya_1"],
        secrets=["sec_maya_1"],
        beliefs=["bel_maya_1"],
        emotional_state=EmotionalState(happiness=0.5, fear=0.2, anger=0.1, trust=0.1, curiosity=0.5),
        dynamics=CharacterDynamicsProfile(
            core_value="discretion",
            primary_archetype=ArchetypeType.RULER,
        ),
    )
    goal_arjun = Goal(
        id="goal_arjun_1",
        character_id="char_arjun",
        description="Audit the accounts",
        priority=0.9,
        progress=0.0,
        status=GoalStatus.ACTIVE,
    )
    goal_maya = Goal(
        id="goal_maya_1",
        character_id="char_maya",
        description="Pass the audit cleanly",
        priority=0.8,
        progress=0.0,
        status=GoalStatus.ACTIVE,
    )
    bel_arjun = Belief(
        id="bel_arjun_1",
        character_id="char_arjun",
        statement="The records have discrepancies",
        confidence=0.7,
    )
    bel_maya = Belief(
        id="bel_maya_1",
        character_id="char_maya",
        statement="The auditor will find nothing",
        confidence=0.6,
    )
    rel = Relationship(
        id="rel_arjun_maya",
        character_a_id="char_arjun",
        character_b_id="char_maya",
        affinity=0.0,
        trust=0.0,
        suspicion=0.1,
        resentment=0.0,
        history="Formal working relationship",
    )

    world = WorldState(
        id="world_history_test",
        name="History Test World",
        locations={loc.id: loc},
        characters={char_arjun.id: char_arjun, char_maya.id: char_maya},
        goals={goal_arjun.id: goal_arjun, goal_maya.id: goal_maya},
        beliefs={bel_arjun.id: bel_arjun, bel_maya.id: bel_maya},
        relationships={rel.id: rel},
        current_tick=0,
    )
    return world


def simulate_events_on_world(world: WorldState) -> List[Event]:
    """Helper that adds chronological events and updates world relationships/emotions."""
    # Tick 1: Conversation
    evt1 = Event(
        id="evt_001",
        tick=1,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun", "char_maya"],
        description="Arjun asked Maya about the missing receipts.",
        metadata={"social_intent": "question"},
    )
    world.events[evt1.id] = evt1

    # Tick 2: Accusation causing relationship suspicion and anger
    evt2 = Event(
        id="evt_002",
        tick=2,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun", "char_maya"],
        description="Arjun formally accused Maya of fabricating invoices.",
        metadata={"social_intent": "accuse", "delta_suspicion": 0.4, "delta_trust": -0.3, "delta_fear": 0.25},
    )
    world.events[evt2.id] = evt2

    # Apply relationship delta
    RelationshipUpdater.apply_interaction(
        world,
        "char_arjun",
        "char_maya",
        delta_suspicion=0.4,
        delta_trust=-0.3,
        note="Accused of fabrication",
        event_id=evt2.id,
    )

    # Tick 4: Goal Progress
    evt3 = Event(
        id="evt_003",
        tick=4,
        event_type=EventType.OBJECT_PICKED_UP,
        actor_ids=["char_arjun"],
        description="Arjun recovered the hidden ledger from the safe.",
        metadata={"object_id": "obj_ledger", "goal_id": "goal_arjun_1", "goal_progress": 0.8},
    )
    world.events[evt3.id] = evt3
    g_arjun = world.goals["goal_arjun_1"]
    g_arjun.progress = 0.8
    g_arjun.last_progress_tick = 4

    # Tick 5: Goal Completed & Belief Shaken
    evt4 = Event(
        id="evt_004",
        tick=5,
        event_type=EventType.BELIEF_FORMED,
        actor_ids=["char_arjun", "char_maya"],
        description="Maya admitted to moving the funds.",
        metadata={"belief_id": "bel_maya_confess", "goal_id": "goal_arjun_1", "goal_status": "completed"},
    )
    world.events[evt4.id] = evt4
    g_arjun.progress = 1.0
    g_arjun.status = GoalStatus.COMPLETED

    world.current_tick = 5
    return [evt1, evt2, evt3, evt4]


# =============================================================================
# 1. Relationship Dimensions Reconstruction & Event Provenance
# =============================================================================

def test_reconstruct_relationship_dimension_series():
    world = build_test_history_world()
    CharacterStateHistoryReconstructor.clear_cache()

    # Reconstruct before events (tick 0)
    series_pre = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "trust"
    )
    assert series_pre.metric == "trust"
    assert len(series_pre.points) == 1
    assert series_pre.points[0].tick == 0
    assert series_pre.points[0].value == 0.0
    assert series_pre.points[0].event_ids == []

    # Run events
    simulate_events_on_world(world)

    # Reconstruct suspicion and trust
    series_suspicion = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "suspicion"
    )
    series_trust = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "trust"
    )

    # Suspicion rose at tick 2
    assert len(series_suspicion.points) >= 2
    assert series_suspicion.points[0].tick == 0
    assert series_suspicion.points[0].value == 0.1

    change_pt = series_suspicion.points[1]
    assert change_pt.tick == 2
    assert change_pt.value == 0.5  # 0.1 + 0.4
    assert "evt_002" in change_pt.event_ids

    # Trust dropped at tick 2
    assert len(series_trust.points) >= 2
    trust_change = series_trust.points[1]
    assert trust_change.tick == 2
    assert trust_change.value == -0.3
    assert "evt_002" in trust_change.event_ids


# =============================================================================
# 2. Goal Progress and Pressure Reconstruction
# =============================================================================

def test_reconstruct_goal_metrics():
    world = build_test_history_world()
    simulate_events_on_world(world)
    CharacterStateHistoryReconstructor.clear_cache()

    prog_series = CharacterStateHistoryReconstructor.reconstruct_character_metric_series(
        world, "char_arjun", "goal_progress"
    )
    assert prog_series.metric == "goal_progress"
    assert len(prog_series.points) >= 3

    # Tick 0: 0.0 progress
    assert prog_series.points[0].tick == 0
    assert prog_series.points[0].value == 0.0

    # Progress points carry event provenance
    pts_with_events = prog_series.get_points_with_events()
    assert len(pts_with_events) >= 1
    assert any(p.tick == 4 and "evt_003" in p.event_ids for p in pts_with_events)

    # Final completion point
    assert prog_series.get_latest_value() == 1.0


# =============================================================================
# 3. Belief Confidence and Emotion Reconstruction
# =============================================================================

def test_reconstruct_belief_and_emotion_metrics():
    world = build_test_history_world()
    simulate_events_on_world(world)
    CharacterStateHistoryReconstructor.clear_cache()

    # Belief confidence
    b_series = CharacterStateHistoryReconstructor.reconstruct_character_metric_series(
        world, "char_maya", "belief_confidence"
    )
    assert b_series.metric == "belief_confidence"
    assert len(b_series.points) >= 2
    assert b_series.points[0].tick == 0
    assert b_series.points[1].tick == 5
    assert "evt_004" in b_series.points[1].event_ids

    # Emotion (fear)
    f_series = CharacterStateHistoryReconstructor.reconstruct_character_metric_series(
        world, "char_maya", "fear"
    )
    assert f_series.metric == "fear"
    assert len(f_series.points) >= 2
    # Fear changed at tick 2 due to accusation
    fear_change = [p for p in f_series.points if p.tick == 2]
    assert len(fear_change) == 1
    assert "evt_002" in fear_change[0].event_ids


# =============================================================================
# 4. Archetype Alignment and Arc Stage Reconstruction
# =============================================================================

def test_reconstruct_archetype_and_arc_trajectory():
    world = build_test_history_world()
    simulate_events_on_world(world)
    CharacterStateHistoryReconstructor.clear_cache()

    series_list = CharacterStateHistoryReconstructor.reconstruct_trajectory_series(
        world, "char_arjun"
    )
    assert len(series_list) == 2
    s_arch, s_arc = series_list[0], series_list[1]

    assert s_arch.metric == "archetype_alignment"
    assert len(s_arch.points) >= 1
    assert s_arch.points[0].tick == 0
    assert "sage" in s_arch.points[0].label.lower()

    assert s_arc.metric == "arc_stage"
    assert len(s_arc.points) >= 1
    assert s_arc.points[0].tick == 0


# =============================================================================
# 5. Significant-Change Detection & Sparse vs Dense Emission
# =============================================================================

def test_sparse_vs_dense_sampling():
    world = build_test_history_world()
    simulate_events_on_world(world)
    CharacterStateHistoryReconstructor.clear_cache()

    # Sparse: only emits tick 0 and change points (tick 2)
    sparse_series = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "suspicion", sparse=True
    )
    assert sparse_series.is_sparse is True
    # Should only have baseline (tick 0) and change (tick 2) -> 2 points
    assert len(sparse_series.points) == 2
    assert [p.tick for p in sparse_series.points] == [0, 2]

    # Dense: emits all ticks from 0 to current_tick (5) -> 6 points (0, 1, 2, 3, 4, 5)
    dense_series = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "suspicion", sparse=False
    )
    assert dense_series.is_sparse is False
    assert len(dense_series.points) == 6
    assert [p.tick for p in dense_series.points] == [0, 1, 2, 3, 4, 5]

    # Forward filled points have no event_ids
    assert dense_series.points[3].tick == 3
    assert dense_series.points[3].value == 0.5
    assert dense_series.points[3].event_ids == []


# =============================================================================
# 6. Critical Invariant: Mandatory Event Provenance & No WorldState Mutation
# =============================================================================

def test_provenance_mandatory_and_no_world_state_mutation():
    world = build_test_history_world()
    simulate_events_on_world(world)
    CharacterStateHistoryReconstructor.clear_cache()

    snapshot_before = world.model_dump(mode="json")

    # Run multiple history reconstructions
    rep = CharacterStateHistoryReconstructor.reconstruct_character_history(
        world, "char_arjun", target_character_id="char_maya"
    )

    snapshot_after = world.model_dump(mode="json")

    # Invariant: WorldState is completely bit-for-bit identical
    assert snapshot_before == snapshot_after

    # Invariant: Every non-baseline point with value change has event_ids
    for s_name, series in rep.series.items():
        assert series.is_analytical_only is True
        for pt in series.points:
            if pt.tick > 0 and not pt.metadata.get("forward_filled"):
                assert len(pt.event_ids) > 0, f"Point at tick {pt.tick} in {s_name} lacks event provenance!"


# =============================================================================
# 7. Caching and Invalidation Behavior
# =============================================================================

def test_caching_and_automatic_invalidation():
    world = build_test_history_world()
    CharacterStateHistoryReconstructor.clear_cache()

    # Query 1: Cache Miss
    s1 = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "trust"
    )

    # Query 2: Cache Hit (identical object returned from cache)
    s2 = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "trust"
    )
    assert s1 is s2

    # Add a new event -> cache token changes
    new_evt = Event(
        id="evt_new",
        tick=1,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun"],
        description="A new event occurs",
    )
    world.events[new_evt.id] = new_evt
    world.current_tick = 1

    # Query 3: Should invalidate and compute freshly
    s3 = CharacterStateHistoryReconstructor.reconstruct_relationship_series(
        world, "char_arjun", "char_maya", "trust"
    )
    assert s3 is not s1


# =============================================================================
# 8. Backward Compatibility: Legacy Projects Load and Reconstruct
# =============================================================================

def test_backward_compatibility_with_legacy_projects(tmp_path):
    store = ProjectStore(base_dir=tmp_path)
    world = build_test_history_world()

    meta = ProjectMetadata(
        id="proj_legacy_hist",
        title="Legacy Project",
        seed_prompt="Test seed",
    )
    proj = ProjectData(
        metadata=meta,
        world=world,
    )
    store.save_project(proj)

    loaded = store.load_project("proj_legacy_hist")
    assert loaded is not None

    # History reconstructs on-demand from legacy project without error
    rep = CharacterStateHistoryReconstructor.reconstruct_character_history(
        loaded.world, "char_arjun", target_character_id="char_maya"
    )
    assert rep.character_id == "char_arjun"
    assert "goal_progress" in rep.series
    assert "trust" in rep.series


# =============================================================================
# 9. API Endpoints
# =============================================================================

def test_history_api_endpoints(tmp_path):
    store = ProjectStore(base_dir=tmp_path)
    world = build_test_history_world()
    simulate_events_on_world(world)

    meta = ProjectMetadata(
        id="proj_api_hist",
        title="API Hist Project",
        seed_prompt="Test",
    )
    proj = ProjectData(metadata=meta, world=world)
    store.save_project(proj)

    test_app = create_app(store_dir=tmp_path)
    client = TestClient(test_app)

    # 1. GET character history (single metric)
    res1 = client.get("/api/projects/proj_api_hist/characters/char_arjun/history?metric=goal_progress")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["metric"] == "goal_progress"
    assert len(data1["points"]) >= 2

    # 2. GET relationship dimension history
    res2 = client.get("/api/projects/proj_api_hist/relationships/char_arjun/char_maya/history?dimension=suspicion")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["metric"] == "suspicion"
    assert any(p["tick"] == 2 for p in data2["points"])

    # 3. GET all relationship dimensions history
    res3 = client.get("/api/projects/proj_api_hist/relationships/char_arjun/char_maya/history")
    assert res3.status_code == 200
    data3 = res3.json()
    assert "trust" in data3["dimensions"]
    assert "suspicion" in data3["dimensions"]

    # 4. GET trajectory history
    res4 = client.get("/api/projects/proj_api_hist/characters/char_arjun/trajectory/history")
    assert res4.status_code == 200
    data4 = res4.json()
    assert "trajectory" in data4
    assert len(data4["trajectory"]) == 2

    # 5. GET batch history
    res5 = client.get("/api/projects/proj_api_hist/characters/char_arjun/history/batch?metrics=goal_progress,goal_pressure")
    assert res5.status_code == 200
    data5 = res5.json()
    assert "goal_progress" in data5["series"]
    assert "goal_pressure" in data5["series"]
