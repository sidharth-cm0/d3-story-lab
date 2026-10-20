"""Tests for Narrative Genome v0.1 in D3 Story Lab.

Verifies:
1. Genome schema validation (types, defaults, invariants)
2. Narrative analysis determinism (same EventLog + same WorldState -> identical result)
3. Event grounding (all analysis claims reference valid EventLog IDs)
4. No canonical mutation (running NarrativeAnalyzer or NarrativeAdvisor never mutates WorldState)
5. Recommendation sovereignty (canonical_mutation_allowed is strictly False)
6. Director boundary (Director translates recommendation to environmental pressure, never forces character actions)
7. Replay compatibility (deterministic replay preserved)
8. Provider-off compatibility (runs without external AI provider)
9. Legacy compatibility (existing disk projects load cleanly)
10. Explainability (provenance, matched_genome_ids, rationale, related_event_ids preserved)
"""

import copy
import json
import pytest
from pathlib import Path

from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.relationship import Relationship
from src.domain.secret import Secret
from src.domain.goal import Goal
from src.domain.event import Event, EventType
from src.domain.story_structure import DramaticFunction, StoryBlueprint, StoryStructureType
from src.domain.narrative_genome import (
    ConflictType,
    CausalRelation,
    TensionDirection,
    InformationPattern,
    ScenePurpose,
    SetupPayoffState,
    GenomeSourceType,
    GenomeProvenance,
    NarrativeGenomeRecord,
    NarrativeAnalysisResult,
    NarrativeRecommendation,
)
from src.narrative.genome_store import LocalJsonGenomeRepository
from src.narrative.narrative_analyzer import NarrativeAnalyzer
from src.narrative.narrative_advisor import NarrativeAdvisor
from src.agents.director import DirectorAgent, DirectorInterventionType
from src.simulation.orchestrator import SimulationOrchestrator
from src.simulation.recorder import EventRecorder
from src.simulation.actions import ActionValidator
from src.storage.project_store import ProjectStore


def _build_intrigue_world() -> WorldState:
    """Create a deterministic test world with secrets, relationships, and co-located characters."""
    loc_suite = Location(id="loc_suite_301", name="Executive Suite")
    loc_hall = Location(id="loc_corridor", name="North Corridor")
    loc_suite.connected_locations.append("loc_corridor")
    loc_hall.connected_locations.append("loc_suite_301")

    char_maya = Character(
        id="char_maya",
        name="Maya Lin",
        role="Investigative Reporter",
        current_location_id="loc_suite_301",
        emotional_state=EmotionalState(fear=0.3, anger=0.2, curiosity=0.8),
    )
    char_arjun = Character(
        id="char_arjun",
        name="Arjun Mehta",
        role="Corporate Whistleblower",
        current_location_id="loc_suite_301",
        emotional_state=EmotionalState(fear=0.6, anger=0.1, curiosity=0.4),
    )

    # Relationship with high suspicion and low trust
    rel_maya_arjun = Relationship(
        id="rel_maya_arjun",
        character_a_id="char_maya",
        character_b_id="char_arjun",
        trust=-0.5,
        suspicion=0.75,
        resentment=0.4,
    )

    # Secret held by Arjun concealed from Maya
    secret_ledger = Secret(
        id="sec_black_ledger",
        character_id="char_arjun",
        statement="The offshore shell company was authorized under Maya's editor's signature.",
        known_by=[],
        importance=0.9,
    )

    keycard = WorldObject(
        id="obj_keycard",
        name="Executive Keycard",
        description="An encrypted access card",
        location_id="loc_suite_301",
        portable=True,
    )

    goal_maya = Goal(
        id="goal_maya_evidence",
        character_id="char_maya",
        description="Secure proof of corporate conspiracy",
        priority=1.0,
        status="active",
    )

    world = WorldState(
        id="world_genome_test",
        name="Intrigue Suite Test World",
        current_tick=3,
        locations={"loc_suite_301": loc_suite, "loc_corridor": loc_hall},
        characters={"char_maya": char_maya, "char_arjun": char_arjun},
        objects={"obj_keycard": keycard},
        relationships={"rel_maya_arjun": rel_maya_arjun},
        secrets={"sec_black_ledger": secret_ledger},
        goals={"goal_maya_evidence": goal_maya},
    )

    # Populate canonical events
    e1 = Event(
        id="ev_001",
        tick=1,
        event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_maya"],
        location_id="loc_suite_301",
        description="Maya Lin arrives and inspects the executive suite.",
    )
    e2 = Event(
        id="ev_002",
        tick=2,
        event_type=EventType.OBJECT_PICKED_UP,
        actor_ids=["char_maya"],
        location_id="loc_suite_301",
        description="Maya Lin locates and picks up the Executive Keycard.",
        caused_by=["ev_001"],
        metadata={"object_id": "obj_keycard"},
    )
    e3 = Event(
        id="ev_003",
        tick=3,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_maya", "char_arjun"],
        location_id="loc_suite_301",
        description="Maya Lin confronts Arjun Mehta regarding missing financial files.",
        caused_by=["ev_002"],
        metadata={"speech_act": "confront"},
    )
    world.events = {e1.id: e1, e2.id: e2, e3.id: e3}
    return world


# ==============================================================================
# CATEGORY 1: Genome Schema Validation
# ==============================================================================

def test_genome_schema_validation():
    """Verify NarrativeGenomeRecord, Provenance, and Recommendation enforce typing and invariants."""
    repo = LocalJsonGenomeRepository()
    patterns = repo.list_patterns()
    assert len(patterns) >= 15, "Should have loaded at least 15 seed abstract genome patterns"

    ng1 = repo.get_pattern("NG-001")
    assert ng1 is not None
    assert ng1.id == "NG-001"
    assert ng1.dramatic_function == DramaticFunction.ESCALATION
    assert ConflictType.INTERPERSONAL in ng1.conflict_types
    assert ng1.tension_direction == TensionDirection.RISING
    assert ng1.provenance.source_type == GenomeSourceType.SYSTEM_AUTHORED

    # Verify immutability of NarrativeGenomeRecord
    with pytest.raises(Exception):
        ng1.id = "NG-MUTATED"  # frozen model


def test_recommendation_sovereignty_field_enforced():
    """Verify canonical_mutation_allowed is frozen False and cannot be set True."""
    rec = NarrativeRecommendation(
        id="rec_test_01",
        source_analysis_id="na_test_01",
        recommendation_type="opportunity_creation",
        dramatic_goal="Introduce time pressure",
        rationale="Pacing stagnant",
        target_pressure="ANNOUNCE_DEADLINE",
        relevant_character_ids=["char_maya"],
        related_event_ids=["ev_001"],
        matched_genome_ids=["NG-004"],
        expected_narrative_effect="Forces decisive action",
        priority=0.8,
        confidence=0.9,
        canonical_mutation_allowed=False,
    )
    assert rec.canonical_mutation_allowed is False

    # Attempting to construct with canonical_mutation_allowed=True must fail validation
    with pytest.raises(Exception):
        NarrativeRecommendation(
            id="rec_illegal",
            source_analysis_id="na_test_01",
            recommendation_type="forced_action",
            dramatic_goal="Illegal puppetry",
            rationale="Illegal",
            target_pressure="ILLEGAL",
            expected_narrative_effect="Breaks engine",
            canonical_mutation_allowed=True,  # Disallowed by Literal[False]
        )


# ==============================================================================
# CATEGORY 2: Narrative Analysis Determinism
# ==============================================================================

def test_narrative_analysis_determinism():
    """Same EventLog + same WorldState MUST yield identical NarrativeAnalysisResult."""
    world_a = _build_intrigue_world()
    world_b = _build_intrigue_world()

    analyzer = NarrativeAnalyzer()
    res_a = analyzer.analyze(world=world_a, events=list(world_a.events.values()))
    res_b = analyzer.analyze(world=world_b, events=list(world_b.events.values()))

    # Compare all deterministic fields
    assert res_a.event_ids == res_b.event_ids
    assert res_a.dramatic_functions == res_b.dramatic_functions
    assert res_a.tension == res_b.tension
    assert res_a.tension_direction == res_b.tension_direction
    assert res_a.active_conflicts == res_b.active_conflicts
    assert res_a.information_state == res_b.information_state
    assert res_a.setup_payoff_status == res_b.setup_payoff_status
    assert res_a.scene_purpose == res_b.scene_purpose
    assert res_a.pacing_assessment == res_b.pacing_assessment
    assert res_a.opportunities == res_b.opportunities


# ==============================================================================
# CATEGORY 3: Event Grounding
# ==============================================================================

def test_narrative_analysis_event_grounding():
    """All analysis event_ids and causal links must reference valid, existing EventLog IDs."""
    world = _build_intrigue_world()
    analyzer = NarrativeAnalyzer()
    res = analyzer.analyze(world=world, events=list(world.events.values()))

    existing_ids = set(world.events.keys())
    for eid in res.event_ids:
        assert eid in existing_ids, f"event_id '{eid}' must exist in world.events"

    for link in res.causal_chain:
        assert link["from_event_id"] in existing_ids
        assert link["to_event_id"] in existing_ids


# ==============================================================================
# CATEGORY 4: No Canonical Mutation
# ==============================================================================

def test_no_canonical_mutation_on_analysis_and_advisory():
    """Running NarrativeAnalyzer or NarrativeAdvisor must NOT mutate WorldState or EventLog."""
    world = _build_intrigue_world()

    # Deep snapshot before running analysis
    chars_before = {k: v.model_dump() for k, v in world.characters.items()}
    objs_before = {k: v.model_dump() for k, v in world.objects.items()}
    rels_before = {k: v.model_dump() for k, v in world.relationships.items()}
    secs_before = {k: v.model_dump() for k, v in world.secrets.items()}
    evts_before = {k: v.model_dump() for k, v in world.events.items()}
    tick_before = world.current_tick

    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world, events=list(world.events.values()))

    advisor = NarrativeAdvisor()
    recs = advisor.advise(analysis)

    # Verify zero mutations
    assert world.current_tick == tick_before
    assert {k: v.model_dump() for k, v in world.characters.items()} == chars_before
    assert {k: v.model_dump() for k, v in world.objects.items()} == objs_before
    assert {k: v.model_dump() for k, v in world.relationships.items()} == rels_before
    assert {k: v.model_dump() for k, v in world.secrets.items()} == secs_before
    assert {k: v.model_dump() for k, v in world.events.items()} == evts_before


# ==============================================================================
# CATEGORY 5: Recommendation Sovereignty
# ==============================================================================

def test_recommendation_sovereignty_cannot_force_actions():
    """Recommendations describe dramatic pressure, NOT character decisions or forced actions."""
    world = _build_intrigue_world()
    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world, events=list(world.events.values()))

    advisor = NarrativeAdvisor()
    recs = advisor.advise(analysis)
    assert len(recs) > 0

    forbidden_action_phrases = [
        "maya confesses", "arjun confesses", "maya attacks", "arjun attacks",
        "maya drops", "arjun steals", "maya discovers the secret"
    ]

    for rec in recs:
        assert rec.canonical_mutation_allowed is False
        assert rec.target_pressure in [
            "ANNOUNCE_DEADLINE", "REVEAL_CLUE", "INTRODUCE_OBSTACLE",
            "TIME_PRESSURE", "QUIET_INTERVAL", "PHONE_RING", "KNOCK_ON_DOOR"
        ]
        text = (rec.dramatic_goal + " " + rec.rationale).lower()
        for forbidden in forbidden_action_phrases:
            assert forbidden not in text, f"Puppetry phrase '{forbidden}' leaked into recommendation rationale!"


# ==============================================================================
# CATEGORY 6: Director Boundary
# ==============================================================================

def test_director_boundary_accepts_pressure_without_puppetry():
    """Director considers recommendation and creates environmental intervention validated by ActionValidator."""
    world = _build_intrigue_world()
    world.current_tick = 5  # past tick 2 initial quiet window

    rec = NarrativeRecommendation(
        id="rec_test_deadline",
        source_analysis_id="na_01",
        recommendation_type="pacing_acceleration",
        dramatic_goal="Introduce time pressure",
        rationale="Suspicion high and characters co-located",
        target_pressure="ANNOUNCE_DEADLINE",
        relevant_character_ids=["char_maya", "char_arjun"],
        related_event_ids=["ev_003"],
        matched_genome_ids=["NG-004"],
        expected_narrative_effect="Accelerates decision velocity",
        priority=0.9,
        confidence=1.0,
        canonical_mutation_allowed=False,
    )

    director = DirectorAgent()
    interv = director.consider_narrative_recommendation(world, rec)
    assert interv is not None
    assert interv.intervention_type == DirectorInterventionType.ANNOUNCE_DEADLINE
    assert interv.target_location_id == "loc_suite_301"

    # Inject intervention via standard validator path
    recorder = EventRecorder(world)
    validator = ActionValidator()
    event = director.inject_intervention(world, recorder, interv, validator=validator)
    assert event is not None
    assert event.source == "DIRECTOR"
    assert event.actor_ids == []  # No character puppetry: Director has no character actor
    assert "lockdown" in event.description.lower() or "deadline" in event.description.lower()

    # Cooldown check: immediate second intervention must be rejected by can_intervene
    interv2 = director.consider_narrative_recommendation(world, rec)
    assert interv2 is None, "Director must respect cooldown"


# ==============================================================================
# CATEGORY 7: Replay Compatibility
# ==============================================================================

def test_replay_compatibility_with_narrative_intelligence():
    """Running narrative intelligence in parallel must not affect simulation tick replay."""
    world_clean = _build_intrigue_world()
    orch_clean = SimulationOrchestrator(world=world_clean, seed=42)

    # Step simulation 2 ticks without narrative analyzer
    res_clean = []
    for _ in range(2):
        res_clean.extend(orch_clean.step())

    # Now step identical world with narrative analyzer invoked at each step
    world_analyzed = _build_intrigue_world()
    orch_analyzed = SimulationOrchestrator(world=world_analyzed, seed=42)
    analyzer = NarrativeAnalyzer()
    advisor = NarrativeAdvisor()

    res_analyzed = []
    for _ in range(2):
        res_analyzed.extend(orch_analyzed.step())
        # Invoke analyzer and advisor as pure observers
        analysis = analyzer.analyze(world=world_analyzed)
        _ = advisor.advise(analysis)

    # Must produce byte-identical results
    assert len(res_clean) == len(res_analyzed)
    for rc, ra in zip(res_clean, res_analyzed):
        assert rc.status == ra.status
        assert rc.events_created == ra.events_created

    events_clean = [e.description for e in world_clean.events.values()]
    events_analyzed = [e.description for e in world_analyzed.events.values()]
    assert events_clean == events_analyzed


# ==============================================================================
# CATEGORY 8: Provider-off Compatibility
# ==============================================================================

def test_provider_off_offline_narrative_intelligence():
    """Core Narrative Genome analysis must function completely offline without external AI."""
    world = _build_intrigue_world()
    analyzer = NarrativeAnalyzer()
    analysis = analyzer.analyze(world=world)

    assert analysis is not None
    assert len(analysis.dramatic_functions) > 0
    assert "after" in analysis.tension

    advisor = NarrativeAdvisor()
    recs = advisor.advise(analysis)
    assert isinstance(recs, list)
    for rec in recs:
        assert rec.confidence > 0.0
        assert len(rec.matched_genome_ids) > 0


# ==============================================================================
# CATEGORY 9: Legacy Compatibility
# ==============================================================================

def test_legacy_project_storage_compatibility():
    """ProjectData loads and saves cleanly with optional narrative genome fields."""
    store = ProjectStore()
    projects = store.list_projects()
    # If any saved project exists on disk, verify it loads without validation error
    if projects:
        proj_id = projects[0].id
        proj = store.load_project(proj_id)
        assert proj is not None
        # Defaults to None for legacy files
        assert proj.narrative_analysis is None or isinstance(proj.narrative_analysis, NarrativeAnalysisResult)


# ==============================================================================
# CATEGORY 10: API Endpoints & Observability
# ==============================================================================

def test_narrative_genome_api_endpoints():
    """Verify Narrative Genome API endpoints function end-to-end with FastAPI TestClient."""
    import tempfile
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)

        # 1. Patterns endpoint
        patterns_res = client.get("/api/narrative-genome/patterns")
        assert patterns_res.status_code == 200
        patterns = patterns_res.json()
        assert len(patterns) >= 15
        assert any(p["id"] == "NG-001" for p in patterns)

        # 2. Create and step project
        create_res = client.post(
            "/api/projects",
            json={
                "seed_prompt": "Undercover detective discovers hidden microchip in a vintage radio inside a repair workshop.",
                "title": "The Vintage Radio Intrigue",
            },
        )
        assert create_res.status_code == 200
        pid = create_res.json()["id"]

        client.post(f"/api/projects/{pid}/step", json={"ticks": 2})

        # 3. Narrative analysis endpoint
        analysis_res = client.get(f"/api/projects/{pid}/narrative-genome/analysis")
        assert analysis_res.status_code == 200
        analysis = analysis_res.json()
        assert "dramatic_functions" in analysis
        assert "tension" in analysis
        assert "pacing_assessment" in analysis

        # 4. Recommendations endpoint
        recs_res = client.get(f"/api/projects/{pid}/narrative-genome/recommendations")
        assert recs_res.status_code == 200
        recs = recs_res.json()
        assert isinstance(recs, list)
        for r in recs:
            assert r["canonical_mutation_allowed"] is False
            assert "dramatic_goal" in r
            assert "rationale" in r
            assert len(r["matched_genome_ids"]) > 0

        # 5. Director application endpoint
        apply_res = client.post(f"/api/projects/{pid}/director/apply-narrative-recommendation")
        assert apply_res.status_code == 200
        apply_data = apply_res.json()
        assert "applied" in apply_data

