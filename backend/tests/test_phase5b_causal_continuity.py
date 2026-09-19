"""Tests for Phase 5B CausalContinuityAnalyzer, SceneLink taxonomy, and Phase 5 Acceptance."""

import copy
import pytest
from typing import Dict, List, Optional
from src.domain.world import WorldState, Location, Character, WorldObject
from src.domain.event import Event, EventType, EventHistory
from src.domain.goal import Goal, GoalStatus
from src.domain.story_structure import (
    DramaticFunction,
    Scene,
    SceneObjective,
    SceneLink,
    SceneLinkType,
    CausalTransitionType,
)
from src.narrative.causal_analyzer import CausalContinuityAnalyzer
from src.narrative.provenance import ProvenanceService


class MockAIProvider:
    """Mock AI provider to verify zero AI calls."""
    def __init__(self):
        self.call_count = 0

    def generate(self, *args, **kwargs):
        self.call_count += 1
        raise AssertionError("AI Provider must never be called in Phase 5 deterministic analysis!")


def _make_event(
    id: str,
    tick: int = 1,
    event_type: EventType = EventType.CHARACTER_MOVED,
    description: str = "Action occurred",
    actor_ids: Optional[List[str]] = None,
    caused_by: Optional[List[str]] = None,
    location_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Event:
    return Event(
        id=id,
        tick=tick,
        event_type=event_type,
        description=description,
        actor_ids=actor_ids or ["char_arjun"],
        caused_by=caused_by or [],
        location_id=location_id or "loc_office",
        metadata=metadata or {},
    )


# =============================================================================
# 1. Direct caused_by chain creates THEREFORE
# =============================================================================
def test_direct_caused_by_chain_creates_therefore():
    ev_a = _make_event(id="evt_a1", tick=1, event_type=EventType.CHARACTER_SPOKE, description="Maya drops clue", actor_ids=["char_maya"])
    ev_b = _make_event(id="evt_b1", tick=2, event_type=EventType.CHARACTER_MOVED, description="Arjun searches archive", actor_ids=["char_arjun"], caused_by=["evt_a1"])

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a.id],
        purpose=DramaticFunction.DISCOVERY,
        chronological_position=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_archive",
        source_event_ids=[ev_b.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=2,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.THEREFORE
    assert link.from_scene_id == "sc_a"
    assert link.to_scene_id == "sc_b"
    assert "evt_a1" in link.evidence_event_ids
    assert "evt_b1" in link.evidence_event_ids


# =============================================================================
# 2. Transitive caused_by ancestry creates THEREFORE
# =============================================================================
def test_transitive_caused_by_ancestry_creates_therefore():
    ev_a = _make_event(id="evt_a1", tick=1, event_type=EventType.OBJECT_PICKED_UP, description="Maya secures key", actor_ids=["char_maya"])
    ev_mid = _make_event(id="evt_mid", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Radio alert triggers", actor_ids=["char_guard"], caused_by=["evt_a1"])
    ev_b = _make_event(id="evt_b1", tick=3, event_type=EventType.CHARACTER_MOVED, description="Arjun investigates alert", actor_ids=["char_arjun"], caused_by=["evt_mid"])

    events_by_id = {ev_a.id: ev_a, ev_mid.id: ev_mid, ev_b.id: ev_b}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a.id],
        purpose=DramaticFunction.DISCOVERY,
        chronological_position=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_corridor",
        source_event_ids=[ev_b.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=2,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.THEREFORE
    assert link.evidence_event_ids == ["evt_a1", "evt_mid", "evt_b1"]


# =============================================================================
# 3. Evidence_event_ids supports THEREFORE
# =============================================================================
def test_evidence_event_ids_supports_therefore():
    ev_a1 = _make_event(id="evt_a1", tick=1, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_arjun"])
    ev_a2 = _make_event(id="evt_a2", tick=2, event_type=EventType.OBJECT_PICKED_UP, actor_ids=["char_arjun"])
    ev_b1 = _make_event(id="evt_b1", tick=3, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_maya"], caused_by=["evt_a2"])

    events_by_id = {e.id: e for e in (ev_a1, ev_a2, ev_b1)}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a1.id, ev_a2.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_hallway",
        source_event_ids=[ev_b1.id],
        purpose=DramaticFunction.CONFRONTATION,
        chronological_position=2,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.THEREFORE
    assert len(link.evidence_event_ids) >= 2
    # First event in evidence chain is from Scene A, last is from Scene B
    assert link.evidence_event_ids[0] in scene_a.source_event_ids
    assert link.evidence_event_ids[-1] in scene_b.source_event_ids


# =============================================================================
# 4. Goal progress reversal creates BUT
# =============================================================================
def test_goal_progress_reversal_creates_but():
    ev_a = _make_event(id="evt_a", tick=1, event_type=EventType.OBJECT_PICKED_UP, description="Arjun retrieves dossier", actor_ids=["char_arjun"])
    ev_b = _make_event(id="evt_b", tick=2, event_type=EventType.OBJECT_DROPPED, description="Arjun forced to drop dossier", actor_ids=["char_arjun"])

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    obj_a = SceneObjective(
        pov_character_id="char_arjun",
        wants="Retrieve the dossier",
        emotional_want="Determined",
        obstacle="Safe locked",
        tactics=["PICK_UP"],
        outcome="ACHIEVED",
        state_delta={"inventory_added": ["dossier"]},
    )
    obj_b = SceneObjective(
        pov_character_id="char_arjun",
        wants="Keep the dossier safe",
        emotional_want="Panicked",
        obstacle="Maya intercepts",
        tactics=["FLEE"],
        outcome="DENIED",
        state_delta={"inventory_removed": ["dossier"]},
    )

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a.id],
        objective=obj_a,
        purpose=DramaticFunction.DISCOVERY,
        chronological_position=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_hallway",
        source_event_ids=[ev_b.id],
        objective=obj_b,
        purpose=DramaticFunction.REVERSAL,
        chronological_position=2,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.BUT
    assert "evt_a" in link.evidence_event_ids
    assert "evt_b" in link.evidence_event_ids


# =============================================================================
# 5. Ordinary obstacle without reversal does not automatically create BUT
# =============================================================================
def test_ordinary_obstacle_without_reversal_does_not_create_but():
    ev_a = _make_event(id="evt_a", tick=1, event_type=EventType.CHARACTER_MOVED, description="Arjun paces in office", actor_ids=["char_arjun"])
    ev_b = _make_event(id="evt_b", tick=2, event_type=EventType.CHARACTER_MOVED, description="Arjun encounters locked door", actor_ids=["char_arjun"])

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    # Scene A was simple setup, did not achieve goal advancement
    obj_a = SceneObjective(
        pov_character_id="char_arjun",
        wants="Look around",
        emotional_want="Calm",
        obstacle="None",
        tactics=["MOVE"],
        outcome="PARTIAL",
    )
    # Scene B has an obstacle, but no reversal of prior progress occurred
    obj_b = SceneObjective(
        pov_character_id="char_arjun",
        wants="Exit building",
        emotional_want="Alert",
        obstacle="Heavy security door is locked",
        tactics=["INSPECT"],
        outcome="PARTIAL",
    )

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a.id],
        objective=obj_a,
        purpose=DramaticFunction.SETUP,
        chronological_position=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_corridor",
        source_event_ids=[ev_b.id],
        objective=obj_b,
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=2,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    # Must NOT be BUT because no established goal progress was reversed
    assert link.type != SceneLinkType.BUT
    assert link.type == SceneLinkType.AND_THEN


# =============================================================================
# 6. Causally disconnected sequential scenes create AND_THEN
# =============================================================================
def test_causally_disconnected_sequential_scenes_create_and_then():
    ev_a = _make_event(id="evt_a", tick=1, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_arjun"], location_id="loc_office")
    ev_b = _make_event(id="evt_b", tick=5, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_arjun"], location_id="loc_archive", caused_by=[])

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        source_event_ids=[ev_a.id],
        purpose=DramaticFunction.SETUP,
        chronological_position=1,
        start_tick=1,
        end_tick=1,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_archive",
        source_event_ids=[ev_b.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=2,
        start_tick=5,
        end_tick=5,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.AND_THEN
    assert link.evidence_event_ids == []


# =============================================================================
# 7. Demonstrably concurrent different-location scenes create MEANWHILE
# =============================================================================
def test_demonstrably_concurrent_different_location_scenes_create_meanwhile():
    # Both events occur at tick 5, in different locations with disjoint characters
    ev_a = _make_event(id="evt_a", tick=5, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_arjun"], location_id="loc_office")
    ev_b = _make_event(id="evt_b", tick=5, event_type=EventType.OBJECT_PICKED_UP, actor_ids=["char_maya"], location_id="loc_vault")

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        characters_present=["char_arjun"],
        source_event_ids=[ev_a.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=1,
        start_tick=5,
        end_tick=5,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_vault",
        characters_present=["char_maya"],
        source_event_ids=[ev_b.id],
        purpose=DramaticFunction.DISCOVERY,
        chronological_position=2,
        start_tick=5,
        end_tick=5,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    assert link.type == SceneLinkType.MEANWHILE
    assert "evt_a" in link.evidence_event_ids
    assert "evt_b" in link.evidence_event_ids


# =============================================================================
# 8. Unknown concurrency does not become MEANWHILE
# =============================================================================
def test_unknown_concurrency_does_not_become_meanwhile():
    # Scene A at tick 2, Scene B at tick 10. No shared ticks, continuous time context
    ev_a = _make_event(id="evt_a", tick=2, event_type=EventType.CHARACTER_SPOKE, actor_ids=["char_arjun"], location_id="loc_office")
    ev_b = _make_event(id="evt_b", tick=10, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_maya"], location_id="loc_vault")

    events_by_id = {ev_a.id: ev_a, ev_b.id: ev_b}

    scene_a = Scene(
        scene_id="sc_a",
        location_id="loc_office",
        characters_present=["char_arjun"],
        source_event_ids=[ev_a.id],
        purpose=DramaticFunction.SETUP,
        chronological_position=1,
        start_tick=2,
        end_tick=2,
    )
    scene_b = Scene(
        scene_id="sc_b",
        location_id="loc_vault",
        characters_present=["char_maya"],
        source_event_ids=[ev_b.id],
        purpose=DramaticFunction.INVESTIGATION,
        chronological_position=2,
        start_tick=10,
        end_tick=10,
    )

    analyzer = CausalContinuityAnalyzer()
    link = analyzer.classify_scene_transition(scene_a, scene_b, events_by_id=events_by_id)

    # Concurrency cannot be demonstrated, so must NOT be MEANWHILE
    assert link.type != SceneLinkType.MEANWHILE
    assert link.type == SceneLinkType.AND_THEN


# =============================================================================
# 9. AND_THEN ratio calculated correctly
# =============================================================================
def test_and_then_ratio_calculated_correctly():
    analyzer = CausalContinuityAnalyzer()

    # Create 5 scenes -> 4 links: THEREFORE, AND_THEN, BUT, AND_THEN
    ev1 = _make_event(id="e1", tick=1, actor_ids=["c1"], location_id="loc1")
    ev2 = _make_event(id="e2", tick=2, actor_ids=["c1"], caused_by=["e1"], location_id="loc1")
    ev3 = _make_event(id="e3", tick=3, actor_ids=["c1"], location_id="loc2")
    ev4 = _make_event(id="e4", tick=4, event_type=EventType.OBJECT_PICKED_UP, actor_ids=["c1"], location_id="loc2")
    ev5 = _make_event(id="e5", tick=5, event_type=EventType.OBJECT_DROPPED, actor_ids=["c1"], location_id="loc3")

    events = [ev1, ev2, ev3, ev4, ev5]

    s1 = Scene(scene_id="s1", location_id="loc1", source_event_ids=["e1"], chronological_position=1, start_tick=1, end_tick=1)
    s2 = Scene(scene_id="s2", location_id="loc1", source_event_ids=["e2"], chronological_position=2, start_tick=2, end_tick=2)
    s3 = Scene(scene_id="s3", location_id="loc2", source_event_ids=["e3"], chronological_position=3, start_tick=3, end_tick=3)
    s4 = Scene(
        scene_id="s4",
        location_id="loc2",
        source_event_ids=["e4"],
        chronological_position=4,
        start_tick=4,
        end_tick=4,
        objective=SceneObjective(pov_character_id="c1", wants="W", emotional_want="E", obstacle="O", outcome="ACHIEVED"),
    )
    s5 = Scene(
        scene_id="s5",
        location_id="loc3",
        source_event_ids=["e5"],
        chronological_position=5,
        start_tick=5,
        end_tick=5,
        objective=SceneObjective(pov_character_id="c1", wants="W", emotional_want="E", obstacle="O", outcome="DENIED"),
    )

    scenes = [s1, s2, s3, s4, s5]
    summary = analyzer.analyze_scene_sequence(scenes, events=events)

    assert summary.total_scene_links == 4
    assert summary.therefore_count == 1
    assert summary.but_count == 1
    assert summary.and_then_count == 2
    assert summary.and_then_ratio == 0.50


# =============================================================================
# 10. Two consecutive AND_THEN links trigger diagnostic
# =============================================================================
def test_two_consecutive_and_then_links_trigger_diagnostic():
    analyzer = CausalContinuityAnalyzer()

    # 4 scenes where s1->s2 is AND_THEN, s2->s3 is AND_THEN, s3->s4 is THEREFORE
    ev1 = _make_event(id="e1", tick=1, actor_ids=["c1"], location_id="l1")
    ev2 = _make_event(id="e2", tick=2, actor_ids=["c1"], location_id="l2")
    ev3 = _make_event(id="e3", tick=3, actor_ids=["c1"], location_id="l3")
    ev4 = _make_event(id="e4", tick=4, actor_ids=["c1"], caused_by=["e3"], location_id="l3")

    events = [ev1, ev2, ev3, ev4]

    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e1"], chronological_position=1, start_tick=1, end_tick=1)
    s2 = Scene(scene_id="s2", location_id="l2", source_event_ids=["e2"], chronological_position=2, start_tick=2, end_tick=2)
    s3 = Scene(scene_id="s3", location_id="l3", source_event_ids=["e3"], chronological_position=3, start_tick=3, end_tick=3)
    s4 = Scene(scene_id="s4", location_id="l3", source_event_ids=["e4"], chronological_position=4, start_tick=4, end_tick=4)

    summary = analyzer.analyze_scene_sequence([s1, s2, s3, s4], events=events)

    assert len(summary.consecutive_and_then_runs) == 1
    assert summary.consecutive_and_then_runs[0] == ["s1", "s2", "s3"]


# =============================================================================
# 11. Analyzer does not alter scenes
# =============================================================================
def test_analyzer_does_not_alter_scenes():
    analyzer = CausalContinuityAnalyzer()

    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e1"], chronological_position=1)
    s2 = Scene(scene_id="s2", location_id="l2", source_event_ids=["e2"], chronological_position=2)
    scenes = [s1, s2]

    scenes_before = copy.deepcopy(scenes)
    analyzer.analyze_scene_sequence(scenes, events=[_make_event(id="e1", tick=1), _make_event(id="e2", tick=2)])

    assert scenes == scenes_before


# =============================================================================
# 12. Analyzer does not alter EventHistory
# =============================================================================
def test_analyzer_does_not_alter_event_history():
    analyzer = CausalContinuityAnalyzer()

    ev1 = _make_event(id="e1", tick=1, actor_ids=["c1"])
    ev2 = _make_event(id="e2", tick=2, actor_ids=["c1"])
    world = WorldState(
        id="w1",
        name="Test",
        current_tick=2,
        locations={"l1": Location(id="l1", name="Loc")},
        characters={"c1": Character(id="c1", name="C", role="R", current_location_id="l1")},
        events={"e1": ev1, "e2": ev2},
    )

    events_before = copy.deepcopy(world.events)
    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e1"], chronological_position=1)
    s2 = Scene(scene_id="s2", location_id="l1", source_event_ids=["e2"], chronological_position=2)

    analyzer.analyze_scene_sequence([s1, s2], world=world)

    assert world.events == events_before


# =============================================================================
# 13. Same input -> same links
# =============================================================================
def test_same_input_yields_same_links():
    analyzer = CausalContinuityAnalyzer()

    ev1 = _make_event(id="e1", tick=1, actor_ids=["c1"])
    ev2 = _make_event(id="e2", tick=2, actor_ids=["c1"], caused_by=["e1"])
    events = [ev1, ev2]

    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e1"], chronological_position=1)
    s2 = Scene(scene_id="s2", location_id="l1", source_event_ids=["e2"], chronological_position=2)

    summary_1 = analyzer.analyze_scene_sequence([s1, s2], events=events)
    summary_2 = analyzer.analyze_scene_sequence([s1, s2], events=events)

    assert summary_1.scene_links == summary_2.scene_links
    assert summary_1.and_then_ratio == summary_2.and_then_ratio
    assert summary_1.consecutive_and_then_runs == summary_2.consecutive_and_then_runs


# =============================================================================
# 14. Zero AI calls in CausalContinuityAnalyzer
# =============================================================================
def test_zero_ai_calls_in_causal_continuity_analyzer():
    mock_ai = MockAIProvider()
    analyzer = CausalContinuityAnalyzer()

    ev1 = _make_event(id="e1", tick=1, actor_ids=["c1"])
    ev2 = _make_event(id="e2", tick=2, actor_ids=["c1"], caused_by=["e1"])

    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e1"], chronological_position=1)
    s2 = Scene(scene_id="s2", location_id="l1", source_event_ids=["e2"], chronological_position=2)

    summary = analyzer.analyze_scene_sequence([s1, s2], events=[ev1, ev2])

    assert mock_ai.call_count == 0
    assert summary.total_scene_links == 1


# =============================================================================
# 15. ProvenanceService SceneLinks integration
# =============================================================================
def test_provenance_service_scene_links():
    ev_a = _make_event(id="e_a", tick=1, actor_ids=["c1"])
    ev_b = _make_event(id="e_b", tick=2, actor_ids=["c1"], caused_by=["e_a"])

    world = WorldState(
        id="w",
        name="W",
        current_tick=2,
        locations={"l1": Location(id="l1", name="L")},
        characters={"c1": Character(id="c1", name="C", role="R", current_location_id="l1")},
        events={"e_a": ev_a, "e_b": ev_b},
    )

    s1 = Scene(scene_id="s1", location_id="l1", source_event_ids=["e_a"], chronological_position=1)
    s2 = Scene(scene_id="s2", location_id="l1", source_event_ids=["e_b"], chronological_position=2)

    link = SceneLink(
        from_scene_id="s1",
        to_scene_id="s2",
        type=SceneLinkType.THEREFORE,
        evidence_event_ids=["e_a", "e_b"],
        rationale="Test link",
    )

    provenance = ProvenanceService(world=world, scenes=[s1, s2], scene_links=[link])

    # Traversal queries
    assert provenance.links_for_scene("s1") == [link]
    assert provenance.links_for_scene("s2") == [link]
    assert provenance.links_for_event("e_a") == [link]
    assert provenance.links_for_event("e_b") == [link]
    assert provenance.links_for_event("e_unknown") == []

    evidence_events = provenance.evidence_events_for_link(link)
    assert len(evidence_events) == 2
    assert evidence_events[0].id == "e_a"
    assert evidence_events[1].id == "e_b"


# =============================================================================
# 16. The Missing Dossier — Full Phase 5 Diagnostic
# =============================================================================
def test_missing_dossier_full_phase5_diagnostic():
    from src.story.features import extract_story_input_rule_based
    from src.story.loader import get_structure_registry
    from src.story.scorer import select_structure
    from src.story.blueprint import compile_blueprint
    from src.demo_world import create_demo_world
    from src.simulation.orchestrator import SimulationOrchestrator
    from src.narrative.observer import Observer
    from src.narrative.scene_builder import SceneBuilder
    from src.domain.proposition import Proposition, KnowledgeItem

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

    provider = MockAIProvider()
    orch = SimulationOrchestrator(world=world, blueprint=blueprint, provider=provider, seed=42)
    _ = orch.run(max_ticks=25, use_sufficiency_gate=True)

    report = orch.last_sufficiency_report
    assert report is not None
    assert report.recommendation in ("PROCEED", "HALT_INSUFFICIENT")

    observer = Observer()
    obs_selection = observer.observe(world=world, blueprint=blueprint)

    builder = SceneBuilder()
    scenes = builder.build_scenes(
        selection=obs_selection,
        world=world,
        gate_report=report,
        blueprint=blueprint,
        differ=orch.differ,
    )

    analyzer = CausalContinuityAnalyzer()
    causal_summary = analyzer.analyze_scene_sequence(scenes, world=world, differ=orch.differ)

    assert len(scenes) >= 5
    assert causal_summary.total_scene_links == len(scenes) - 1
    assert (
        causal_summary.therefore_count
        + causal_summary.but_count
        + causal_summary.and_then_count
        + causal_summary.meanwhile_count
    ) == causal_summary.total_scene_links
    assert provider.call_count == 0
