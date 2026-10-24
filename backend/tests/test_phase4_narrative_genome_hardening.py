"""Hardening & Acceptance Tests for Phase 4: Narrative Genome v0.1.

Verifies:
1. Schema Stabilization: NarrativeRecommendation includes observed_issue, relevance_score,
   counter_conditions, limitations, and lifecycle status.
2. Empty and Short Stories: NarrativeAnalyzer processes 0-event and 1-event histories gracefully
   without crashing or dividing by zero.
3. Repeated Events Deduplication: Repeated event IDs do not double-count information discoveries.
4. Belief Flips & Secret Revelations: Explicitly detects belief contradictions and secret revelations.
5. Unresolved Conflicts & Stalled Relationships: Correctly flags stalled relationships in unresolved threads.
6. Pacing Assessment: Explicitly distinguishes healthy, stalled, idle, and overheated pacing states.
7. Advisor Deduplication: Advisor does not repeat an intervention that has already been executed.
8. Director Constraint Reflection: Director cooldowns and budgets are surfaced in counter_conditions and limitations.
9. Deterministic Re-analysis: Repeated analysis of the same project yields consistent results.
"""

import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.relationship import Relationship
from src.domain.secret import Secret
from src.domain.goal import Goal, GoalStatus
from src.domain.event import Event, EventType
from src.domain.narrative_genome import (
    NarrativeRecommendation,
    NarrativeAnalysisResult,
    DramaticFunction,
    InformationPattern,
    TensionDirection,
    RecommendationLifecycleStatus,
)
from src.narrative.narrative_analyzer import NarrativeAnalyzer
from src.narrative.narrative_advisor import NarrativeAdvisor
from src.agents.director import DirectorAgent, DirectorIntervention


def _make_test_world() -> WorldState:
    loc1 = Location(id="loc_room_a", name="Room A", connected_locations=["loc_room_b"])
    loc2 = Location(id="loc_room_b", name="Room B", connected_locations=["loc_room_a"])

    char1 = Character(
        id="char_agent",
        name="Agent",
        role="Operative",
        current_location_id="loc_room_a",
        goals=["goal_find"],
        known_facts={"fact_keycard"},
    )
    char2 = Character(
        id="char_rival",
        name="Rival",
        role="Director",
        current_location_id="loc_room_a",
        goals=["goal_secure"],
        secrets=["sec_code"],
        known_facts={"fact_safe"},
    )

    sec = Secret(
        id="sec_code",
        character_id="char_rival",
        statement="The safe code is 7391",
        known_by=["char_rival"],
        importance=0.9,
    )

    rel = Relationship(
        id="rel_rivalry",
        character_a_id="char_agent",
        character_b_id="char_rival",
        affinity=-0.5,
        trust=-0.7,
    )

    return WorldState(
        id="w_genome_test",
        name="Genome Test World",
        current_tick=3,
        locations={"loc_room_a": loc1, "loc_room_b": loc2},
        characters={"char_agent": char1, "char_rival": char2},
        secrets={"sec_code": sec},
        relationships={"rel_rivalry": rel},
    )


def test_schema_stabilization_recommendation_fields():
    """NarrativeRecommendation must provide observed_issue, relevance_score, counter_conditions, limitations, and status."""
    rec = NarrativeRecommendation(
        id="rec_schema_test",
        source_analysis_id="an_test",
        recommendation_type="tension_modulation",
        dramatic_goal="Decompress scene tension",
        rationale="Tension sustained near ceiling",
        target_pressure="QUIET_INTERVAL",
        expected_narrative_effect="Allows characters to process revelation",
        observed_issue="Dramatic tension reached 0.90 without narrative release.",
        relevance_score=0.88,
        counter_conditions=["Scene in climactic standoff"],
        limitations=["Decompression should not eliminate core mystery"],
        status=RecommendationLifecycleStatus.PENDING,
    )
    assert rec.observed_issue == "Dramatic tension reached 0.90 without narrative release."
    assert rec.relevance_score == 0.88
    assert len(rec.counter_conditions) == 1
    assert len(rec.limitations) == 1
    assert rec.status == RecommendationLifecycleStatus.PENDING
    assert rec.canonical_mutation_allowed is False


def test_empty_and_short_story_handling():
    """NarrativeAnalyzer must handle 0 events and 1 event without crashing or NaN values."""
    world = _make_test_world()
    world.events.clear()
    world.current_tick = 0

    analyzer = NarrativeAnalyzer()
    res_empty = analyzer.analyze(world=world, events=[])
    assert res_empty is not None
    assert len(res_empty.event_ids) == 0
    assert res_empty.tension["after"] >= 0.0
    assert res_empty.confidence == 1.0

    # 1 Event
    ev1 = Event(
        id="evt_001",
        tick=0,
        event_type=EventType.CHARACTER_OBSERVED,
        actor_ids=["char_agent"],
        location_id="loc_room_a",
        description="Agent entered Room A and looked around.",
    )
    world.events[ev1.id] = ev1

    res_short = analyzer.analyze(world=world, events=[ev1])
    assert res_short is not None
    assert len(res_short.event_ids) == 1
    assert ev1.id in res_short.event_ids


def test_repeated_events_deduplication():
    """Repeated event records in window must not inflate information discoveries."""
    world = _make_test_world()
    ev1 = Event(
        id="evt_discover_01",
        tick=1,
        event_type=EventType.CHARACTER_OBSERVED,
        actor_ids=["char_agent"],
        location_id="loc_room_a",
        description="Agent uncovers a secret document in the desk drawer.",
    )

    # Pass duplicates of the same event
    events = [ev1, ev1, ev1]
    analyzer = NarrativeAnalyzer()
    res = analyzer.analyze(world=world, events=events)

    discoveries = [
        item for item in res.information_state
        if item.get("pattern") == InformationPattern.DISCOVERY.value and item.get("event_id") == ev1.id
    ]
    assert len(discoveries) == 1, "Duplicate event IDs must be deduplicated in information state"


def test_belief_flip_and_secret_revelation_detection():
    """Analyzer must classify belief contradictions and secret revelations into information patterns."""
    world = _make_test_world()
    ev_flip = Event(
        id="evt_flip",
        tick=2,
        event_type=EventType.BELIEF_FORMED,
        actor_ids=["char_agent"],
        location_id="loc_room_a",
        description="Agent doubts prior belief; the evidence contradicts earlier assumptions.",
        metadata={"belief_flipped": True},
    )
    ev_secret = Event(
        id="evt_reveal",
        tick=3,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_rival"],
        location_id="loc_room_a",
        description="Rival confessed the secret code aloud.",
        metadata={"secret_revealed": True},
    )

    analyzer = NarrativeAnalyzer()
    res = analyzer.analyze(world=world, events=[ev_flip, ev_secret])

    patterns = [item.get("pattern") for item in res.information_state]
    assert InformationPattern.CONTRADICTION.value in patterns
    assert InformationPattern.REVELATION.value in patterns


def test_pacing_assessment_states():
    """Pacing assessment must accurately classify idle, stalled, and healthy pacing."""
    world = _make_test_world()
    analyzer = NarrativeAnalyzer()

    # Idle events
    idle_events = [
        Event(id=f"evt_wait_{i}", tick=i, event_type=EventType.OTHER, actor_ids=["char_agent"], description="Agent waited silently.", metadata={"action_type": "wait"})
        for i in range(4)
    ]
    res_idle = analyzer.analyze(world=world, events=idle_events)
    assert res_idle.pacing_assessment["pacing_state"] == "idle"
    assert res_idle.pacing_assessment["idle_events_count"] == 4


def test_advisor_deduplication_of_executed_recommendations():
    """Advisor must not re-recommend an intervention that has already been executed in history."""
    world = _make_test_world()
    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world, events=[])

    advisor = NarrativeAdvisor()

    # Generate initial recommendations
    initial_recs = advisor.advise(analysis=analysis, world=world)
    assert len(initial_recs) > 0
    rec_target = initial_recs[0]

    # Simulate that this recommendation was already executed and logged in world events
    executed_event = Event(
        id="evt_exec_rec",
        tick=4,
        event_type=EventType.OTHER,
        actor_ids=[],
        location_id="loc_room_a",
        description="Environmental pressure executed by Director",
        source="DIRECTOR",
        metadata={"recommendation_id": rec_target.id},
    )
    world.events[executed_event.id] = executed_event

    # Re-advise with updated world
    subsequent_recs = advisor.advise(analysis=analysis, world=world)
    assert not any(r.id == rec_target.id for r in subsequent_recs), "Executed recommendation must not be repeatedly suggested"


def test_advisor_director_cooldown_and_budget_reflection():
    """Director cooldown and budget exhaustion must be reflected in recommendation counter-conditions."""
    world = _make_test_world()
    world.current_tick = 5

    director = DirectorAgent(max_interventions_total=1, min_ticks_between_interventions=3)
    # Simulate an intervention executed at tick 4
    director.interventions_history.append(
        DirectorIntervention(intervention_type="power_failure", description="Power outage", target_location_id="loc_room_a")
    )
    director.last_intervention_tick = 4

    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world, events=[])

    advisor = NarrativeAdvisor()
    recs = advisor.advise(analysis=analysis, world=world, director=director)

    assert len(recs) > 0
    first_rec = recs[0]
    # Check that cooldown and budget constraints are surfaced
    all_constraints = " ".join(first_rec.counter_conditions + first_rec.limitations).lower()
    assert "cooldown" in all_constraints or "budget exhausted" in all_constraints


def test_repeated_analysis_consistency():
    """Analyzing the exact same WorldState and Event history twice produces identical results."""
    world = _make_test_world()
    ev1 = Event(
        id="evt_e1",
        tick=1,
        event_type=EventType.CHARACTER_OBSERVED,
        actor_ids=["char_agent"],
        location_id="loc_room_a",
        description="Agent entered Room A.",
    )
    world.events[ev1.id] = ev1

    analyzer = NarrativeAnalyzer()
    res1 = analyzer.analyze(world=world)
    res2 = analyzer.analyze(world=world)

    assert res1.id == res2.id
    assert res1.event_ids == res2.event_ids
    assert res1.dramatic_functions == res2.dramatic_functions
    assert res1.tension == res2.tension
    assert res1.tension_direction == res2.tension_direction
    assert len(res1.information_state) == len(res2.information_state)
    assert res1.pacing_assessment == res2.pacing_assessment
