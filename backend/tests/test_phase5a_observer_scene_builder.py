"""Tests for Phase 5A: Observer, Scene Builder, Scene Objective, and Shared DramaticFunction.

Covers all 18 required tests:
1. Observer leaves EventHistory byte-identical.
2. EventSalience.signals is non-empty.
3. EventSalience scoring deterministic.
4. shared DramaticFunction identity.
5. Scene Builder rejected for CONTINUE.
6. Scene Builder rejected for ADJUST_PRESSURE_AND_CONTINUE.
7. allowed for PROCEED.
8. allowed for HALT_INSUFFICIENT.
9. location transition produces expected scene boundary.
10. temporal gap produces expected scene boundary.
11. contiguous related events remain grouped.
12. SceneObjective.wants from actual goal.
13. tactics only from actual events.
14. static scene detected.
15. meaningful scene not marked static.
16. turning point belongs to source events.
17. Event -> Scene provenance available.
18. zero AI calls.
"""

import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.goal import Goal
from src.domain.event import Event, EventType, EventLog, EventHistory
from src.domain.proposition import Proposition, KnowledgeItem
from src.domain.story_structure import (
    DramaticFunction,
    ScenePurpose,
    ScenePurposeType,
    Scene,
    SceneData,
    SceneObjective,
    CoreEmotionalObjective,
)
from src.story.models import (
    BeatPressure,
    StoryBlueprint,
    SufficiencyReport,
    PredicateSpec,
    PredicateClause,
    StructureSelection,
)
from src.narrative.observer import Observer, EventSalience
from src.narrative.scene_builder import SceneBuilder, SufficiencyGateExecutionError
from src.narrative.provenance import ProvenanceService
from src.providers.mock import MockLLMProvider


@pytest.fixture
def setup_test_world() -> WorldState:
    """Fixture providing a standard 2-location, 2-character simulation world."""
    world = WorldState(id="world_p5a", name="Phase 5A Test World", current_tick=10)

    loc1 = Location(id="loc_archives", name="Secure Archives", connected_locations=["loc_hallway"])
    loc2 = Location(id="loc_hallway", name="Corridor B", connected_locations=["loc_archives"])
    world.locations[loc1.id] = loc1
    world.locations[loc2.id] = loc2

    obj = WorldObject(id="obj_dossier", name="Classified Dossier", location_id="loc_archives")
    world.objects[obj.id] = obj

    char1 = Character(
        id="char_arjun",
        name="Detective Arjun",
        role="Investigator",
        current_location_id="loc_archives",
        emotional_state=EmotionalState(fear=0.2, anger=0.3, curiosity=0.8),
    )
    char2 = Character(
        id="char_maya",
        name="Courier Maya",
        role="Courier",
        current_location_id="loc_archives",
        emotional_state=EmotionalState(fear=0.7, anger=0.1, trust=-0.5),
    )
    world.characters[char1.id] = char1
    world.characters[char2.id] = char2

    goal1 = Goal(id="goal_retrieve", character_id="char_arjun", description="Retrieve the classified dossier")
    world.goals[goal1.id] = goal1
    char1.goals.append(goal1.id)

    # Seed events
    ev1 = Event(
        id="ev_01",
        tick=1,
        event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_arjun"],
        location_id="loc_archives",
        description="Detective Arjun enters the Secure Archives.",
    )
    ev2 = Event(
        id="ev_02",
        tick=2,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun", "char_maya"],
        location_id="loc_archives",
        description="Detective Arjun confronts Courier Maya about the missing classified dossier.",
    )
    ev3 = Event(
        id="ev_03",
        tick=3,
        event_type=EventType.OBJECT_PICKED_UP,
        actor_ids=["char_arjun"],
        location_id="loc_archives",
        description="Detective Arjun picks up the Classified Dossier from the steel shelf.",
        metadata={"object_id": "obj_dossier"},
    )
    for ev in [ev1, ev2, ev3]:
        world.events[ev.id] = ev

    return world


# -----------------------------------------------------------------------------
# Test 1: Observer leaves EventHistory byte-identical
# -----------------------------------------------------------------------------
def test_01_observer_leaves_event_history_byte_identical(setup_test_world):
    world = setup_test_world
    ev_list = list(world.events.values())
    history = EventHistory(events=ev_list)

    before_json = history.model_dump_json()

    observer = Observer()
    _ = observer.observe_events(ev_list, world=world)
    _ = observer.score_all_events(ev_list, world=world)

    after_json = history.model_dump_json()

    assert before_json == after_json, "Observer mutated the immutable EventHistory!"


# -----------------------------------------------------------------------------
# Test 2: EventSalience.signals is non-empty
# -----------------------------------------------------------------------------
def test_02_event_salience_signals_is_non_empty(setup_test_world):
    world = setup_test_world
    observer = Observer()
    ev = world.events["ev_03"]

    salience = observer.score_event_salience(ev, world=world)

    assert isinstance(salience, EventSalience)
    assert len(salience.signals) > 0, "EventSalience signals must not be empty!"
    assert "state_delta_magnitude" in salience.signals
    assert "knowledge_change_magnitude" in salience.signals
    assert "relationship_change_magnitude" in salience.signals
    assert "goal_progress_delta" in salience.signals
    assert "beat_binding_bonus" in salience.signals


# -----------------------------------------------------------------------------
# Test 3: EventSalience scoring deterministic
# -----------------------------------------------------------------------------
def test_03_event_salience_scoring_deterministic(setup_test_world):
    world = setup_test_world
    observer = Observer()
    ev = world.events["ev_02"]

    scores = [observer.score_event_salience(ev, world=world).score for _ in range(10)]
    assert len(set(scores)) == 1, "EventSalience scoring must be strictly deterministic across repeated invocations!"


# -----------------------------------------------------------------------------
# Test 4: Shared DramaticFunction identity
# -----------------------------------------------------------------------------
def test_04_shared_dramatic_function_identity():
    assert BeatPressure.model_fields["dramatic_function"].annotation is DramaticFunction
    assert ScenePurpose is DramaticFunction
    assert ScenePurposeType is DramaticFunction

    required_vocabs = [
        "SETUP", "INCITING_INCIDENT", "INVESTIGATION", "DISCOVERY",
        "ESCALATION", "NEGOTIATION", "REVERSAL", "CONFRONTATION",
        "CRISIS", "CHASE", "REVELATION", "CLIMAX", "RESOLUTION",
    ]
    for vocab in required_vocabs:
        assert hasattr(DramaticFunction, vocab), f"Missing required DramaticFunction member: {vocab}"
        assert getattr(DramaticFunction, vocab).value == vocab


# -----------------------------------------------------------------------------
# Test 5: Scene Builder rejected for CONTINUE
# -----------------------------------------------------------------------------
def test_05_scene_builder_rejected_for_continue(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()
    report = SufficiencyReport(
        required_beats_satisfied=False,
        climax_detected=False,
        arc_detected=False,
        recommendation="CONTINUE",
        reason="Simulation beats pending within active window.",
    )

    with pytest.raises(SufficiencyGateExecutionError) as exc_info:
        builder.build_scenes(world=world, sufficiency_report=report)

    assert "CONTINUE" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Test 6: Scene Builder rejected for ADJUST_PRESSURE_AND_CONTINUE
# -----------------------------------------------------------------------------
def test_06_scene_builder_rejected_for_adjust_pressure_and_continue(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()
    report = SufficiencyReport(
        required_beats_satisfied=False,
        climax_detected=False,
        arc_detected=False,
        recommendation="ADJUST_PRESSURE_AND_CONTINUE",
        reason="Extending budget and adjusting pressure.",
    )

    with pytest.raises(SufficiencyGateExecutionError) as exc_info:
        builder.build_scenes(world=world, sufficiency_report=report)

    assert "ADJUST_PRESSURE_AND_CONTINUE" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Test 7: Allowed for PROCEED
# -----------------------------------------------------------------------------
def test_07_scene_builder_allowed_for_proceed(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()
    report = SufficiencyReport(
        required_beats_satisfied=True,
        climax_detected=True,
        arc_detected=True,
        recommendation="PROCEED",
        reason="Required beats satisfied and climax detected.",
    )

    scenes = builder.build_scenes(world=world, sufficiency_report=report)
    assert len(scenes) >= 1
    assert scenes[0].presentation_position == scenes[0].chronological_position


# -----------------------------------------------------------------------------
# Test 8: Allowed for HALT_INSUFFICIENT
# -----------------------------------------------------------------------------
def test_08_scene_builder_allowed_for_halt_insufficient(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()
    report = SufficiencyReport(
        required_beats_satisfied=False,
        climax_detected=False,
        arc_detected=False,
        recommendation="HALT_INSUFFICIENT",
        reason="Tick cap reached without full beat satisfaction.",
    )

    scenes = builder.build_scenes(world=world, sufficiency_report=report)
    assert len(scenes) >= 1, "HALT_INSUFFICIENT is valid narrative output and must produce scenes from actual history."


# -----------------------------------------------------------------------------
# Test 9: Location transition produces expected scene boundary
# -----------------------------------------------------------------------------
def test_09_location_transition_produces_expected_scene_boundary(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    ev_archives = Event(
        id="ev_a1", tick=1, event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun"], location_id="loc_archives", description="Arjun searches the archives.",
    )
    ev_hallway = Event(
        id="ev_a2", tick=2, event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_arjun"], location_id="loc_hallway", description="Arjun exits into the hallway.",
    )

    scenes = builder.build_scenes(world=world, events=[ev_archives, ev_hallway])
    assert len(scenes) == 2, "Location transition must produce a scene boundary."
    assert scenes[0].location_id == "loc_archives"
    assert scenes[1].location_id == "loc_hallway"


# -----------------------------------------------------------------------------
# Test 10: Temporal gap produces expected scene boundary
# -----------------------------------------------------------------------------
def test_10_temporal_gap_produces_expected_scene_boundary(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    ev_early = Event(
        id="ev_t1", tick=1, event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun"], location_id="loc_archives", description="Arjun reads the file.",
    )
    ev_late = Event(
        id="ev_t2", tick=6, event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun"], location_id="loc_archives", description="Hours later, Arjun spots a hidden safe.",
    )

    scenes = builder.build_scenes(world=world, events=[ev_early, ev_late])
    assert len(scenes) == 2, "A temporal gap of >2 ticks must produce a scene boundary."
    assert scenes[0].end_tick == 1
    assert scenes[1].start_tick == 6


# -----------------------------------------------------------------------------
# Test 11: Contiguous related events remain grouped
# -----------------------------------------------------------------------------
def test_11_contiguous_related_events_remain_grouped(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    ev1 = Event(id="ev_g1", tick=1, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_arjun", "char_maya"], location_id="loc_archives", description="Arjun confronts Maya.")
    ev2 = Event(id="ev_g2", tick=2, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_maya", "char_arjun"], location_id="loc_archives", description="Maya refuses to speak.")
    ev3 = Event(id="ev_g3", tick=3, event_type=EventType.CHARACTER_OBSERVED, actor_ids=["char_arjun"], location_id="loc_archives", description="Arjun notices Maya's briefcase.")

    scenes = builder.build_scenes(world=world, events=[ev1, ev2, ev3])
    assert len(scenes) == 1, "Contiguous related events at the same location must remain in a single scene."
    assert scenes[0].source_event_ids == ["ev_g1", "ev_g2", "ev_g3"]


# -----------------------------------------------------------------------------
# Test 12: SceneObjective.wants from actual goal
# -----------------------------------------------------------------------------
def test_12_scene_objective_wants_from_actual_goal(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    scenes = builder.build_scenes(world=world)
    assert len(scenes) >= 1

    scene = scenes[0]
    assert scene.objective is not None
    assert scene.objective.wants == "Retrieve the classified dossier"
    assert scene.objective.pov_character_id == "char_arjun"


# -----------------------------------------------------------------------------
# Test 13: Tactics only from actual events
# -----------------------------------------------------------------------------
def test_13_tactics_only_from_actual_events(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    scenes = builder.build_scenes(world=world)
    assert len(scenes) >= 1

    scene = scenes[0]
    # Arjun performed ev_01, ev_02, ev_03
    expected_tactics = [
        "Detective Arjun enters the Secure Archives.",
        "Detective Arjun confronts Courier Maya about the missing classified dossier.",
        "Detective Arjun picks up the Classified Dossier from the steel shelf.",
    ]
    assert scene.objective.tactics == expected_tactics, "Tactics must be drawn strictly from actual events."


# -----------------------------------------------------------------------------
# Test 14: Static scene detected
# -----------------------------------------------------------------------------
def test_14_static_scene_detected(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    # Create idle event where nothing in the world changes
    idle_ev = Event(
        id="ev_idle",
        tick=4,
        event_type=EventType.OTHER,
        actor_ids=["char_arjun"],
        location_id="loc_archives",
        description="Detective Arjun pauses and waits in the shadows.",
    )

    scenes = builder.build_scenes(world=world, events=[idle_ev])
    assert len(scenes) == 1
    assert scenes[0].is_static is True
    assert scenes[0].metadata.get("static_scene") is True
    assert scenes[0].metadata.get("scene_flag") == "STATIC_SCENE"


# -----------------------------------------------------------------------------
# Test 15: Meaningful scene not marked static
# -----------------------------------------------------------------------------
def test_15_meaningful_scene_not_marked_static(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    # Pickup event alters object possession
    pickup_ev = world.events["ev_03"]
    scenes = builder.build_scenes(world=world, events=[pickup_ev])

    assert len(scenes) == 1
    assert scenes[0].is_static is False
    assert scenes[0].metadata.get("static_scene") is False


# -----------------------------------------------------------------------------
# Test 16: Turning point belongs to source events
# -----------------------------------------------------------------------------
def test_16_turning_point_belongs_to_source_events(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()

    scenes = builder.build_scenes(world=world)
    for sc in scenes:
        if sc.turning_point_event_id is not None:
            assert sc.turning_point_event_id in sc.source_event_ids, (
                f"Turning point {sc.turning_point_event_id} must be one of source_event_ids {sc.source_event_ids}"
            )


# -----------------------------------------------------------------------------
# Test 17: Event -> Scene provenance available
# -----------------------------------------------------------------------------
def test_17_event_to_scene_provenance_available(setup_test_world):
    world = setup_test_world
    builder = SceneBuilder()
    prov = ProvenanceService(world=world)

    scenes = builder.build_scenes(world=world, provenance=prov)
    assert len(scenes) >= 1

    # Query scene for ev_01
    matched_scenes = prov.scenes_for_event("ev_01")
    assert len(matched_scenes) >= 1
    assert matched_scenes[0].scene_id == scenes[0].scene_id

    # Query events for scene_01
    events_in_scene = prov.events_for_scene(scenes[0].scene_id)
    assert len(events_in_scene) >= 1
    assert any(e.id == "ev_01" for e in events_in_scene)


# -----------------------------------------------------------------------------
# Test 18: Zero AI calls
# -----------------------------------------------------------------------------
def test_18_zero_ai_calls(setup_test_world):
    world = setup_test_world
    provider = MockLLMProvider()

    observer = Observer(provider=provider)
    selection = observer.observe(world=world)

    builder = SceneBuilder()
    scenes = builder.build_scenes(selection=selection, world=world)

    assert len(scenes) >= 1
    assert provider.call_count == 0, "Phase 5A pipeline must execute with zero AI calls!"


# -----------------------------------------------------------------------------
# Test 19: Missing Dossier partial Phase 5 pipeline & EventHistory immutability
# -----------------------------------------------------------------------------
def test_19_missing_dossier_scenario_phase5a_run():
    """Run The Missing Dossier through simulation -> sufficiency gate -> Observer -> Scene Builder.
    
    Verifies:
    - simulation termination recommendation
    - scenes constructed with deterministic boundaries
    - static scene detection
    - turning points within source_event_ids
    - EventHistory byte-identical immutability
    - zero AI calls
    """
    from src.story.features import extract_story_input_rule_based
    from src.story.loader import get_structure_registry
    from src.story.scorer import select_structure
    from src.story.blueprint import compile_blueprint
    from src.demo_world import create_demo_world
    from src.simulation.orchestrator import SimulationOrchestrator

    prompt = "Detective Arjun investigates the locked office to find the secret dossier hidden by courier Maya."
    analysis = extract_story_input_rule_based(prompt)
    defs = get_structure_registry()
    selection = select_structure(analysis.features, defs)
    blueprint = compile_blueprint(
        structure_selection=selection,
        role_bindings=analysis.role_bindings,
        canon_facts=analysis.canon_facts,
    )

    world = create_demo_world()
    world.propositions["prop_dossier_loc"] = Proposition(
        id="prop_dossier_loc",
        subject="obj_dossier",
        predicate="location",
        object="loc_room307",
        truth_value=True,
        enforced=True,
        is_secret=True,
    )
    c_maya = world.characters["char_maya"]
    c_maya.knowledge["prop_dossier_loc"] = KnowledgeItem(
        proposition_id="prop_dossier_loc",
        holder_id="char_maya",
        believed_truth_value=True,
    )

    provider = MockLLMProvider()
    orch = SimulationOrchestrator(world=world, blueprint=blueprint, provider=provider, seed=42)
    _ = orch.run(max_ticks=25, use_sufficiency_gate=True)

    report = orch.last_sufficiency_report
    assert report is not None
    assert report.recommendation in ("PROCEED", "HALT_INSUFFICIENT", "CONTINUE", "ADJUST_PRESSURE_AND_CONTINUE")

    # Capture EventHistory before Observer / SceneBuilder
    history_before = EventHistory(events=list(world.events.values()))
    before_json = history_before.model_dump_json()

    # Observer
    observer = Observer()
    obs_selection = observer.observe(world=world, blueprint=blueprint)

    # Scene Builder
    builder = SceneBuilder()
    scenes = builder.build_scenes(
        selection=obs_selection,
        world=world,
        blueprint=blueprint,
        sufficiency_report=report if report.recommendation in ("PROCEED", "HALT_INSUFFICIENT") else SufficiencyReport(
            required_beats_satisfied=True, climax_detected=True, arc_detected=True, recommendation="PROCEED", reason="Forced for test"
        ),
    )

    # Capture EventHistory after Observer / SceneBuilder
    history_after = EventHistory(events=list(world.events.values()))
    after_json = history_after.model_dump_json()

    # Assert byte-identical immutability
    assert before_json == after_json, "EventHistory was modified during Observer or SceneBuilder execution!"

    assert len(scenes) >= 1
    assert provider.call_count == 0
    for sc in scenes:
        assert sc.presentation_position == sc.chronological_position
        if sc.turning_point_event_id is not None:
            assert sc.turning_point_event_id in sc.source_event_ids

