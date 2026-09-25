"""Comprehensive verification tests for Phase F: Dramatic Signal Integration.

Covers all core requirements for Phase F:
1. Signal Extraction:
   - Unresolved high-intensity ConflictEdges
   - Stalled and threshold-crossing relationship dimensions
   - Significant archetype / arc movement
   - Analytical dramatic_need opportunities (thematic challenge suggestion, never Goal projection)
   - Secret revelations and belief flips
2. Director Integration (Sovereignty & World Pressure Only):
   - Injects world-level circumstances (deadlines, obstacles, clues)
   - NEVER creates character ActionProposals, dialogue, or speech
   - NEVER mutates character internal state directly
   - Passes through ActionValidator
   - Respects budget and cooldown limits
3. Sufficiency Gate Integration:
   - Conflict escalation and relationship threshold recognition
   - Intentional unresolved tension (cliffhanger/open thread) supported as valid PROCEED
   - Recommends ADJUST_PRESSURE_AND_CONTINUE when drama is escalating and budget allows
   - Does NOT require every conflict to be resolved
4. Observer Integration:
   - EventSalience boosts for relationship threshold crossing, secret revelation, conflict escalation, archetype shift
   - Explainable signal contributions recorded
   - Read-only integrity: EventHistory and WorldState never mutated
5. Integration & Sovereignty:
   - High-conflict scenario run end-to-end without forced confrontation
   - Characters decide autonomously via DecisionPolicy
   - Deterministic provider-off verification
"""

import pytest
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
    Motivation,
    KnowledgeItem,
    Proposition,
    Event,
    EventType,
    Relationship,
    CharacterDynamicsProfile,
    ArchetypeType,
)
from src.narrative.conflict_engine import ConflictEngine, ConflictEdge, ConflictDimension
from src.narrative.dramatic_signals import (
    extract_dramatic_signals,
    get_unresolved_conflicts,
    get_relationship_threshold_crossings,
    get_stalled_relationships,
    get_archetype_movements,
    get_dramatic_need_opportunities,
    detect_secret_revelations,
    detect_belief_flips,
    DramaticSignalsReport,
)
from src.agents.director import DirectorAgent, DirectorIntervention, DirectorInterventionType
from src.simulation.actions import ActionValidator
from src.simulation.recorder import EventRecorder
from src.simulation.orchestrator import SimulationOrchestrator
from src.narrative.sufficiency_gate import NarrativeSufficiencyGate
from src.narrative.observer import Observer, EventSalience
from src.story.models import (
    StoryBlueprint,
    BeatPressure,
    DramaticFunction,
    PredicateSpec,
    PredicateClause,
    StructureSelection,
    SufficiencyReport,
)


@pytest.fixture
def dramatic_world() -> WorldState:
    """Fixture providing a rich scenario with 2 characters in high conflict."""
    world = create_demo_world()

    # Enhance characters with Phase B dynamics and Phase C archetypes
    char_arjun = world.characters["char_arjun"]
    char_arjun.dynamics = CharacterDynamicsProfile(
        core_value="justice",
        shadow_value="obsession",
        conscious_want="Recover the stolen ledger",
        dramatic_need="Acknowledge personal culpability and learn to trust allies.",
        primary_archetype=ArchetypeType.HERO,
    )

    char_maya = world.characters["char_maya"]
    char_maya.dynamics = CharacterDynamicsProfile(
        core_value="truth",
        shadow_value="secrecy",
        conscious_want="Expose corporate conspiracy",
        dramatic_need="Recognize when a cause is worth risking personal safety for.",
        primary_archetype=ArchetypeType.OUTLAW,
    )

    # Update existing relationship with multidimensional tension
    rel = Relationship(
        id="rel_001",
        character_a_id="char_arjun",
        character_b_id="char_maya",
        affinity=-0.4,
        trust=-0.6,
        suspicion=0.8,
        resentment=0.5,
        respect=0.4,
        dimension_provenance={"trust": "evt_init"},
    )
    world.relationships["rel_001"] = rel

    return world


# =============================================================================
# 1. Dramatic Signal Extractors
# =============================================================================

def test_signal_extractor_unresolved_conflicts(dramatic_world):
    """Test pure detection of unresolved high-intensity conflicts."""
    report = extract_dramatic_signals(dramatic_world)
    assert isinstance(report, DramaticSignalsReport)
    assert len(report.unresolved_conflicts) > 0
    top = report.unresolved_conflicts[0]
    assert top.aggregate_intensity >= 0.5
    assert {top.source_character_id, top.target_character_id} == {"char_arjun", "char_maya"}


def test_signal_extractor_relationship_thresholds(dramatic_world):
    """Test detection of multidimensional threshold crossings."""
    thresholds = get_relationship_threshold_crossings(dramatic_world)
    assert len(thresholds) >= 1
    dims = {t["dimension"] for t in thresholds}
    # trust is -0.6, suspicion is 0.8, resentment is 0.5
    assert "trust" in dims or "suspicion" in dims


def test_signal_extractor_stalled_relationships(dramatic_world):
    """Test detection of co-located characters with high latent suspicion/resentment."""
    # Place both in room307
    dramatic_world.characters["char_arjun"].current_location_id = "loc_room307"
    dramatic_world.characters["char_maya"].current_location_id = "loc_room307"

    stalled = get_stalled_relationships(dramatic_world)
    assert len(stalled) >= 1
    assert stalled[0]["character_a_id"] in ("char_arjun", "char_maya")
    assert stalled[0]["severity"] >= 0.5


def test_signal_extractor_dramatic_need_opportunities(dramatic_world):
    """Test analytical extraction of dramatic need thematic opportunities.

    CRITICAL: dramatic_need must NEVER be projected to a character Goal.
    """
    opportunities = get_dramatic_need_opportunities(dramatic_world)
    assert len(opportunities) >= 2
    arjun_opp = next(o for o in opportunities if o["character_id"] == "char_arjun")
    assert "culpability" in arjun_opp["dramatic_need"] or "trust" in arjun_opp["dramatic_need"]
    assert arjun_opp["suggested_pressure"] in ("REVEAL_CLUE", "INTRODUCE_OBSTACLE")

    # Invariant: Goal list for Arjun is unchanged
    assert len(dramatic_world.characters["char_arjun"].goals) == 1
    goal = dramatic_world.goals[dramatic_world.characters["char_arjun"].goals[0]]
    assert "culpability" not in goal.description.lower()


def test_signal_extractor_secret_revelation(dramatic_world):
    """Test detection of revealed secrets via known_by or events."""
    # Initially Maya's secret is private
    secret = dramatic_world.secrets.get("sec_001") or next(iter(dramatic_world.secrets.values()))
    secret.known_by = ["char_arjun"]  # Arjun found out

    revs = detect_secret_revelations(dramatic_world)
    assert len(revs) >= 1
    assert any("char_arjun" in r.get("revealed_to", []) for r in revs)


def test_signal_extractor_belief_flips(dramatic_world):
    """Test detection of belief confidence inversion from event stream."""
    flip_event = Event(
        id="ev_flip_1",
        tick=3,
        event_type=EventType.BELIEF_FORMED,
        actor_ids=["char_arjun"],
        location_id="loc_room307",
        description="Arjun now believes Maya was framed.",
        metadata={"belief_flip": True, "old_confidence": 0.9, "new_confidence": 0.1},
    )
    dramatic_world.events[flip_event.id] = flip_event

    flips = detect_belief_flips(dramatic_world, events=[flip_event])
    assert len(flips) == 1
    assert flips[0]["character_id"] == "char_arjun"


# =============================================================================
# 2. Director Integration (Environmental Pressure & Sovereignty)
# =============================================================================

def test_director_injects_world_level_pressure_only(dramatic_world):
    """Test Director injects external environmental circumstances, NEVER character dialogue."""
    director = DirectorAgent(min_ticks_between_interventions=1)
    validator = ActionValidator()
    recorder = EventRecorder(dramatic_world)

    # Set both characters in room307 at tick 3
    dramatic_world.current_tick = 3
    dramatic_world.characters["char_arjun"].current_location_id = "loc_room307"
    dramatic_world.characters["char_maya"].current_location_id = "loc_room307"

    # Evaluate dramatic pressure with stagnation
    interv = director.evaluate_dramatic_pressure(
        dramatic_world,
        inactivity_count=1,
    )
    assert interv is not None
    assert interv.intervention_type in (
        DirectorInterventionType.ANNOUNCE_DEADLINE,
        DirectorInterventionType.INTRODUCE_OBSTACLE,
        DirectorInterventionType.TIME_PRESSURE,
        DirectorInterventionType.REVEAL_CLUE,
    )
    assert "lockdown" in interv.description or "door" in interv.description or "security" in interv.description

    # Inject and verify event invariants
    evt = director.inject_intervention(dramatic_world, recorder, interv, validator=validator)
    assert evt is not None
    assert evt.source == "DIRECTOR"
    assert evt.actor_ids == []  # Crucial: NO character is the actor of Director intervention
    assert evt.metadata.get("trigger_signal") == "unresolved_conflict"


def test_director_cannot_create_dialogue_or_force_character_proposals(dramatic_world):
    """Test ActionValidator strictly rejects any Director proposal that attempts speech or character puppeteering."""
    validator = ActionValidator()

    # Director attempts to speak through a proposal
    invalid_speech = ActionProposal(
        id="prop_dir_dialogue",
        actor_id="DIRECTOR",
        action_type=ActionType.SPEAK,
        target_id="char_maya",
        location_id="loc_room307",
        tick_proposed=1,
        motivation=Motivation(kind="PURSUE_GOAL", goal_id="pacing"),
        parameters={"statement": "You stole the ledger!"},
        reason="Forced confrontation",
    )
    valid, err, gate = validator.validate_proposal(dramatic_world, invalid_speech)
    assert not valid
    assert "cannot perform speech actions or force dialogue" in (err or "")

    # Director cannot set an actor_id to an existing character
    puppet_proposal = ActionProposal(
        id="prop_puppet",
        actor_id="char_arjun",
        action_type=ActionType.SPEAK,
        target_id="char_maya",
        location_id="loc_room307",
        tick_proposed=1,
        motivation=Motivation(kind="PURSUE_GOAL", goal_id="pacing"),
        parameters={"statement": "I confess everything."},
        reason="Director forced confession",
    )
    # Even if Director constructs this, Director's inject_intervention always creates proposals with actor_id='DIRECTOR'
    director = DirectorAgent()
    director_prop = director.create_action_proposal(
        DirectorIntervention(intervention_type=DirectorInterventionType.ANNOUNCE_DEADLINE, description="Deadline announced"),
        dramatic_world,
    )
    assert director_prop.actor_id == "DIRECTOR"


def test_director_respects_cooldown_and_budget(dramatic_world):
    """Test Director enforces max interventions and pacing spacing."""
    director = DirectorAgent(max_interventions_total=2, min_ticks_between_interventions=3)
    recorder = EventRecorder(dramatic_world)

    dramatic_world.current_tick = 3
    interv1 = DirectorIntervention(intervention_type=DirectorInterventionType.TIME_PRESSURE, description="Footsteps outside")
    evt1 = director.inject_intervention(dramatic_world, recorder, interv1)
    assert evt1 is not None

    # Next tick (tick 4): cooldown violation
    dramatic_world.current_tick = 4
    interv2 = DirectorIntervention(intervention_type=DirectorInterventionType.TIME_PRESSURE, description="Footsteps closer")
    evt2 = director.inject_intervention(dramatic_world, recorder, interv2)
    assert evt2 is None

    # Tick 6: cooldown satisfied
    dramatic_world.current_tick = 6
    evt3 = director.inject_intervention(dramatic_world, recorder, interv2)
    assert evt3 is not None

    # Tick 9: budget limit reached (2/2)
    dramatic_world.current_tick = 9
    evt4 = director.inject_intervention(dramatic_world, recorder, interv2)
    assert evt4 is None


# =============================================================================
# 3. Sufficiency Gate Integration
# =============================================================================

def test_sufficiency_gate_incorporates_dramatic_signals(dramatic_world):
    """Test Sufficiency Gate returns enriched reports with conflict and threshold signals."""
    gate = NarrativeSufficiencyGate()

    blueprint = StoryBlueprint(
        structure=StructureSelection(primary_macro="three_act"),
        beats=[
            BeatPressure(
                beat_id="beat_climax",
                dramatic_function=DramaticFunction.CLIMAX,
                target_window=(0.5, 0.9),
                satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="char_arjun")]),
                status="SATISFIED",
                required=True,
            )
        ],
    )

    report = gate.evaluate(
        blueprint=blueprint,
        world=dramatic_world,
        current_tick=8,
        current_budget_ticks=10,
        hard_cap_ticks=20,
    )

    assert isinstance(report, SufficiencyReport)
    assert report.recommendation == "PROCEED"
    assert report.required_beats_satisfied is True
    assert report.climax_detected is True
    assert report.has_unresolved_tension is True
    assert "cliffhanger" in report.reason or "unresolved" in report.reason
    assert report.relationship_threshold_crossed is True


def test_sufficiency_gate_adjust_pressure_when_drama_escalating(dramatic_world):
    """Test Sufficiency Gate recommends ADJUST_PRESSURE_AND_CONTINUE when conflict is escalating and budget can expand."""
    gate = NarrativeSufficiencyGate(extension_increment_ticks=5)

    blueprint = StoryBlueprint(
        structure=StructureSelection(primary_macro="three_act"),
        beats=[
            BeatPressure(
                beat_id="beat_confront",
                dramatic_function=DramaticFunction.CONFRONTATION,
                target_window=(0.4, 0.8),
                satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="char_arjun")]),
                status="PENDING",
                required=True,
            )
        ],
    )

    # Current budget reached at tick 10, but hard cap is 25
    report = gate.evaluate(
        blueprint=blueprint,
        world=dramatic_world,
        current_tick=10,
        current_budget_ticks=10,
        hard_cap_ticks=25,
    )

    assert report.recommendation == "ADJUST_PRESSURE_AND_CONTINUE"
    assert "Extending tick budget" in report.reason
    assert report.relationship_threshold_crossed is True


def test_sufficiency_gate_does_not_require_full_conflict_resolution(dramatic_world):
    """Test Sufficiency Gate does NOT fail a scene just because high-intensity conflict remains unresolved (cliffhangers are valid)."""
    gate = NarrativeSufficiencyGate()

    blueprint = StoryBlueprint(
        structure=StructureSelection(primary_macro="three_act"),
        beats=[
            BeatPressure(
                beat_id="beat_resolution",
                dramatic_function=DramaticFunction.RESOLUTION,
                target_window=(0.8, 1.0),
                satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="char_arjun")]),
                status="SATISFIED",
                required=True,
            ),
            BeatPressure(
                beat_id="beat_climax",
                dramatic_function=DramaticFunction.CLIMAX,
                target_window=(0.6, 0.8),
                satisfaction_predicate=PredicateSpec(any_of=[PredicateClause(type="GOAL_ADOPTED", character="char_arjun")]),
                status="SATISFIED",
                required=True,
            )
        ],
    )

    # High unresolved tension exists
    signals = extract_dramatic_signals(dramatic_world)
    assert signals.unresolved_tension_level > 0.0

    report = gate.evaluate(
        blueprint=blueprint,
        world=dramatic_world,
        current_tick=10,
        current_budget_ticks=10,
        hard_cap_ticks=20,
    )

    assert report.recommendation == "PROCEED"
    assert report.has_unresolved_tension is True


# =============================================================================
# 4. Observer Integration
# =============================================================================

def test_observer_salience_boost_for_relationship_threshold_crossing(dramatic_world):
    """Test Observer provides explainable salience boost for relationship threshold crossing."""
    observer = Observer()

    rel_event = Event(
        id="ev_rel_cross",
        tick=4,
        event_type=EventType.RELATIONSHIP_CHANGED,
        actor_ids=["char_arjun", "char_maya"],
        location_id="loc_room307",
        description="Arjun turns cold, his trust in Maya shattered.",
        metadata={"threshold_crossing": True, "dimension": "trust", "new_value": -0.8},
    )

    salience = observer.score_event_salience(rel_event, world=dramatic_world)
    assert salience.score >= 0.65
    assert salience.signals["relationship_threshold_bonus"] == 0.25


def test_observer_salience_boost_for_secret_revelation(dramatic_world):
    """Test Observer provides explainable salience boost for secret revelation."""
    observer = Observer()

    secret_event = Event(
        id="ev_sec_rev",
        tick=5,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_maya", "char_arjun"],
        location_id="loc_room307",
        description="Maya reveals the secret ledger to Arjun.",
        metadata={"secret_revealed": True, "speech_act": "reveal"},
    )

    salience = observer.score_event_salience(secret_event, world=dramatic_world)
    assert salience.score >= 0.70
    assert salience.signals["secret_revelation_bonus"] == 0.30


def test_observer_salience_boost_for_conflict_escalation(dramatic_world):
    """Test Observer provides explainable boost for major confrontation/conflict escalation."""
    observer = Observer()

    confront_event = Event(
        id="ev_confront_esc",
        tick=6,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_arjun", "char_maya"],
        location_id="loc_room307",
        description="Arjun confronts Maya and demands she surrender the files.",
        metadata={"conflict_escalation": True},
    )

    salience = observer.score_event_salience(confront_event, world=dramatic_world)
    assert salience.score >= 0.80
    assert salience.signals["conflict_escalation_bonus"] == 0.25


def test_observer_read_only_invariant(dramatic_world):
    """Test Observer never mutates WorldState or Event history."""
    observer = Observer()
    event_list = list(dramatic_world.events.values())

    initial_world_dict = dramatic_world.model_dump(mode="json")
    _ = observer.score_all_events(event_list, world=dramatic_world)
    _ = observer.observe_events(event_list, world=dramatic_world)

    assert dramatic_world.model_dump(mode="json") == initial_world_dict


# =============================================================================
# 5. Full Autonomous Simulation & Sovereignty Integration
# =============================================================================

def test_autonomous_simulation_with_conflict_and_director_pressure(dramatic_world):
    """Test end-to-end autonomous simulation where Director applies bounded pressure and actors decide autonomously."""
    director = DirectorAgent(min_ticks_between_interventions=2, max_interventions_total=3)
    orchestrator = SimulationOrchestrator(
        world=dramatic_world,
        director=director,
        seed=42,
    )

    results = orchestrator.run(max_ticks=8)
    assert len(results) >= 4
    assert dramatic_world.current_tick >= 8

    events = list(dramatic_world.events.values())

    # Verify: Any Director event has source='DIRECTOR' and actor_ids=[]
    director_events = [e for e in events if e.source == "DIRECTOR"]
    for de in director_events:
        assert de.actor_ids == []

    # Verify: All character events have source='SIMULATION'
    actor_events = [e for e in events if len(e.actor_ids) > 0]
    for ae in actor_events:
        assert ae.source == "SIMULATION"

    # Verify: Characters acted autonomously via simulation events, not director forcing
    # Character actions come from actor proposals, never DIRECTOR
    for r in results:
        assert not r.proposal_id.startswith("prop_dir_")


def test_phase_f_api_endpoints():
    """Test the Phase F API endpoints for dramatic signals, director pressure, and sufficiency evaluation."""
    import tempfile
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)

        # Create project
        create_res = client.post(
            "/api/projects",
            json={
                "seed_prompt": "Two undercover operatives meet in a safehouse to uncover a leak.",
                "title": "The Safehouse Leak",
            },
        )
        assert create_res.status_code == 200
        pid = create_res.json()["id"]

        # Step 1 tick
        step_res = client.post(f"/api/projects/{pid}/step", json={"ticks": 1})
        assert step_res.status_code == 200

        # 1. GET /api/projects/{pid}/dramatic-signals
        sig_res = client.get(f"/api/projects/{pid}/dramatic-signals")
        assert sig_res.status_code == 200
        sig_data = sig_res.json()
        assert "unresolved_conflicts" in sig_data
        assert "unresolved_tension_level" in sig_data
        assert "threshold_relationships" in sig_data

        # 2. GET /api/projects/{pid}/director/pressure-signals
        dir_res = client.get(f"/api/projects/{pid}/director/pressure-signals")
        assert dir_res.status_code == 200
        dir_data = dir_res.json()
        assert "can_intervene" in dir_data
        assert "unresolved_tension_level" in dir_data

        # 3. GET /api/projects/{pid}/sufficiency/evaluation
        # Ensure blueprint exists
        bp_res = client.get(f"/api/projects/{pid}/blueprint")
        assert bp_res.status_code == 200

        suff_res = client.get(f"/api/projects/{pid}/sufficiency/evaluation")
        assert suff_res.status_code == 200
        assert "recommendation" in suff_res.json()
        assert "dramatic_signals" in suff_res.json()

