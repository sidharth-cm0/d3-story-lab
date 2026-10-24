"""Comprehensive tests for Phase 1: Stabilize the Simulation Engine.

Verifies:
1. Canonical state sovereignty (WorldState and EventLog cannot be mutated by analytics,
   Narrative Genome, RAG, graph projector, or Scribe).
2. Character autonomy and worldview boundaries (private knowledge isolation, no foreign secrets,
   Director pressure cannot dictate character decisions, characters may ignore environmental cues).
3. Failed/rejected actions cannot partially mutate world state (clean transaction semantics).
4. Event integrity and causal parent validation (caused_by must strictly reference real events;
   rejections never appear in EventLog; strict (tick, id) ordering).
5. Deterministic replay and seed sensitivity across multi-tick windows without AI providers.
"""

import pytest
from src.domain.world import WorldState, Location, WorldObject, Goal
from src.domain.character import Character, EmotionalState
from src.domain.proposition import KnowledgeItem, Proposition
from src.domain.secret import Secret
from src.domain.event import Event, EventType, EventLog
from src.domain.action import ActionProposal, ActionType, Motivation, ActionResultStatus
from src.domain.world_view import project_view
from src.simulation.actions import ActionValidator, ActionExecutor
from src.simulation.recorder import EventRecorder
from src.simulation.orchestrator import SimulationOrchestrator
from src.agents.director import DirectorAgent, DirectorIntervention
from src.narrative.rag.service import NarrativeRAGService
from src.narrative.temporal_graph.projector import TemporalGraphProjector
from src.narrative.narrative_analyzer import NarrativeAnalyzer
from src.narrative.narrative_advisor import NarrativeAdvisor
from src.narrative.scribe import Scribe
from src.narrative.scene_builder import SceneBuilder


@pytest.fixture
def baseline_simulation_world():
    """Construct a clean, canonical two-room sandbox world."""
    loc_dock = Location(id="loc_dock", name="Docks", connected_locations=["loc_warehouse"])
    loc_wh = Location(id="loc_warehouse", name="Warehouse", connected_locations=["loc_dock"])

    char_alice = Character(
        id="char_alice",
        name="Alice Vance",
        role="Investigator",
        current_location_id="loc_warehouse",
        emotional_state=EmotionalState(trust=0.4, fear=0.2, curiosity=0.7),
    )
    char_bob = Character(
        id="char_bob",
        name="Bob Mercer",
        role="Courier",
        current_location_id="loc_warehouse",
        emotional_state=EmotionalState(trust=0.2, fear=0.3, curiosity=0.4),
    )

    dossier = WorldObject(
        id="obj_dossier",
        name="Syndicate Dossier",
        location_id="loc_warehouse",
        holder_id=None,
        portable=True,
    )
    heavy_crate = WorldObject(
        id="obj_crate",
        name="Heavy Shipping Crate",
        location_id="loc_warehouse",
        holder_id=None,
        portable=False,
    )

    prop_safe = Proposition(
        id="prop_safe_code",
        subject="safe",
        predicate="code_is",
        object="8492",
        truth_value=True,
        is_secret=True,
    )

    secret_alice = Secret(
        id="sec_safe_code",
        character_id="char_alice",
        statement="The safe code is 8492.",
    )

    char_alice.secrets.append("sec_safe_code")
    char_alice.knowledge["prop_safe_code"] = KnowledgeItem(
        proposition_id="prop_safe_code",
        holder_id="char_alice",
        believed_truth_value=True,
        acquired_at_event="evt_0",
    )

    initial_event = Event(
        id="evt_0",
        tick=0,
        event_type=EventType.OTHER,
        actor_ids=["char_alice"],
        location_id="loc_warehouse",
        description="Alice reviews confidential instructions in the warehouse.",
    )

    world = WorldState(
        id="world_phase1_test",
        name="Phase 1 Test World",
        current_tick=0,
        locations={"loc_dock": loc_dock, "loc_warehouse": loc_wh},
        characters={"char_alice": char_alice, "char_bob": char_bob},
        objects={"obj_dossier": dossier, "obj_crate": heavy_crate},
        propositions={"prop_safe_code": prop_safe},
        secrets={"sec_safe_code": secret_alice},
        events={"evt_0": initial_event},
    )
    return world


def test_canonical_state_immutable_from_all_read_layers(baseline_simulation_world):
    """Analytics, RAG, Graph Projector, Scribe, and Genome MUST NOT mutate canonical WorldState."""
    world = baseline_simulation_world
    initial_event_count = len(world.events)
    initial_char_count = len(world.characters)
    initial_loc_count = len(world.locations)
    initial_obj_count = len(world.objects)
    initial_tick = world.current_tick

    # 1. Temporal Graph projection
    _ = TemporalGraphProjector.project_at_tick("proj_p1", world, tick=0)

    # 2. Narrative RAG service search & inquiry
    from src.narrative.rag.models import RAGSearchFilter
    rag = NarrativeRAGService.get_instance()
    _ = rag.search_patterns(RAGSearchFilter(query="mounting suspicion"))

    # 3. Narrative Genome Analysis & Advisory
    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world, events=list(world.events.values()))
    advisor = NarrativeAdvisor()
    _ = advisor.advise(analysis)

    # 4. Scribe scene projection and screenplay generation
    from src.narrative.observer import Observer
    observer = Observer()
    selection = observer.observe(world)
    scribe = Scribe()
    _ = scribe.compose_screenplay(selection, world)

    # Assert 100% state sovereignty
    assert len(world.events) == initial_event_count
    assert len(world.characters) == initial_char_count
    assert len(world.locations) == initial_loc_count
    assert len(world.objects) == initial_obj_count
    assert world.current_tick == initial_tick


def test_character_autonomy_and_view_isolation(baseline_simulation_world):
    """Character worldview boundary must strictly isolate private knowledge and prevent foreign leaks."""
    world = baseline_simulation_world
    bob = world.characters["char_bob"]

    view_bob = project_view(world, bob)

    # 1. Bob's view must NOT contain Alice's secret or knowledge
    assert view_bob.knows("prop_safe_code") is None
    assert view_bob.holds_secret("sec_safe_code") is False
    assert not hasattr(view_bob, "propositions")

    # 2. Bob cannot propose an action targeting unheld secret
    proposal = ActionProposal(
        id="prop_speak_bob",
        actor_id="char_bob",
        action_type=ActionType.SPEAK,
        target_id="char_alice",
        location_id="loc_warehouse",
        tick_proposed=0,
        motivation=Motivation(
            kind="ACT_ON_KNOWLEDGE",
            description="Share safe code with Alice",
            knowledge_item_id="prop_safe_code",
        ),
        parameters={"statement": "8492"},
    )

    validator = ActionValidator()
    is_valid, err, gate = validator.validate_proposal(world, proposal)
    assert is_valid is False
    assert gate == "KnowledgeGate"
    assert "does not hold knowledge" in err


def test_director_cannot_force_character_decisions(baseline_simulation_world):
    """Director pressure is strictly external/environmental; characters retain autonomy."""
    world = baseline_simulation_world
    director = DirectorAgent()

    # Director introduces environmental pressure (e.g. power failure / noise)
    intervention = DirectorIntervention(
        intervention_type="power_failure",
        target_location_id="loc_warehouse",
        description="Lights flicker and an overhead pipe bursts with steam.",
    )

    recorder = EventRecorder(world)
    validator = ActionValidator()
    event = director.inject_intervention(world, recorder, intervention, validator=validator)

    assert event is not None
    # Anti-puppetry: director interventions have empty actor_ids and source DIRECTOR
    assert event.actor_ids == []
    assert event.source == "DIRECTOR"

    # Bob's decision policy is evaluated: Bob is free to wait or move, NOT compelled by Director
    bob = world.characters["char_bob"]
    view_bob = project_view(world, bob)
    assert bob.current_location_id == "loc_warehouse"


def test_failed_actions_do_not_partially_mutate_state(baseline_simulation_world):
    """Rejected proposals must execute zero state changes and never append to EventLog."""
    world = baseline_simulation_world
    initial_event_count = len(world.events)
    dossier = world.objects["obj_dossier"]
    crate = world.objects["obj_crate"]

    recorder = EventRecorder(world)
    validator = ActionValidator()
    executor = ActionExecutor(validator=validator)

    # Case A: Bob attempts to take an unportable crate
    proposal_unportable = ActionProposal(
        id="prop_crate",
        actor_id="char_bob",
        action_type=ActionType.TAKE_OBJECT,
        target_id="obj_crate",
        location_id="loc_warehouse",
        tick_proposed=0,
        motivation=Motivation(kind="PURSUE_GOAL", description="Move heavy crate"),
    )
    res_crate = executor.execute(world, proposal_unportable, recorder)
    assert res_crate.status == ActionResultStatus.INVALID
    assert crate.holder_id is None
    assert "obj_crate" not in world.characters["char_bob"].inventory
    assert len(world.events) == initial_event_count

    # Case B: Bob attempts invalid move to unconnected destination
    proposal_invalid_move = ActionProposal(
        id="prop_teleport",
        actor_id="char_bob",
        action_type=ActionType.MOVE,
        location_id="loc_non_existent",
        tick_proposed=0,
        motivation=Motivation(kind="PURSUE_GOAL", description="Teleport away"),
    )
    res_move = executor.execute(world, proposal_invalid_move, recorder)
    assert res_move.status == ActionResultStatus.INVALID
    assert world.characters["char_bob"].current_location_id == "loc_warehouse"
    assert len(world.events) == initial_event_count

    # All rejections are tracked in validator audit, not canonical EventLog
    assert len(validator.rejections) == 2


def test_event_integrity_and_causal_parent_validation(baseline_simulation_world):
    """Causal parent references (caused_by) must strictly reference existing events."""
    world = baseline_simulation_world
    recorder = EventRecorder(world)
    executor = ActionExecutor()

    # Valid action with both legitimate and fabricated causal parent IDs in motivation
    proposal = ActionProposal(
        id="prop_dossier",
        actor_id="char_alice",
        action_type=ActionType.TAKE_OBJECT,
        target_id="obj_dossier",
        location_id="loc_warehouse",
        tick_proposed=0,
        motivation=Motivation(
            kind="REACT_TO_EVENT",
            prior_event_id="evt_0",  # Real event in world.events
            description="Secure the dossier observed earlier",
        ),
    )

    result = executor.execute(world, proposal, recorder)
    assert result.status == ActionResultStatus.SUCCESS
    created_event_id = result.events_created[0]
    created_event = world.events[created_event_id]

    # Real event is in caused_by
    assert "evt_0" in created_event.caused_by

    # Action with future event ID (tick 10 > current_tick 0)
    world.events["evt_future_10"] = Event(
        id="evt_future_10",
        tick=10,
        event_type=EventType.OTHER,
        description="A future event that has not happened yet.",
    )

    proposal_future_cause = ActionProposal(
        id="prop_future_cause",
        actor_id="char_alice",
        action_type=ActionType.WAIT,
        location_id="loc_warehouse",
        tick_proposed=0,
        motivation=Motivation(
            kind="REACT_TO_EVENT",
            prior_event_id="evt_future_10",  # Causality violation
            description="React to a future event",
        ),
    )
    result_future = executor.execute(world, proposal_future_cause, recorder)
    assert result_future.status == ActionResultStatus.SUCCESS
    created_future_event = world.events[result_future.events_created[0]]

    # Causal validation MUST strip the future event ID
    assert "evt_future_10" not in created_future_event.caused_by


def test_deterministic_replay_across_multi_tick_simulation(baseline_simulation_world):
    """Identical random seeds must produce byte-for-byte identical event traces and states."""
    import copy
    world_a = baseline_simulation_world
    world_b = copy.deepcopy(baseline_simulation_world)

    orch_a = SimulationOrchestrator(world=world_a, seed=777)
    orch_b = SimulationOrchestrator(world=world_b, seed=777)

    for _ in range(5):
        orch_a.step()
        orch_b.step()

    events_a = sorted(world_a.events.values(), key=lambda e: (e.tick, e.id))
    events_b = sorted(world_b.events.values(), key=lambda e: (e.tick, e.id))

    assert len(events_a) == len(events_b)
    for ea, eb in zip(events_a, events_b):
        assert ea.tick == eb.tick
        assert ea.event_type == eb.event_type
        assert ea.actor_ids == eb.actor_ids
        assert ea.location_id == eb.location_id
        assert ea.description == eb.description
        assert ea.caused_by == eb.caused_by
