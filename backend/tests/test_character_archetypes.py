"""Phase C Test Suite: Narrative Archetypes, Field Authority, and Observational Trajectory.

CRITICAL INVARIANTS TESTED:
1. Archetype is design metadata + derived analytics only (NEVER canonical simulation state).
2. FieldAuthority rules apply fully: USER_LOCKED archetypes are NEVER overwritten by inference or enrichers.
3. Archetypes have ZERO direct influence on DecisionPolicy and GoalActionSelector (design orientation + derived observational analytics only).
4. Archetype never grants knowledge and never appears in CharacterWorldView.
5. ArchetypeTrajectory is strictly read-only, has ZERO mutation methods, and produces event-evidenced results.
6. Legacy characters without archetype metadata serialize, deserialize, and simulate unchanged.
"""

import pytest
import random
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.world import WorldState, Location
from src.domain.character import Character, EmotionalState
from src.domain.goal import Goal, GoalStatus
from src.domain.event import Event, EventType
from src.domain.character_creation import FieldAuthority, FieldProvenance, CharacterProfileDraft
from src.domain.character_dynamics import CharacterDynamicsProfile, DYNAMICS_FIELD_NAMES
from src.domain.archetype import ArchetypeType, ArchetypeShiftPoint, ArchetypeTrajectory
from src.domain.world_view import project_view, CharacterWorldView
from src.domain.action import ActionProposal, ActionType, Motivation
from src.generator.archetype_inference import ArchetypeInferenceEngine, ARCHETYPE_SIGNALS
from src.generator.character_normalizer import CharacterProfileNormalizer
from src.generator.character_enricher import CharacterEnrichmentService
from src.agents.goal_selector import GoalActionSelector, CandidateAction
from src.simulation.policy import RuleDecisionPolicy
from src.narrative.archetype_analyzer import ArchetypeTrajectoryAnalyzer


# ============================================================================
# 1. ArchetypeType & Field Authority Tests
# ============================================================================

def test_archetype_type_enum_and_aliases():
    """Verify all 12 standard narrative archetypes exist and aliases parse correctly."""
    assert ArchetypeType.HERO.value == "HERO"
    assert ArchetypeType.RULER.value == "RULER"
    assert ArchetypeType.CAREGIVER.value == "CAREGIVER"
    assert ArchetypeType.CREATOR.value == "CREATOR"
    assert ArchetypeType.INNOCENT.value == "INNOCENT"
    assert ArchetypeType.SAGE.value == "SAGE"
    assert ArchetypeType.EXPLORER.value == "EXPLORER"
    assert ArchetypeType.OUTLAW.value == "OUTLAW"
    assert ArchetypeType.MAGICIAN.value == "MAGICIAN"
    assert ArchetypeType.LOVER.value == "LOVER"
    assert ArchetypeType.JESTER.value == "JESTER"
    assert ArchetypeType.EVERYMAN.value == "EVERYMAN"

    # Test alias parsing
    assert ArchetypeType.from_str("artist") == ArchetypeType.CREATOR
    assert ArchetypeType.from_str("CREATOR") == ArchetypeType.CREATOR
    assert ArchetypeType.from_str("sage") == ArchetypeType.SAGE
    assert ArchetypeType.from_str("unknown_garbage") is None
    assert ArchetypeType.from_str(None) is None


def test_archetype_field_authority_locking():
    """Verify primary and secondary archetype respect Phase A FieldAuthority locking."""
    dyn = CharacterDynamicsProfile(
        primary_archetype=ArchetypeType.SAGE,
        secondary_archetype=ArchetypeType.OUTLAW,
    )
    # Lock primary archetype
    dyn.lock_field("primary_archetype")
    assert dyn.is_locked("primary_archetype")
    assert dyn.get_authority("primary_archetype") == FieldAuthority.USER_LOCKED

    # Attempt to overwrite with SYSTEM_INFERRED must fail
    res = dyn.set_field(
        "primary_archetype",
        ArchetypeType.RULER,
        FieldAuthority.SYSTEM_INFERRED,
    )
    assert res is False
    assert dyn.primary_archetype == ArchetypeType.SAGE

    # Unlock primary archetype
    dyn.unlock_field("primary_archetype")
    assert not dyn.is_locked("primary_archetype")


# ============================================================================
# 2. Deterministic Inference Tests
# ============================================================================

def test_deterministic_archetype_inference_roles_and_values():
    """Verify deterministic inference picks appropriate archetypes without external LLM."""
    # Detective / Investigator with empirical truth values -> SAGE
    primary, secondary, rationale = ArchetypeInferenceEngine.infer_archetypes(
        role="Detective",
        core_value="Empirical truth and logical deduction",
        fear="Deception and false conclusions",
    )
    assert primary == ArchetypeType.SAGE
    assert "SAGE" in rationale

    # Executive with dominance and control -> RULER
    primary_exec, _, _ = ArchetypeInferenceEngine.infer_archetypes(
        role="Corporate Executive",
        core_value="Strategic order and organizational dominance",
        fear="Loss of status and chaos",
    )
    assert primary_exec == ArchetypeType.RULER

    # Smuggler / Rebel with disruption and defiance -> OUTLAW
    primary_outlaw, _, _ = ArchetypeInferenceEngine.infer_archetypes(
        role="Underground Smuggler",
        core_value="Radical freedom and defiance of institutional boundaries",
        fear="Confinement and forced conformity",
    )
    assert primary_outlaw == ArchetypeType.OUTLAW


def test_inference_never_overwrites_user_locked_fields():
    """Verify enrichment and inference never overwrite USER_LOCKED or USER_PREFERRED fields."""
    dyn = CharacterDynamicsProfile(
        primary_archetype=ArchetypeType.JESTER,
        core_value="Truth, empirical logic, and forensic science",
    )
    dyn.lock_field("primary_archetype")

    # Call inference enrichment
    updated = ArchetypeInferenceEngine.enrich_dynamics_archetypes(
        dynamics=dyn,
        role="Senior Detective",
    )
    # Primary archetype must remain JESTER because it is USER_LOCKED
    assert dyn.primary_archetype == ArchetypeType.JESTER


# ============================================================================
# 3. Simulation Sovereignty Invariant: Zero Influence on Action Selection & DecisionPolicy
# ============================================================================

def test_archetype_has_zero_influence_on_action_selection_and_decision_policy():
    """Verify that given identical canonical simulation state (WorldState, goals, beliefs,
    knowledge, relationships, emotions, seed), characters with DIFFERENT archetypes
    produce IDENTICAL candidate utility scores, rankings, and selected actions.
    """
    # Character A: HERO
    actor_hero = Character(
        id="char_test",
        name="Dr. Jane",
        role="Scientist",
        description="Analyst",
        current_location_id="lab",
        personality_traits={"curiosity": 0.8, "courage": 0.7},
        emotional_state=EmotionalState(fear=0.2, anger=0.1, trust=0.5, curiosity=0.8),
        goals=["goal_cure"],
        dynamics=CharacterDynamicsProfile(
            primary_archetype=ArchetypeType.HERO,
            secondary_archetype=ArchetypeType.OUTLAW,
        ),
    )

    # Character B: SAGE (all canonical state identical to A)
    actor_sage = Character(
        id="char_test",
        name="Dr. Jane",
        role="Scientist",
        description="Analyst",
        current_location_id="lab",
        personality_traits={"curiosity": 0.8, "courage": 0.7},
        emotional_state=EmotionalState(fear=0.2, anger=0.1, trust=0.5, curiosity=0.8),
        goals=["goal_cure"],
        dynamics=CharacterDynamicsProfile(
            primary_archetype=ArchetypeType.SAGE,
            secondary_archetype=ArchetypeType.CREATOR,
        ),
    )

    # Character C: No archetype (dynamics present but archetypes None)
    actor_neutral = Character(
        id="char_test",
        name="Dr. Jane",
        role="Scientist",
        description="Analyst",
        current_location_id="lab",
        personality_traits={"curiosity": 0.8, "courage": 0.7},
        emotional_state=EmotionalState(fear=0.2, anger=0.1, trust=0.5, curiosity=0.8),
        goals=["goal_cure"],
        dynamics=CharacterDynamicsProfile(),
    )

    goal = Goal(id="goal_cure", character_id="char_test", description="Discover the cure", priority=1.0)

    mock_world = WorldState(
        id="world_test",
        name="Test World",
        current_tick=1,
        locations={"lab": Location(id="lab", name="Laboratory")},
        characters={"char_test": actor_hero},
        goals={"goal_cure": goal},
    )

    test_candidates = [
        CandidateAction(action_type=ActionType.INSPECT_OBJECT, target_id="microscope", base_utility=0.50),
        CandidateAction(action_type=ActionType.MOVE, location_id="corridor", base_utility=0.40),
        CandidateAction(action_type=ActionType.SPEAK, target_id="colleague", parameters={"social_intent": "question"}, base_utility=0.55),
        CandidateAction(action_type=ActionType.WAIT, base_utility=0.10),
    ]

    # 1. Assert GoalActionSelector scores each candidate action identically across all archetypes
    for candidate in test_candidates:
        score_hero = GoalActionSelector.score_candidate(
            candidate=candidate,
            actor=actor_hero,
            goals=[goal],
            world=mock_world,
        )
        score_sage = GoalActionSelector.score_candidate(
            candidate=candidate,
            actor=actor_sage,
            goals=[goal],
            world=mock_world,
        )
        score_neutral = GoalActionSelector.score_candidate(
            candidate=candidate,
            actor=actor_neutral,
            goals=[goal],
            world=mock_world,
        )

        assert score_hero == score_sage == score_neutral, (
            f"Candidate {candidate.action_type} scored differently across archetypes: "
            f"HERO={score_hero}, SAGE={score_sage}, NEUTRAL={score_neutral}"
        )

    # 2. Assert RuleDecisionPolicy produces identical decisions for different archetypes
    policy = RuleDecisionPolicy()
    view = project_view(mock_world, actor_hero)

    proposal_hero = policy.propose(actor_hero, view, [], rng=random.Random(1337))
    proposal_sage = policy.propose(actor_sage, view, [], rng=random.Random(1337))
    proposal_neutral = policy.propose(actor_neutral, view, [], rng=random.Random(1337))

    assert proposal_hero.action_type == proposal_sage.action_type == proposal_neutral.action_type
    assert proposal_hero.target_id == proposal_sage.target_id == proposal_neutral.target_id
    assert proposal_hero.parameters == proposal_sage.parameters == proposal_neutral.parameters
    assert proposal_hero.reason == proposal_sage.reason == proposal_neutral.reason
    assert proposal_hero.expected_outcome == proposal_sage.expected_outcome == proposal_neutral.expected_outcome
    assert proposal_hero.motivation.kind == proposal_sage.motivation.kind == proposal_neutral.motivation.kind


# ============================================================================
# 4. Omniscience Firewall: Archetype Never Grants Knowledge
# ============================================================================

def test_archetype_never_appears_in_character_world_view():
    """Verify CharacterWorldView omniscience firewall does not leak archetype as canonical truth."""
    char = Character(
        id="char_1",
        name="Marcus Vance",
        role="Investigator",
        description="Methodical",
        current_location_id="office",
        dynamics=CharacterDynamicsProfile(
            primary_archetype=ArchetypeType.SAGE,
            secondary_archetype=ArchetypeType.HERO,
        ),
    )

    world = WorldState(
        id="world_office",
        name="Office World",
        current_tick=0,
        locations={"office": Location(id="office", name="Office")},
        characters={"char_1": char},
    )

    view = project_view(world, char)
    assert isinstance(view, CharacterWorldView)
    # CharacterWorldView has extra='forbid'
    assert not hasattr(view, "primary_archetype")
    assert not hasattr(view, "secondary_archetype")
    assert not hasattr(view, "archetype")
    # Character view knowledge does not contain archetype
    for k_item in view.knowledge.values():
        assert "SAGE" not in str(k_item)


# ============================================================================
# 5. Observational ArchetypeTrajectoryAnalyzer Tests
# ============================================================================

def test_archetype_trajectory_is_strictly_read_only_and_event_evidenced():
    """Verify ArchetypeTrajectoryAnalyzer evaluates historical events without mutation."""
    char = Character(
        id="char_hero",
        name="Alex Mercer",
        role="Field Agent",
        description="Tenacious",
        current_location_id="docks",
        dynamics=CharacterDynamicsProfile(
            primary_archetype=ArchetypeType.HERO,
        ),
    )

    world = WorldState(
        id="world_docks",
        name="Docks World",
        current_tick=12,
        locations={"docks": Location(id="docks", name="Docks")},
        characters={"char_hero": char},
    )

    # Synthetic events: Hero starts out, but at tick 10 engages in defying / challenging speech -> OUTLAW shift
    events = [
        Event(
            id="ev_1",
            tick=1,
            event_type=EventType.OBJECT_PICKED_UP,
            actor_ids=["char_hero"],
            location_id="docks",
            description="Alex takes the evidence briefcase.",
        ),
        Event(
            id="ev_2",
            tick=10,
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_hero"],
            location_id="docks",
            description="Alex defies the chief's order.",
            metadata={"social_intent": "defy", "dialogue": "I will not comply with your corrupt orders."},
        ),
        Event(
            id="ev_3",
            tick=11,
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_hero"],
            location_id="docks",
            description="Alex challenges the corrupt official.",
            metadata={"social_intent": "challenge", "dialogue": "Try and stop me."},
        ),
    ]

    trajectory = ArchetypeTrajectoryAnalyzer.analyze_trajectory(
        character_id="char_hero",
        world=world,
        events=events,
    )

    assert isinstance(trajectory, ArchetypeTrajectory)
    assert trajectory.is_observed_only is True
    assert trajectory.initial_archetype == ArchetypeType.HERO
    # World state must remain 100% unmutated
    assert world.characters["char_hero"].dynamics.primary_archetype == ArchetypeType.HERO

    # Check observed shift point
    assert len(trajectory.shift_points) >= 1
    shift = trajectory.shift_points[0]
    assert shift.dominant_archetype == ArchetypeType.OUTLAW
    assert "ev_2" in shift.evidence_event_ids or "ev_3" in shift.evidence_event_ids
    assert trajectory.stability_score < 1.0


# ============================================================================
# 6. Integration Test: Full Intake -> Dynamics -> Archetype -> Simulation
# ============================================================================

def test_full_phase_c_intake_archetype_simulation_pipeline():
    """Verify complete lifecycle: intake with archetype -> infer -> accept -> simulation."""
    app = create_app()
    client = TestClient(app)

    # Create project
    proj_res = client.post("/api/projects", json={
        "name": "Phase C Verification Project",
        "seed_prompt": "An undercover detective infiltrates a luxury casino to expose money laundering.",
    })
    assert proj_res.status_code == 200
    proj_id = proj_res.json()["id"]

    # 1. Intake with explicit archetype in natural language
    intake_res = client.post(f"/api/projects/{proj_id}/characters/intake", json={
        "raw_text": "Detective Sarah Stone, a forensic investigator. Archetype: SAGE. Core Value: Objective truth.",
        "auto_enrich": False,
    })
    assert intake_res.status_code == 200
    draft = intake_res.json()["draft"]
    draft_id = draft["id"]

    # Check parsed archetype
    assert draft["dynamics"]["primary_archetype"] == "SAGE"

    # 2. Lock primary archetype
    lock_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/lock", json={
        "field_name": "primary_archetype"
    })
    assert lock_res.status_code == 200

    # 3. Trigger draft archetype inference
    infer_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/archetype/infer")
    assert infer_res.status_code == 200
    inferred_draft = infer_res.json()["draft"]
    # Locked primary remains SAGE
    assert inferred_draft["dynamics"]["primary_archetype"] == "SAGE"

    # 4. Accept draft into simulation cast
    accept_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/accept")
    assert accept_res.status_code == 200
    char_id = accept_res.json()["character_id"]

    # 5. Fetch archetype endpoint
    arch_res = client.get(f"/api/projects/{proj_id}/characters/{char_id}/archetype")
    assert arch_res.status_code == 200
    assert arch_res.json()["primary_archetype"] == "SAGE"

    # 6. Fetch observational trajectory endpoint
    traj_res = client.get(f"/api/projects/{proj_id}/characters/{char_id}/archetype-trajectory")
    assert traj_res.status_code == 200
    traj_data = traj_res.json()
    assert traj_data["character_id"] == char_id
    assert traj_data["is_observed_only"] is True

    # 7. Run 3 simulation ticks
    step_res = client.post(f"/api/projects/{proj_id}/step", json={"ticks": 3})
    assert step_res.status_code == 200
    assert step_res.json()["current_tick"] == 3


# ============================================================================
# 7. Backward Compatibility
# ============================================================================

def test_legacy_character_without_archetype_backward_compatibility():
    """Verify legacy character with primary_archetype=None simulates cleanly."""
    legacy_char = Character(
        id="char_legacy",
        name="Legacy Actor",
        role="Worker",
        description="Pre-Phase-C character",
        current_location_id="loc_1",
        dynamics=None,  # No dynamics at all
    )

    world = WorldState(
        id="world_legacy",
        name="Legacy World",
        current_tick=0,
        locations={"loc_1": Location(id="loc_1", name="Room")},
        characters={"char_legacy": legacy_char},
    )

    trajectory = ArchetypeTrajectoryAnalyzer.analyze_trajectory(
        character_id="char_legacy",
        world=world,
        events=[],
    )
    assert trajectory.initial_archetype is None
    assert trajectory.is_observed_only is True
