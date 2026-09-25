"""Comprehensive tests for Phase B: Character Dynamics Design-Time Profile.

Invariants verified:
1. CharacterDynamicsProfile is character design metadata, never canonical WorldState.
2. FieldAuthority and FieldProvenance protect USER_LOCKED fields from silent overwrite.
3. conscious_want may project into the canonical Goal model.
4. dramatic_need is strictly analytical and never influences CharacterWorldView, ActionProposal, or DecisionPolicy.
5. Simulation sovereignty: characters decide via DecisionPolicy -> Motivation -> ActionProposal -> Validator -> Executor.
6. Old projects and characters without dynamics profiles load and simulate without regression.
7. Fully deterministic provider-off path works.
"""

import pytest
import random
from fastapi.testclient import TestClient

from src.api.app import app
from src.domain.character import Character, EmotionalState
from src.domain.character_dynamics import CharacterDynamicsProfile, DYNAMICS_FIELD_NAMES
from src.domain.character_creation import (
    FieldAuthority,
    FieldProvenance,
    CharacterProfileDraft,
)
from src.domain.goal import Goal, GoalStatus
from src.domain.world import WorldState, Location
from src.domain.world_view import project_view, CharacterWorldView
from src.domain.action import ActionProposal, ActionType, Motivation
from src.simulation.policy import RuleDecisionPolicy, LLMDecisionPolicy
from src.simulation.affordances import ObjectAffordance
from src.generator.character_normalizer import CharacterProfileNormalizer
from src.generator.character_enricher import CharacterEnrichmentService
from src.providers.mock import MockLLMProvider
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata


# ============================================================================
# 1. Unit Tests: CharacterDynamicsProfile and FieldAuthority Tagging
# ============================================================================

def test_dynamics_profile_creation_and_field_authority():
    """Verify that CharacterDynamicsProfile instantiates and tracks FieldAuthority."""
    dyn = CharacterDynamicsProfile(
        core_value="Absolute truth",
        shadow_value="Need for control",
        conscious_want="Expose the corruption in sector 4",
        dramatic_need="Learn to trust others and forgive himself",
        fear="Becoming what he fought against",
        contradiction="Preaches transparency while maintaining false identities",
        moral_boundary="Will not harm non-combatants",
        habits=["Taps fingers to count ticks", "Checks room corners"],
        mannerisms=["Unblinking focus", "Speaks in short clipped sentences"],
        lifestyle="Sparse apartment, irregular hours",
        speech_style="Direct, minimal adjectives",
        conflict_strategy="Evidential confrontation",
    )

    assert dyn.core_value == "Absolute truth"
    assert dyn.conscious_want == "Expose the corruption in sector 4"
    assert dyn.dramatic_need == "Learn to trust others and forgive himself"
    assert dyn.fear == "Becoming what he fought against"
    assert dyn.contradiction == "Preaches transparency while maintaining false identities"
    assert len(dyn.habits) == 2
    assert len(dyn.mannerisms) == 2

    # Tagging with FieldAuthority
    dyn.set_field("core_value", "Truth and honor", FieldAuthority.USER_PREFERRED, source_snippet="User prompt")
    assert dyn.core_value == "Truth and honor"
    assert dyn.get_authority("core_value") == FieldAuthority.USER_PREFERRED
    assert not dyn.is_locked("core_value")

    # Lock field
    dyn.lock_field("core_value")
    assert dyn.is_locked("core_value")
    assert dyn.get_authority("core_value") == FieldAuthority.USER_LOCKED
    assert dyn.provenance["core_value"].locked_at is not None

    # Unlock field
    dyn.unlock_field("core_value")
    assert not dyn.is_locked("core_value")
    assert dyn.get_authority("core_value") == FieldAuthority.USER_PREFERRED


def test_dynamics_draft_synchronization():
    """Verify that CharacterProfileDraft delegates to and synchronizes with its dynamics profile."""
    draft = CharacterProfileDraft(name="Marcus Vance", role="Detective")
    assert draft.dynamics is not None

    draft.set_field("conscious_want", "Catch the docks killer", FieldAuthority.USER_PREFERRED)
    assert draft.dynamics.conscious_want == "Catch the docks killer"
    assert draft.get_authority("conscious_want") == FieldAuthority.USER_PREFERRED
    assert "conscious_want" in draft.provenance
    assert draft.provenance["conscious_want"].authority == FieldAuthority.USER_PREFERRED

    # Lock from draft level
    draft.lock_field("conscious_want")
    assert draft.is_locked("conscious_want")
    assert draft.dynamics.is_locked("conscious_want")

    # Attempt to overwrite with system inferred must fail
    success = draft.set_field("conscious_want", "System generated want", FieldAuthority.SYSTEM_INFERRED)
    assert not success
    assert draft.dynamics.conscious_want == "Catch the docks killer"

    # Unlock from draft level
    draft.unlock_field("conscious_want")
    assert not draft.is_locked("conscious_want")
    assert not draft.dynamics.is_locked("conscious_want")


# ============================================================================
# 2. Unit Tests: Enrichment Respects Locks on Dynamics Fields
# ============================================================================

def test_enrichment_never_overwrites_user_locked_dynamics_fields():
    """CRITICAL: USER_LOCKED dynamics fields must NEVER be overwritten by enrichment."""
    enricher = CharacterEnrichmentService()
    draft = CharacterProfileDraft(name="Elena Rostova", role="Analyst")
    draft.set_field("core_value", "User Locked Core Value", FieldAuthority.USER_LOCKED)
    draft.set_field("dramatic_need", "User Locked Dramatic Need", FieldAuthority.USER_LOCKED)

    assert draft.is_locked("core_value")
    assert draft.is_locked("dramatic_need")

    enriched = enricher.enrich(draft, premise="Cyber breach in Neo-Tokyo")

    # Locked values remain unchanged
    assert enriched.dynamics.core_value == "User Locked Core Value"
    assert enriched.dynamics.dramatic_need == "User Locked Dramatic Need"
    assert enriched.get_authority("core_value") == FieldAuthority.USER_LOCKED
    assert enriched.get_authority("dramatic_need") == FieldAuthority.USER_LOCKED

    # Unlocked fields (like fear, habits, speech_style) are enriched
    assert enriched.dynamics.fear != ""
    assert enriched.get_authority("fear") == FieldAuthority.SYSTEM_INFERRED
    assert len(enriched.dynamics.habits) > 0


def test_enrichment_never_overwrites_user_preferred_dynamics_fields():
    """USER_PREFERRED dynamics fields provided by user must NOT be replaced by enrichment."""
    enricher = CharacterEnrichmentService()
    draft = CharacterProfileDraft(name="Jax", role="Courier")
    draft.set_field("conscious_want", "Deliver the black case safely", FieldAuthority.USER_PREFERRED)
    draft.set_field("fear", "Closed spaces and handcuffs", FieldAuthority.USER_PREFERRED)

    enriched = enricher.enrich(draft)

    assert enriched.dynamics.conscious_want == "Deliver the black case safely"
    assert enriched.dynamics.fear == "Closed spaces and handcuffs"
    assert enriched.get_authority("conscious_want") == FieldAuthority.USER_PREFERRED
    assert enriched.get_authority("fear") == FieldAuthority.USER_PREFERRED

    # Empty fields are enriched
    assert enriched.dynamics.core_value != ""
    assert enriched.get_authority("core_value") == FieldAuthority.SYSTEM_INFERRED


# ============================================================================
# 3. Unit Tests: Safe Projection (Want -> Goal) and Analytical Need Invariant
# ============================================================================

def test_conscious_want_safely_projects_into_goal():
    """Verify conscious_want projects into canonical Goal upon accept without duplicating."""
    client = TestClient(app)

    create_res = client.post("/api/projects", json={
        "seed_prompt": "An undercover agent tries to infiltrate the syndicate.",
        "title": "Infiltration",
    })
    assert create_res.status_code == 200
    proj_id = create_res.json()["id"]

    # Intake with dynamics
    intake_res = client.post(f"/api/projects/{proj_id}/characters/intake", json={
        "structured_payload": {
            "name": "Sarah Blake",
            "role": "Operative",
            "conscious_want": "Infiltrate the secure server room unnoticed",
            "dramatic_need": "Confront her hidden trauma from the previous mission",
            "goals": ["Map out security cameras"],
        },
        "auto_enrich": False,
    })
    assert intake_res.status_code == 200
    draft_id = intake_res.json()["draft"]["id"]

    # Accept draft
    accept_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/accept")
    assert accept_res.status_code == 200
    char_data = accept_res.json()["character"]
    char_id = accept_res.json()["character_id"]

    # Verify world goals contain the projected conscious want
    world_res = client.get(f"/api/projects/{proj_id}/world")
    world_data = world_res.json()

    want_goal_id = f"goal_{char_id}_want"
    assert want_goal_id in world_data["goals"]
    assert world_data["goals"][want_goal_id]["description"] == "Infiltrate the secure server room unnoticed"
    assert want_goal_id in char_data["goals"]

    # CRITICAL: Verify dramatic_need is NEVER a Goal in WorldState
    for gid, g in world_data["goals"].items():
        assert "hidden trauma" not in g["description"].lower()
        assert "dramatic_need" not in gid

    # Verify dramatic_need is strictly stored in char.dynamics
    assert char_data["dynamics"]["dramatic_need"] == "Confront her hidden trauma from the previous mission"


def test_explicit_project_want_endpoint():
    """Verify explicit POST .../project-want projects conscious_want and respects locks."""
    client = TestClient(app)

    create_res = client.post("/api/projects", json={
        "seed_prompt": "A researcher uncovers evidence.",
        "title": "Evidence",
    })
    proj_id = create_res.json()["id"]

    # Create character via intake & accept
    intake_res = client.post(f"/api/projects/{proj_id}/characters/intake", json={
        "structured_payload": {
            "name": "Dr. Aris",
            "role": "Scientist",
            "conscious_want": "Publish the validated dataset",
            "dramatic_need": "Acknowledge scientific humility",
        }
    })
    draft_id = intake_res.json()["draft"]["id"]
    accept_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/accept")
    char_id = accept_res.json()["character_id"]

    # Call project-want endpoint explicitly
    proj_res = client.post(f"/api/projects/{proj_id}/characters/{char_id}/project-want")
    assert proj_res.status_code == 200
    res_data = proj_res.json()
    assert res_data["conscious_want"] == "Publish the validated dataset"
    assert res_data["is_need_projected"] is False
    assert res_data["dramatic_need"] == "Acknowledge scientific humility"


# ============================================================================
# 4. Omniscience Firewall & Simulation Sovereignty Invariant Tests
# ============================================================================

def test_dramatic_need_never_appears_in_character_world_view():
    """CRITICAL INVARIANT: CharacterWorldView must NEVER contain dramatic_need or dynamics metadata."""
    world = WorldState(
        id="world_test_firewall",
        name="Firewall Test",
        locations={"loc_1": Location(id="loc_1", name="Archive")},
    )

    dyn = CharacterDynamicsProfile(
        core_value="Integrity",
        conscious_want="Retrieve the file",
        dramatic_need="SECRET INTERNAL PSYCHOLOGICAL NEED TO BE IGNORED BY SIMULATION",
        fear="Phobia of darkness",
        contradiction="Honest thief",
    )

    char = Character(
        id="char_agent_1",
        name="Agent 1",
        role="Investigator",
        current_location_id="loc_1",
        dynamics=dyn,
    )
    world.characters[char.id] = char

    # Project subjective view through the Omniscience Firewall
    view = project_view(world, char)

    # 1. Attribute presence check
    assert hasattr(view, "dramatic_need") is False
    assert hasattr(view, "dynamics") is False

    # 2. Serialized dictionary dump check
    view_dump = view.model_dump(mode="json")
    assert "dramatic_need" not in view_dump
    assert "SECRET INTERNAL PSYCHOLOGICAL NEED" not in str(view_dump)


def test_decision_policy_never_uses_dramatic_need_and_preserves_sovereignty():
    """CRITICAL INVARIANT: DecisionPolicy proposes actions purely via view and affordances,

    uninfluenced by dramatic_need.
    """
    world = WorldState(
        id="world_test_policy",
        name="Policy Test",
        locations={"loc_office": Location(id="loc_office", name="Main Office")},
    )

    dyn = CharacterDynamicsProfile(
        core_value="Mission",
        conscious_want="Solve the case",
        dramatic_need="CRITICAL_UNCONSCIOUS_NEED_THAT_MUST_NOT_DRIVE_ACTION",
    )

    # Conscious want projected into Goal
    want_goal = Goal(
        id="goal_solve",
        character_id="char_detective",
        description="Solve the case",
        priority=0.9,
        status=GoalStatus.ACTIVE,
    )
    world.goals["goal_solve"] = want_goal

    char = Character(
        id="char_detective",
        name="Detective Cole",
        role="Investigator",
        current_location_id="loc_office",
        goals=["goal_solve"],
        dynamics=dyn,
    )
    world.characters[char.id] = char

    # Other co-present character for social affordance
    other = Character(
        id="char_suspect",
        name="Suspect Ray",
        role="Courier",
        current_location_id="loc_office",
    )
    world.characters[other.id] = other

    view = project_view(world, char)
    rng = random.Random(42)

    # 1. Deterministic RuleDecisionPolicy
    rule_policy = RuleDecisionPolicy()
    proposal = rule_policy.propose(char, view, affordances=[], rng=rng)

    assert isinstance(proposal, ActionProposal)
    assert proposal.actor_id == "char_detective"
    # ActionProposal reason, parameters, and dump must not reference dramatic_need
    assert "CRITICAL_UNCONSCIOUS_NEED" not in (proposal.reason or "")
    assert "CRITICAL_UNCONSCIOUS_NEED" not in (proposal.expected_outcome or "")
    assert "CRITICAL_UNCONSCIOUS_NEED" not in str(proposal.parameters)
    assert "CRITICAL_UNCONSCIOUS_NEED" not in str(proposal.model_dump())

    # Motivation follows Goal
    if proposal.motivation and proposal.motivation.kind == "PURSUE_GOAL":
        assert proposal.motivation.goal_id == "goal_solve"

    # 2. LLMDecisionPolicy (Provider-off / Mock)
    mock_provider = MockLLMProvider()
    llm_policy = LLMDecisionPolicy(mock_provider)
    proposal_llm = llm_policy.propose(char, view, affordances=[], rng=rng)

    assert isinstance(proposal_llm, ActionProposal)
    assert "CRITICAL_UNCONSCIOUS_NEED" not in str(proposal_llm.model_dump())


# ============================================================================
# 5. Normalizer Tests for Dynamics
# ============================================================================

def test_normalizer_extracts_dynamics_from_natural_language():
    """Verify natural-language extraction of core dynamics fields."""
    normalizer = CharacterProfileNormalizer()
    text = (
        "Meet Dr. Samuel O'Connor, a 48-year-old Chief Neurosurgeon wearing surgical scrubs under a white lab coat. "
        "Core Value: Medical ethics and patient safety. "
        "Conscious Want: Uncover the reason behind the patient's anomalous EEG spikes. "
        "Dramatic Need: Accept that not all outcomes can be controlled by medical skill alone. "
        "Fear: Making a catastrophic fatal diagnosis. "
        "Contradiction: Relentless dedication to saving lives while neglecting his own family. "
        "Speech Style: Calm, measured, highly technical diction."
    )

    char_input, draft = normalizer.normalize(raw_text=text)

    assert "Samuel O'Connor" in draft.name
    assert "Neurosurgeon" in draft.role
    assert draft.dynamics.core_value == "Medical ethics and patient safety"
    assert "anomalous eeg" in draft.dynamics.conscious_want.lower()
    assert "accept that not all outcomes" in draft.dynamics.dramatic_need.lower()
    assert "catastrophic fatal diagnosis" in draft.dynamics.fear.lower()
    assert "relentless dedication" in draft.dynamics.contradiction.lower()
    assert "technical diction" in draft.dynamics.speech_style.lower()

    # Provenance tagged USER_PREFERRED
    assert draft.get_authority("core_value") == FieldAuthority.USER_PREFERRED
    assert draft.get_authority("dramatic_need") == FieldAuthority.USER_PREFERRED
    assert draft.get_authority("conscious_want") == FieldAuthority.USER_PREFERRED


# ============================================================================
# 6. Integration Test: Full Intake -> Dynamics Enrich -> Accept -> Simulation
# ============================================================================

def test_full_phase_b_simulation_pipeline():
    """End-to-end integration: Intake -> Dynamics Enrichment -> Accept -> 5-tick Simulation."""
    client = TestClient(app)

    create_res = client.post("/api/projects", json={
        "seed_prompt": "In an underground transit terminal, an operative tracks a suspicious courier.",
        "title": "Terminal Vigilance",
    })
    assert create_res.status_code == 200
    proj_id = create_res.json()["id"]

    # 1. Intake character with partial dynamics
    intake_res = client.post(f"/api/projects/{proj_id}/characters/intake", json={
        "raw_text": "Agent Sarah, an undercover operative. She wants to track the courier without raising an alarm.",
        "auto_enrich": False,
    })
    assert intake_res.status_code == 200
    draft = intake_res.json()["draft"]
    draft_id = draft["id"]

    # 2. Lock conscious want
    lock_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/lock", json={
        "field_name": "conscious_want"
    })
    assert lock_res.status_code == 200

    # 3. Enrich draft
    enrich_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/enrich")
    assert enrich_res.status_code == 200
    enriched = enrich_res.json()["draft"]

    # Locked want preserved
    assert "track the courier" in enriched["dynamics"]["conscious_want"].lower()
    # Missing dynamics enriched with SYSTEM_INFERRED
    assert enriched["dynamics"]["core_value"] != ""
    assert enriched["dynamics"]["dramatic_need"] != ""
    assert enriched["dynamics"]["fear"] != ""

    # 4. Accept draft into simulation world
    accept_res = client.post(f"/api/projects/{proj_id}/characters/drafts/{draft_id}/accept")
    assert accept_res.status_code == 200
    char_id = accept_res.json()["character_id"]

    # 5. Fetch dynamics via new GET endpoint
    get_dyn_res = client.get(f"/api/projects/{proj_id}/characters/{char_id}/dynamics")
    assert get_dyn_res.status_code == 200
    dyn_data = get_dyn_res.json()
    assert dyn_data["conscious_want"] == enriched["dynamics"]["conscious_want"]
    assert dyn_data["dramatic_need"] == enriched["dynamics"]["dramatic_need"]

    # 6. Update dynamics via new PUT endpoint
    update_dyn_res = client.put(f"/api/projects/{proj_id}/characters/{char_id}/dynamics", json={
        "core_value": "Updated Moral North Star",
        "locked_fields": ["core_value"],
    })
    assert update_dyn_res.status_code == 200
    assert update_dyn_res.json()["core_value"] == "Updated Moral North Star"

    # 7. Run 5 simulation ticks to verify simulation sovereign execution
    step_res = client.post(f"/api/projects/{proj_id}/step", json={"ticks": 5})
    assert step_res.status_code == 200
    assert step_res.json()["current_tick"] == 5

    # Check project world state
    world_res = client.get(f"/api/projects/{proj_id}/world")
    assert world_res.status_code == 200
    assert char_id in world_res.json()["characters"]


# ============================================================================
# 7. Backward Compatibility Tests
# ============================================================================

def test_legacy_character_without_dynamics_backward_compatibility():
    """Verify legacy characters with dynamics=None serialize, deserialize, and simulate unchanged."""
    legacy_char = Character(
        id="char_pre_phase_b",
        name="Legacy Agent",
        role="Infiltrator",
        current_location_id="loc_vault",
    )
    assert legacy_char.dynamics is None

    # Serialization and Deserialization
    char_dict = legacy_char.model_dump(mode="json")
    assert "dynamics" in char_dict
    assert char_dict["dynamics"] is None

    reloaded_char = Character.model_validate(char_dict)
    assert reloaded_char.dynamics is None
    assert reloaded_char.name == "Legacy Agent"

    # World state containing legacy character
    world = WorldState(
        id="world_legacy",
        name="Legacy World",
        locations={"loc_vault": Location(id="loc_vault", name="Vault")},
        characters={legacy_char.id: legacy_char},
    )

    view = project_view(world, legacy_char)
    assert view.character_name == "Legacy Agent"
    assert hasattr(view, "dynamics") is False

    rng = random.Random(123)
    policy = RuleDecisionPolicy()
    proposal = policy.propose(legacy_char, view, affordances=[], rng=rng)
    assert isinstance(proposal, ActionProposal)
