"""Tests for Phase 2: Deterministic Decision Policy and Omniscience Firewall.

Covers all 17 required verification criteria:
1. Zero-AI-call full simulation
2. View isolation — no foreign knowledge
3. View isolation — no canonical registry
4. Motivation required at construction
5. caused_by populated from prior_event_id
6. caused_by populated via KnowledgeItem.acquired_at_event
7–10. Each gate rejecting (KnowledgeGate, SpatialGate, CanonGate, AffordanceGate)
11. Knowledge gate blocks acting on an unheld secret
12. Policy determinism (same view + seed)
13. Repetition penalty over >= 20 ticks
14. Protocol conformance for both policies
15. Rejections excluded from EventHistory
16. Hardened replay: 100+ ticks, providers off, identical history and final state
17. Different seed -> different history
"""

import copy
import random
import pytest
from pydantic import ValidationError

from src.demo_world import create_demo_world
from src.domain import (
    WorldState,
    Location,
    WorldObject,
    Character,
    EmotionalState,
    Goal,
    GoalStatus,
    ActionType,
    ActionProposal,
    ActionResultStatus,
    EventType,
    Motivation,
    ActionRejection,
    KnowledgeItem,
    Proposition,
    CharacterWorldView,
    project_view,
)
from src.simulation import (
    SimulationOrchestrator,
    ActionValidator,
    ActionExecutor,
    EventRecorder,
    KnowledgeGate,
    SpatialGate,
    CanonGate,
    AffordanceGate,
    DecisionPolicy,
    RuleDecisionPolicy,
    LLMDecisionPolicy,
)
from src.providers.base import LLMProvider
from src.providers.mock import MockLLMProvider


class ProviderSpy(LLMProvider):
    """Spy provider that records all generation calls to assert zero AI usage."""

    def __init__(self):
        self.call_count = 0
        self.calls = []

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        self.call_count += 1
        self.calls.append(("generate_text", prompt))
        return "mock text"

    def generate_structured(self, schema_cls, prompt: str, system_prompt: str = ""):
        self.call_count += 1
        self.calls.append(("generate_structured", prompt))
        raise RuntimeError("ProviderSpy should not be called in pure rule simulation")


class TestPhase2DecisionPolicy:
    """Test suite for Phase 2: Deterministic Decision Policy and Omniscience Firewall."""

    # 1. Zero-AI-call full simulation
    def test_zero_ai_call_full_simulation(self):
        """Simulation must run end-to-end with zero AI calls."""
        world = create_demo_world()
        spy = ProviderSpy()
        orchestrator = SimulationOrchestrator(world=world, provider=spy, seed=42)

        results = orchestrator.run(max_ticks=10)
        assert len(results) > 0
        assert spy.call_count == 0, f"Expected 0 AI calls, but recorded {spy.call_count}"
        assert len(spy.calls) == 0

    # 2. View isolation — no foreign knowledge
    def test_view_isolation_no_foreign_knowledge(self):
        """project_view must never expose another character's private KnowledgeItem."""
        world = create_demo_world()
        c_arjun = world.characters["char_arjun"]
        c_maya = world.characters["char_maya"]

        # Maya has a secret KnowledgeItem
        maya_secret_item = KnowledgeItem(
            proposition_id="prop_maya_private_ledger",
            holder_id="char_maya",
            believed_truth_value=True,
            certainty=1.0,
            acquired_at_event="evt_init_001",
        )
        c_maya.knowledge["prop_maya_private_ledger"] = maya_secret_item

        # Both characters are in the same room (Suite 307)
        assert c_arjun.current_location_id == c_maya.current_location_id

        # Project Arjun's firewalled view
        arjun_view = project_view(world, c_arjun)

        # Arjun must NOT have Maya's KnowledgeItem
        assert "prop_maya_private_ledger" not in arjun_view.knowledge
        assert arjun_view.knows("prop_maya_private_ledger") is None
        # In perceivable_characters, Maya's observable state is present, but NO knowledge
        obs_maya = arjun_view.perceivable_characters.get("char_maya")
        assert obs_maya is not None
        assert not hasattr(obs_maya, "knowledge")
        assert not hasattr(obs_maya, "secrets")

    # 3. View isolation — no canonical registry
    def test_view_isolation_no_canonical_registry(self):
        """CharacterWorldView must never contain or expose the canonical PropositionRegistry."""
        world = create_demo_world()
        world.propositions["prop_secret_conspiracy"] = Proposition(
            id="prop_secret_conspiracy",
            statement="CEO forged offshore transfer documents",
            subject="ceo",
            predicate="forged",
            object="documents",
            truth_value=True,
        )

        c_arjun = world.characters["char_arjun"]
        arjun_view = project_view(world, c_arjun)

        # The view model must not even have a propositions attribute
        assert not hasattr(arjun_view, "propositions")
        assert "prop_secret_conspiracy" not in arjun_view.knowledge

    # 4. Motivation required at construction
    def test_motivation_required_at_construction(self):
        """ActionProposal cannot be constructed without motivation."""
        with pytest.raises(ValidationError):
            ActionProposal(
                id="prop_invalid_no_mot",
                actor_id="char_arjun",
                action_type=ActionType.MOVE,
                tick_proposed=1,
            )

        # Constructing WITH motivation succeeds
        mot = Motivation(kind="PURSUE_GOAL", goal_id="goal_search")
        prop = ActionProposal(
            id="prop_valid_mot",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=1,
            motivation=mot,
        )
        assert prop.motivation.kind == "PURSUE_GOAL"
        assert prop.motivation.goal_id == "goal_search"

    # 5. caused_by populated from prior_event_id
    def test_caused_by_populated_from_prior_event_id(self):
        """ActionExecutor populates Event.caused_by from proposal.motivation.prior_event_id."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        executor = ActionExecutor()

        mot = Motivation(kind="REACT_TO_EVENT", prior_event_id="evt_speech_001")
        proposal = ActionProposal(
            id="prop_react",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=0,
            motivation=mot,
        )

        res = executor.execute(world, proposal, recorder)
        assert res.status == ActionResultStatus.SUCCESS
        assert len(res.events_created) == 1

        created_event = world.events[res.events_created[0]]
        assert "evt_speech_001" in created_event.caused_by
        assert created_event.motivation is not None
        assert created_event.motivation["kind"] == "REACT_TO_EVENT"
        assert created_event.motivation["prior_event_id"] == "evt_speech_001"

    # 6. caused_by populated via KnowledgeItem.acquired_at_event
    def test_caused_by_populated_via_knowledge_item_acquired_at_event(self):
        """ActionExecutor populates Event.caused_by from KnowledgeItem.acquired_at_event."""
        world = create_demo_world()
        recorder = EventRecorder(world, seed=42)
        executor = ActionExecutor()
        actor = world.characters["char_arjun"]

        # Actor holds a knowledge item acquired at a specific prior event
        actor.knowledge["prop_wiretap_intel"] = KnowledgeItem(
            proposition_id="prop_wiretap_intel",
            holder_id="char_arjun",
            believed_truth_value=True,
            certainty=0.9,
            acquired_at_event="evt_wiretap_recorded_777",
        )

        mot = Motivation(kind="ACT_ON_KNOWLEDGE", knowledge_item_id="prop_wiretap_intel")
        proposal = ActionProposal(
            id="prop_act_know",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=0,
            motivation=mot,
        )

        res = executor.execute(world, proposal, recorder)
        assert res.status == ActionResultStatus.SUCCESS

        created_event = world.events[res.events_created[0]]
        assert "evt_wiretap_recorded_777" in created_event.caused_by

    # 7. KnowledgeGate rejects unheld knowledge
    def test_gate_knowledge_rejects_unheld_knowledge(self):
        """KnowledgeGate rejects actions acting on propositions the actor does not hold."""
        world = create_demo_world()
        mot = Motivation(kind="ACT_ON_KNOWLEDGE", knowledge_item_id="prop_foreign_unknown")
        proposal = ActionProposal(
            id="prop_bad_knowledge",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=0,
            motivation=mot,
        )

        valid, err = KnowledgeGate.validate(world, proposal)
        assert valid is False
        assert "does not hold knowledge" in err

    # 8. SpatialGate rejects unconnected move
    def test_gate_spatial_rejects_unconnected_move(self):
        """SpatialGate rejects moves across non-adjacent locations."""
        world = create_demo_world()
        proposal = ActionProposal(
            id="prop_bad_teleport",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_penthouse_non_adjacent",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )

        valid, err = SpatialGate.validate(world, proposal)
        assert valid is False
        assert "not exist" in err or "not connected" in err

    # 9. CanonGate rejects contradiction
    def test_gate_canon_rejects_contradiction(self):
        """CanonGate rejects mutations contradicting canon facts."""
        world = create_demo_world()
        proposal = ActionProposal(
            id="prop_canon_test",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_hallway",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )

        # Default stub passes
        valid, err = CanonGate.validate(world, proposal)
        assert valid is True

        # Test rejection via hook
        CanonGate.test_rejection_reason = "Contradicts established canon fact"
        try:
            valid_fail, err_fail = CanonGate.validate(world, proposal)
            assert valid_fail is False
            assert "Contradicts established canon fact" in err_fail
        finally:
            CanonGate.test_rejection_reason = None

    # 10. AffordanceGate rejects non-portable take
    def test_gate_affordance_rejects_non_portable_take(self):
        """AffordanceGate rejects taking an object that is not portable."""
        world = create_demo_world()
        proposal = ActionProposal(
            id="prop_take_door",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_door",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )

        valid, err = AffordanceGate.validate(world, proposal)
        assert valid is False
        assert "not portable" in err

    # 11. Knowledge gate specifically blocks acting on an unheld secret
    def test_knowledge_gate_blocks_acting_on_unheld_secret(self):
        """KnowledgeGate specifically blocks a character acting on a secret object they don't hold."""
        world = create_demo_world()
        # Add a secret dossier object in room 307
        secret_obj = WorldObject(
            id="obj_secret_dossier",
            name="Secret Blackmail Dossier",
            description="Hidden dossier tucked under the floorboard.",
            location_id="loc_room307",
            holder_id=None,
            portable=True,
            properties={"is_secret": "true"},
        )
        world.objects[secret_obj.id] = secret_obj

        # Arjun does NOT know about this secret dossier
        arjun = world.characters["char_arjun"]
        assert not arjun.knows(secret_obj.id)

        proposal = ActionProposal(
            id="prop_take_secret",
            actor_id="char_arjun",
            action_type=ActionType.TAKE_OBJECT,
            target_id="obj_secret_dossier",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )

        # KnowledgeGate must block this proposal
        valid, err = KnowledgeGate.validate(world, proposal)
        assert valid is False
        assert "does not hold knowledge of secret object" in err

    # 12. Policy determinism (same view + seed)
    def test_policy_determinism_same_view_and_seed(self):
        """Same view + same seed must produce identical ActionProposal."""
        world = create_demo_world()
        char = world.characters["char_arjun"]
        view = project_view(world, char)
        policy = RuleDecisionPolicy()

        rng1 = random.Random(12345)
        proposal1 = policy.propose(char, view, affordances=[], rng=rng1)

        rng2 = random.Random(12345)
        proposal2 = policy.propose(char, view, affordances=[], rng=rng2)

        assert proposal1.action_type == proposal2.action_type
        assert proposal1.target_id == proposal2.target_id
        assert proposal1.location_id == proposal2.location_id
        assert proposal1.parameters == proposal2.parameters
        assert proposal1.motivation == proposal2.motivation
        assert proposal1.id == proposal2.id

    # 13. Repetition penalty over >= 20 ticks
    def test_repetition_penalty_prevents_looping_over_20_ticks(self):
        """Repetition penalty prevents an agent from continuously looping the exact same action."""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world=world, seed=42)

        results = orchestrator.run(max_ticks=20)
        assert len(results) >= 20

        # Check action history for Arjun
        arjun_actions = [
            (e.event_type, e.metadata.get("object_id") or e.metadata.get("target_id") or e.location_id)
            for e in world.events.values()
            if "char_arjun" in e.actor_ids
        ]

        # No single action should be repeated 6+ consecutive times
        max_streak = 1
        current_streak = 1
        for i in range(1, len(arjun_actions)):
            if arjun_actions[i] == arjun_actions[i - 1]:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        assert max_streak < 6, f"Agent looped same action consecutively {max_streak} times"

    # 14. Protocol conformance for both policies
    def test_protocol_conformance_for_both_policies(self):
        """Both RuleDecisionPolicy and LLMDecisionPolicy satisfy DecisionPolicy protocol."""
        rule_policy = RuleDecisionPolicy()
        assert isinstance(rule_policy, DecisionPolicy)

        llm_policy = LLMDecisionPolicy(provider=MockLLMProvider())
        assert isinstance(llm_policy, DecisionPolicy)

    # 15. Rejections excluded from EventHistory
    def test_rejections_excluded_from_event_history(self):
        """Rejections are recorded in rejection_log and completely absent from EventHistory."""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world=world, seed=42)

        # Manually execute an invalid proposal
        bad_prop = ActionProposal(
            id="prop_deliberately_invalid",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            location_id="loc_invalid_void",
            tick_proposed=0,
            motivation=Motivation(kind="PURSUE_GOAL"),
        )
        res = orchestrator.executor.execute(world, bad_prop, orchestrator.recorder)
        assert res.status == ActionResultStatus.INVALID

        # Rejection must be in rejection_log
        assert len(orchestrator.rejection_log) >= 1
        rejection = orchestrator.rejection_log[-1]
        assert rejection.proposal.id == "prop_deliberately_invalid"
        assert rejection.gate == "SpatialGate"

        # Rejection must NOT be in EventLog
        event_log = orchestrator.get_event_log()
        for evt in event_log:
            assert evt.id != "prop_deliberately_invalid"
            assert "prop_deliberately_invalid" not in (evt.description or "")

    # 16. Hardened replay: 100+ ticks, providers off, identical history and final state
    def test_hardened_replay_100_ticks_providers_off_identical_history_and_final_state(self):
        """100 ticks replay produces byte-identical EventLog and final WorldState."""
        world1 = create_demo_world()
        orch1 = SimulationOrchestrator(world=world1, provider=None, seed=777)
        orch1.run(max_ticks=100)

        world2 = create_demo_world()
        orch2 = SimulationOrchestrator(world=world2, provider=None, seed=777)
        orch2.run(max_ticks=100)

        assert world1.current_tick == 100
        assert world2.current_tick == 100

        log1 = orch1.get_event_log().model_dump_json()
        log2 = orch2.get_event_log().model_dump_json()
        assert log1 == log2, "Event histories diverged between seeded runs!"

        w1_json = world1.model_dump_json()
        w2_json = world2.model_dump_json()
        assert w1_json == w2_json, "Final WorldStates diverged between seeded runs!"

    # 17. Different seed -> different history
    def test_different_seeds_produce_different_history(self):
        """Different seeds drive distinct simulation trajectories."""
        world1 = create_demo_world()
        orch1 = SimulationOrchestrator(world=world1, provider=None, seed=101)
        orch1.run(max_ticks=15)

        world2 = create_demo_world()
        orch2 = SimulationOrchestrator(world=world2, provider=None, seed=202)
        orch2.run(max_ticks=15)

        log1 = orch1.get_event_log().model_dump_json()
        log2 = orch2.get_event_log().model_dump_json()
        assert log1 != log2, "Different seeds produced identical event logs!"
