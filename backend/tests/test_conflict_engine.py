"""Comprehensive tests for Phase D: Conflict Engine & Multidimensional Relationships.

Tests cover:
1. ConflictDimension and ConflictEdge domain models & creation
2. Deterministic conflict derivation across all 10 typed dimensions with explainable evidence
3. Critical Invariant: ConflictEdge derivation NEVER mutates WorldState or creates Events
4. Critical Invariant: High conflict NEVER forces confrontation actions or bypasses DecisionPolicy
5. Critical Invariant: CharacterWorldView firewall intact (no conflict scores leaked to subjective view)
6. Multidimensional Relationship dimensions and event-provenanced updates
7. Phase A FieldAuthority compliance: USER_LOCKED ConflictEdges are protected against re-derivation
8. Backward compatibility: legacy projects and relationships load without error
"""

import pytest
import random
from typing import Dict, List

from src.domain.conflict import (
    ConflictDimension,
    ConflictEvidence,
    ConflictEdge,
    ConflictGraph,
)
from src.domain.relationship import Relationship
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.goal import Goal, GoalStatus
from src.domain.belief import Belief
from src.domain.secret import Secret
from src.domain.character_creation import FieldAuthority
from src.domain.character_dynamics import CharacterDynamicsProfile
from src.domain.archetype import ArchetypeType
from src.domain.action import ActionType, ActionProposal, ActionResult, ActionResultStatus
from src.domain.world_view import project_view
from src.evolution.relationship import RelationshipUpdater
from src.narrative.conflict_engine import ConflictEngine
from src.simulation.policy import RuleDecisionPolicy
from src.simulation.orchestrator import SimulationOrchestrator
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata


# =============================================================================
# Helper Fixtures
# =============================================================================

def build_test_world_with_two_characters() -> WorldState:
    loc = Location(id="loc_office", name="Corner Office")
    char_arjun = Character(
        id="char_arjun",
        name="Arjun",
        role="Corporate Investigator",
        personality_traits={"cautious": 0.8, "analytical": 0.9},
        current_location_id="loc_office",
        goals=["goal_arjun_1"],
        secrets=[],
        beliefs=["bel_arjun_1"],
        dynamics=CharacterDynamicsProfile(
            core_value="truth",
            shadow_value="secrecy",
            conscious_want="Recover the stolen ledger",
            dramatic_need="Learn to trust allies",
            moral_boundary="Will never forge evidence",
            conflict_strategy="Direct confrontation with facts",
        ),
    )
    char_maya = Character(
        id="char_maya",
        name="Maya",
        role="Executive Suspect",
        personality_traits={"ambitious": 0.9, "secretive": 0.8},
        current_location_id="loc_office",
        goals=["goal_maya_1"],
        secrets=["sec_maya_1"],
        beliefs=["bel_maya_1"],
        dynamics=CharacterDynamicsProfile(
            core_value="discretion",
            shadow_value="deception",
            conscious_want="Destroy the incriminating ledger",
            dramatic_need="Admit wrongdoing",
            moral_boundary="Will not physically harm others",
            conflict_strategy="Denial and evasion",
        ),
    )
    goal_arjun = Goal(
        id="goal_arjun_1",
        character_id="char_arjun",
        description="Recover and expose the hidden financial documents",
        priority=0.9,
        status=GoalStatus.ACTIVE,
    )
    goal_maya = Goal(
        id="goal_maya_1",
        character_id="char_maya",
        description="Hide and destroy the financial documents",
        priority=0.9,
        status=GoalStatus.ACTIVE,
    )
    sec_maya = Secret(
        id="sec_maya_1",
        character_id="char_maya",
        statement="Maya transferred corporate funds to an offshore account; Arjun suspects her.",
        importance=0.95,
    )
    bel_arjun = Belief(
        id="bel_arjun_1",
        character_id="char_arjun",
        statement="Maya is guilty of corporate fraud",
        confidence=0.85,
    )
    bel_maya = Belief(
        id="bel_maya_1",
        character_id="char_maya",
        statement="Arjun is lying about Maya and fabricating claims",
        confidence=0.80,
    )
    obj_ledger = WorldObject(
        id="obj_ledger",
        name="Financial Documents",
        description="Contested financial records",
        location_id="loc_office",
        holder_id=None,
    )
    rel = Relationship(
        id="rel_arjun_maya",
        character_a_id="char_arjun",
        character_b_id="char_maya",
        affinity=-0.3,
        trust=-0.4,
        suspicion=0.6,
        resentment=0.5,
        history="Past rivalry and bitter dispute over audited accounts",
    )

    world = WorldState(
        id="world_test",
        name="Test World",
        locations={loc.id: loc},
        characters={char_arjun.id: char_arjun, char_maya.id: char_maya},
        goals={goal_arjun.id: goal_arjun, goal_maya.id: goal_maya},
        secrets={sec_maya.id: sec_maya},
        beliefs={bel_arjun.id: bel_arjun, bel_maya.id: bel_maya},
        objects={obj_ledger.id: obj_ledger},
        relationships={rel.id: rel},
    )
    return world


# =============================================================================
# 1. Domain Models & Creation
# =============================================================================

def test_conflict_dimension_enum_values():
    expected_dims = {
        "goal_opposition",
        "value_opposition",
        "belief_contradiction",
        "resource_competition",
        "secret_exposure_risk",
        "relationship_tension",
        "dependency",
        "historical_grievance",
        "power_conflict",
        "moral_conflict",
    }
    actual_dims = {d.value for d in ConflictDimension}
    assert expected_dims.issubset(actual_dims)


def test_conflict_edge_creation_and_helpers():
    ev = ConflictEvidence(
        dimension=ConflictDimension.GOAL_OPPOSITION,
        source_id="goal_1",
        target_id="goal_2",
        description="Opposing goal objectives",
    )
    edge = ConflictEdge(
        source_character_id="char_a",
        target_character_id="char_b",
        dimensions={ConflictDimension.GOAL_OPPOSITION: 0.8},
        evidence=[ev],
        aggregate_intensity=0.8,
        is_analytical_only=True,
    )

    assert edge.source_character_id == "char_a"
    assert edge.target_character_id == "char_b"
    assert edge.get_dimension_score(ConflictDimension.GOAL_OPPOSITION) == 0.8
    assert edge.get_dimension_score(ConflictDimension.VALUE_OPPOSITION) == 0.0
    assert len(edge.get_evidence_for(ConflictDimension.GOAL_OPPOSITION)) == 1
    assert len(edge.get_evidence_for(ConflictDimension.VALUE_OPPOSITION)) == 0
    assert edge.is_analytical_only is True


def test_conflict_graph_lookup():
    edge = ConflictEdge(
        source_character_id="char_a",
        target_character_id="char_b",
        dimensions={ConflictDimension.VALUE_OPPOSITION: 0.7},
        aggregate_intensity=0.7,
    )
    graph = ConflictGraph(project_id="proj_1", edges=[edge])

    # Symmetrical lookup
    assert graph.get_edge("char_a", "char_b") == edge
    assert graph.get_edge("char_b", "char_a") == edge
    assert graph.get_edge("char_a", "char_c") is None
    assert len(graph.get_edges_for_character("char_a")) == 1


# =============================================================================
# 2. Deterministic Conflict Derivation Across All 10 Dimensions
# =============================================================================

def test_deterministic_conflict_derivation():
    world = build_test_world_with_two_characters()

    edge1 = ConflictEngine.derive_pairwise_conflict(world, "char_arjun", "char_maya")
    edge2 = ConflictEngine.derive_pairwise_conflict(world, "char_arjun", "char_maya")

    # Invariant: pure determinism
    assert edge1.dimensions == edge2.dimensions
    assert edge1.aggregate_intensity == edge2.aggregate_intensity
    assert len(edge1.evidence) == len(edge2.evidence)

    # Check that multiple expected dimensions were detected
    assert ConflictDimension.GOAL_OPPOSITION in edge1.dimensions
    assert ConflictDimension.VALUE_OPPOSITION in edge1.dimensions
    assert ConflictDimension.BELIEF_CONTRADICTION in edge1.dimensions
    assert ConflictDimension.RESOURCE_COMPETITION in edge1.dimensions
    assert ConflictDimension.SECRET_EXPOSURE_RISK in edge1.dimensions
    assert ConflictDimension.RELATIONSHIP_TENSION in edge1.dimensions
    assert ConflictDimension.HISTORICAL_GRIEVANCE in edge1.dimensions
    assert ConflictDimension.POWER_CONFLICT in edge1.dimensions

    # Evidence items must be populated and explainable
    for ev in edge1.evidence:
        assert ev.dimension in edge1.dimensions
        assert len(ev.description) > 5
        assert ev.source_id != ""

    # Aggregate intensity must be derived, secondary, and bounded [0.0, 1.0]
    assert 0.0 <= edge1.aggregate_intensity <= 1.0
    assert edge1.is_analytical_only is True


def test_derive_full_conflict_graph():
    world = build_test_world_with_two_characters()
    graph = ConflictEngine.derive_conflict_graph(world, project_id="proj_test")

    assert graph.project_id == "proj_test"
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert set([edge.source_character_id, edge.target_character_id]) == {"char_arjun", "char_maya"}


# =============================================================================
# 3. Critical Invariant: Derivation NEVER Mutates WorldState or Events
# =============================================================================

def test_conflict_derivation_never_mutates_world_state():
    world = build_test_world_with_two_characters()

    snapshot_before = world.model_dump(mode="json")
    events_count_before = len(world.events)

    edge = ConflictEngine.derive_pairwise_conflict(world, "char_arjun", "char_maya")
    graph = ConflictEngine.derive_conflict_graph(world, "proj_test")

    snapshot_after = world.model_dump(mode="json")
    events_count_after = len(world.events)

    # Canonical world state must remain completely bit-for-bit identical
    assert snapshot_before == snapshot_after
    assert events_count_before == events_count_after == 0


# =============================================================================
# 4. Critical Invariant: High Conflict NEVER Forces Confrontation
# =============================================================================

def test_high_conflict_never_forces_confrontation_actions():
    world = build_test_world_with_two_characters()

    # Artificially set maximum conflict dimensions
    edge = ConflictEngine.derive_pairwise_conflict(world, "char_arjun", "char_maya")
    assert edge.aggregate_intensity > 0.5

    # Propose action via RuleDecisionPolicy
    policy = RuleDecisionPolicy()
    char_arjun = world.characters["char_arjun"]
    view = project_view(world, char_arjun)

    rng = random.Random(42)
    proposal = policy.propose(char_arjun, view, affordances=[], rng=rng)

    # Sovereign simulation: action proposal must be generated strictly from
    # DecisionPolicy and subjective view, not forced confrontation.
    assert isinstance(proposal, ActionProposal)
    assert proposal.actor_id == "char_arjun"
    # ActionProposal parameters must not contain forced conflict flags
    assert "forced_by_conflict" not in proposal.parameters


# =============================================================================
# 5. Critical Invariant: CharacterWorldView Omniscience Firewall Intact
# =============================================================================

def test_character_world_view_omniscience_firewall():
    world = build_test_world_with_two_characters()
    char_arjun = world.characters["char_arjun"]
    view = project_view(world, char_arjun)

    # CharacterWorldView must NOT expose ConflictEdge or ConflictGraph
    assert not hasattr(view, "conflict_graph")
    assert not hasattr(view, "conflict_edges")
    assert not hasattr(view, "conflict_score")


# =============================================================================
# 6. Multidimensional Relationship Dimensions & Event Provenance
# =============================================================================

def test_multidimensional_relationship_extension_and_defaults():
    rel = Relationship(
        id="rel_test",
        character_a_id="char_1",
        character_b_id="char_2",
    )
    # Default values must be 0.0
    assert rel.affinity == 0.0
    assert rel.trust == 0.0
    assert rel.affection == 0.0
    assert rel.fear == 0.0
    assert rel.dependency == 0.0
    assert rel.respect == 0.0
    assert rel.resentment == 0.0
    assert rel.suspicion == 0.0
    assert rel.power_imbalance == 0.0
    assert rel.event_provenance == {}
    assert rel.last_event_id is None


def test_relationship_updater_with_event_provenance():
    world = build_test_world_with_two_characters()

    # Apply interaction with deltas and event ID
    event_id = "evt_accuse_001"
    updated_rel = RelationshipUpdater.apply_interaction(
        world=world,
        char_a_id="char_arjun",
        char_b_id="char_maya",
        delta_trust=-0.2,
        delta_suspicion=0.3,
        delta_resentment=0.25,
        note="Accusation during interrogation",
        event_id=event_id,
    )

    assert updated_rel.trust == -0.6
    assert updated_rel.suspicion == 0.9
    assert updated_rel.resentment == 0.75
    assert updated_rel.last_event_id == event_id
    assert event_id in updated_rel.event_provenance["trust"]
    assert event_id in updated_rel.event_provenance["suspicion"]
    assert event_id in updated_rel.event_provenance["resentment"]

    # Invariant: dimensions bounded [-1.0, 1.0]
    capped_rel = RelationshipUpdater.apply_interaction(
        world=world,
        char_a_id="char_arjun",
        char_b_id="char_maya",
        delta_suspicion=0.5,
        event_id="evt_002",
    )
    assert capped_rel.suspicion == 1.0


# =============================================================================
# 7. Phase A FieldAuthority & Minimal Merge Model: Locked Premise + Runtime Truth
# =============================================================================

def test_user_locked_conflict_edge_merges_with_runtime_state():
    """LOCKED DESIGN PREMISE + CURRENT RUNTIME DERIVATION = CURRENT CONFLICT EDGE."""
    world = build_test_world_with_two_characters()

    # User explicitly locks moral conflict at 0.95 with custom design evidence
    custom_evidence = ConflictEvidence(
        dimension=ConflictDimension.MORAL_CONFLICT,
        source_id="moral_author_premise",
        target_id="char_maya",
        description="Authorial design premise: Incompatible moral codes",
        is_user_authored=True,
    )
    custom_edge = ConflictEdge(
        source_character_id="char_arjun",
        target_character_id="char_maya",
        dimensions={ConflictDimension.MORAL_CONFLICT: 0.95},
        evidence=[custom_evidence],
        aggregate_intensity=0.95,
        authority=FieldAuthority.USER_LOCKED,
        is_locked=True,
        locked_dimensions=[ConflictDimension.MORAL_CONFLICT],
    )

    re_derived = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )

    # Invariant: user-locked dimension is preserved exactly
    assert re_derived.is_locked is True
    assert re_derived.authority == FieldAuthority.USER_LOCKED
    assert re_derived.dimensions[ConflictDimension.MORAL_CONFLICT] == 0.95
    assert ConflictDimension.MORAL_CONFLICT in re_derived.locked_dimensions

    # Invariant: unlocked dimensions are freshly derived from runtime canonical state
    assert ConflictDimension.GOAL_OPPOSITION in re_derived.dimensions
    assert ConflictDimension.RELATIONSHIP_TENSION in re_derived.dimensions
    assert ConflictDimension.SECRET_EXPOSURE_RISK in re_derived.dimensions

    # Aggregate intensity is recomputed from the merged set
    assert re_derived.aggregate_intensity > 0.0

    # Evidence distinguishes user-authored from runtime-derived
    user_evs = [e for e in re_derived.evidence if e.is_user_authored]
    runtime_evs = [e for e in re_derived.evidence if not e.is_user_authored]
    assert len(user_evs) >= 1
    assert any(e.source_id == "moral_author_premise" for e in user_evs)
    assert len(runtime_evs) >= 1


def test_merge_model_runtime_relationship_change_reflects_in_locked_edge():
    """Test A: Locked edge + relationship change -> locked dimension preserved, relationship tension updates."""
    world = build_test_world_with_two_characters()

    # User locked historical grievance
    custom_edge = ConflictEdge(
        source_character_id="char_arjun",
        target_character_id="char_maya",
        dimensions={ConflictDimension.HISTORICAL_GRIEVANCE: 0.9},
        locked_dimensions=[ConflictDimension.HISTORICAL_GRIEVANCE],
        is_locked=True,
        authority=FieldAuthority.USER_LOCKED,
    )

    # Initial derivation
    derived_initial = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )
    initial_rel_tension = derived_initial.dimensions.get(ConflictDimension.RELATIONSHIP_TENSION, 0.0)

    # Now simulate interaction increasing resentment and suspicion
    rel = world.relationships["rel_arjun_maya"]
    rel.resentment = 0.9
    rel.suspicion = 0.95
    rel.trust = -0.8

    # Re-derive
    derived_updated = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )

    # Historical grievance preserved
    assert derived_updated.dimensions[ConflictDimension.HISTORICAL_GRIEVANCE] == 0.9
    # Relationship tension reflects runtime state change
    updated_rel_tension = derived_updated.dimensions.get(ConflictDimension.RELATIONSHIP_TENSION, 0.0)
    assert updated_rel_tension > initial_rel_tension


def test_merge_model_goal_completion_updates_conflict():
    """Test B: Locked edge + goal completion -> runtime goal opposition updates/resolves."""
    world = build_test_world_with_two_characters()

    custom_edge = ConflictEdge(
        source_character_id="char_arjun",
        target_character_id="char_maya",
        dimensions={ConflictDimension.HISTORICAL_GRIEVANCE: 0.8},
        locked_dimensions=[ConflictDimension.HISTORICAL_GRIEVANCE],
        is_locked=True,
        authority=FieldAuthority.USER_LOCKED,
    )

    # Initial derivation with active opposing goals
    initial_edge = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )
    assert ConflictDimension.GOAL_OPPOSITION in initial_edge.dimensions

    # Maya completes/achieves her goal
    world.goals["goal_maya_1"].status = GoalStatus.COMPLETED

    # Re-derive
    updated_edge = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )

    # Goal opposition has resolved because Maya's goal is no longer active
    assert ConflictDimension.GOAL_OPPOSITION not in updated_edge.dimensions
    # Historical grievance is still preserved
    assert updated_edge.dimensions[ConflictDimension.HISTORICAL_GRIEVANCE] == 0.8


def test_merge_model_secret_exposure_updates_conflict():
    """Test C: Locked edge + secret exposure (known_by) -> secret exposure risk updates/resolves."""
    world = build_test_world_with_two_characters()

    custom_edge = ConflictEdge(
        source_character_id="char_arjun",
        target_character_id="char_maya",
        dimensions={ConflictDimension.HISTORICAL_GRIEVANCE: 0.8},
        locked_dimensions=[ConflictDimension.HISTORICAL_GRIEVANCE],
        is_locked=True,
        authority=FieldAuthority.USER_LOCKED,
    )

    initial_edge = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )
    assert ConflictDimension.SECRET_EXPOSURE_RISK in initial_edge.dimensions

    # Secret is exposed to Arjun (added to known_by)
    world.secrets["sec_maya_1"].known_by.append("char_arjun")

    # Re-derive
    updated_edge = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )

    # Secret exposure risk resolves between them
    assert ConflictDimension.SECRET_EXPOSURE_RISK not in updated_edge.dimensions
    assert updated_edge.dimensions[ConflictDimension.HISTORICAL_GRIEVANCE] == 0.8


def test_merge_model_determinism_and_no_world_mutation():
    """Tests D, E, F: Determinism, no WorldState mutation, and derived_at_tick."""
    world = build_test_world_with_two_characters()
    world.current_tick = 14

    custom_edge = ConflictEdge(
        source_character_id="char_arjun",
        target_character_id="char_maya",
        dimensions={ConflictDimension.MORAL_CONFLICT: 0.9},
        locked_dimensions=[ConflictDimension.MORAL_CONFLICT],
        is_locked=True,
        authority=FieldAuthority.USER_LOCKED,
    )

    snapshot_before = world.model_dump(mode="json")

    edge1 = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )
    edge2 = ConflictEngine.derive_pairwise_conflict(
        world, "char_arjun", "char_maya", existing_edge=custom_edge
    )

    graph = ConflictEngine.derive_conflict_graph(
        world, "proj_test", existing_graph=ConflictGraph(project_id="proj_test", edges=[custom_edge])
    )

    snapshot_after = world.model_dump(mode="json")

    # Invariants:
    assert snapshot_before == snapshot_after
    assert edge1.dimensions == edge2.dimensions
    assert edge1.aggregate_intensity == edge2.aggregate_intensity
    assert graph.derived_at_tick == 14
    assert graph.edges[0].dimensions[ConflictDimension.MORAL_CONFLICT] == 0.9


# =============================================================================
# 8. Backward Compatibility & Project Storage
# =============================================================================

def test_project_store_backwards_compatibility_with_and_without_conflict(tmp_path):
    store = ProjectStore(base_dir=tmp_path)
    world = build_test_world_with_two_characters()

    # Legacy-style project without conflict_graph
    meta = ProjectMetadata(
        id="proj_compat",
        title="Compat Project",
        seed_prompt="A test prompt",
    )
    project = ProjectData(
        metadata=meta,
        world=world,
        conflict_graph=None,
    )

    store.save_project(project)
    loaded = store.load_project("proj_compat")

    assert loaded is not None
    assert loaded.conflict_graph is None
    assert loaded.world.relationships["rel_arjun_maya"].affinity == -0.3

    # Now add derived conflict graph and persist
    graph = ConflictEngine.derive_conflict_graph(loaded.world, "proj_compat")
    loaded.conflict_graph = graph
    store.save_project(loaded)

    reloaded = store.load_project("proj_compat")
    assert reloaded is not None
    assert reloaded.conflict_graph is not None
    assert len(reloaded.conflict_graph.edges) == 1
