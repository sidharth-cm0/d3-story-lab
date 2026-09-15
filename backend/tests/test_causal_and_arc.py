"""Tests for CausalContinuityAnalyzer and observational CharacterArcTracker."""

import pytest
from src.domain.world import WorldState, Location, Character, Relationship
from src.domain.event import Event, EventType
from src.domain.story_structure import CausalTransitionType
from src.narrative.causal_analyzer import CausalContinuityAnalyzer
from src.narrative.arc_tracker import CharacterArcTracker


def test_causal_continuity_analyzer_scores_therefore_vs_and_then():
    """Verify that CausalContinuityAnalyzer correctly flags Therefore/But vs And-Then transitions without rewriting history."""
    ev1 = Event(id="ev_01", tick=1, event_type=EventType.CHARACTER_MOVED, description="Detective enters warehouse stealthily", actor_ids=["char_det"])
    ev2 = Event(id="ev_02", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Courier lies and denies knowing about the dossier", actor_ids=["char_courier"])
    ev3 = Event(id="ev_03", tick=3, event_type=EventType.CHARACTER_SPOKE, description="Detective challenges courier's statement pointing to the padlock", actor_ids=["char_det"])
    ev4 = Event(id="ev_04", tick=4, event_type=EventType.OBJECT_PICKED_UP, description="Detective unlocks the safe and secures the dossier", actor_ids=["char_det"])

    events = [ev1, ev2, ev3, ev4]
    original_event_count = len(events)
    original_descriptions = [e.description for e in events]

    analyzer = CausalContinuityAnalyzer()
    summary = analyzer.analyze_event_causality(events)

    assert summary.total_transitions == 3
    assert summary.but_therefore_count >= 2
    assert summary.but_therefore_ratio >= 0.60
    assert summary.overall_causal_score >= 70.0
    assert summary.pressure_recommendation is not None

    # Verify transition reports
    for t in summary.transitions:
        assert t.score > 0.0
        assert t.rationale
        assert t.transition_type in (CausalTransitionType.BUT_THEREFORE, CausalTransitionType.AND_THEN)

    # CRITICAL INVARIANT: History must NEVER be rewritten
    assert len(events) == original_event_count
    for i, e in enumerate(events):
        assert e.description == original_descriptions[i]


def test_causal_continuity_analyzer_detects_and_then_sequences():
    """Verify that episodic unprompted movements are scored as AND THEN with soft director feedback."""
    ev1 = Event(id="ev_01", tick=1, event_type=EventType.CHARACTER_MOVED, description="Guard paces across corridor", actor_ids=["char_guard"])
    ev2 = Event(id="ev_02", tick=2, event_type=EventType.CHARACTER_MOVED, description="Guard walks to outer dock gate", actor_ids=["char_guard"])
    ev3 = Event(id="ev_03", tick=3, event_type=EventType.CHARACTER_MOVED, description="Guard inspects empty perimeter fence", actor_ids=["char_guard"])

    analyzer = CausalContinuityAnalyzer()
    summary = analyzer.analyze_event_causality([ev1, ev2, ev3])

    assert summary.and_then_count >= 2
    assert summary.but_therefore_ratio <= 0.40
    # Recommendation should inform Director to inject external pressure
    assert "pacing signal for director" in summary.pressure_recommendation.lower() or "episodic" in summary.pressure_recommendation.lower()


def test_character_arc_tracker_is_strictly_observational_without_mutation():
    """Verify CharacterArcTracker has no mutation methods and reads history post-hoc."""
    char_det = Character(id="char_det", name="Miller", role="Detective", current_location_id="loc_1", personality_traits={"suspicious": 0.8, "methodical": 0.9})
    char_courier = Character(id="char_courier", name="Leo", role="Courier", current_location_id="loc_1")
    rel = Relationship(id="rel_1", character_a_id="char_det", character_b_id="char_courier", affinity=-0.2, trust=-0.4)

    world = WorldState(
        id="test_w",
        name="Test World",
        current_tick=4,
        locations={"loc_1": Location(id="loc_1", name="Room")},
        characters={"char_det": char_det, "char_courier": char_courier},
        relationships={"rel_1": rel},
    )

    events = [
        Event(id="ev_1", tick=1, event_type=EventType.CHARACTER_MOVED, description="Miller enters room", actor_ids=["char_det"]),
        Event(id="ev_2", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Miller interrogates Leo", actor_ids=["char_det"]),
        Event(id="ev_3", tick=3, event_type=EventType.EMOTION_CHANGED, description="Miller's suspicion spikes sharply", actor_ids=["char_det"], metadata={"emotional_state": {"fear": 0.2, "anger": 0.7}}),
        Event(id="ev_4", tick=4, event_type=EventType.BELIEF_FORMED, description="Miller forms belief: Leo is actively concealing the document", actor_ids=["char_det"]),
    ]

    tracker = CharacterArcTracker()

    # Verify no mutation API exists on tracker
    forbidden_mutation_methods = ["mutate", "update_world", "set_character_state", "force_transformation", "alter_history"]
    for method in forbidden_mutation_methods:
        assert not hasattr(tracker, method), f"Tracker must not expose mutation method {method}"

    report = tracker.trace_arc("char_det", world, events)

    assert report.is_observed_only is True
    assert report.character_name == "Miller"
    assert len(report.major_decisions) >= 1
    assert len(report.key_turns) == 2
    assert report.arc_trajectory in ("REVELATION", "TRANSFORMATION", "DISILLUSIONMENT")
    assert "Leo" in report.relationship_deltas

    # Verify world state and character were completely unmutated
    assert char_det.name == "Miller"
    assert len(world.events) == 0  # world.events was not mutated by tracker
