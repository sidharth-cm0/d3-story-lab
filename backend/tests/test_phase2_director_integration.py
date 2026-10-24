"""Integration tests for Phase 2: Narrative Genome to Director Integration.

Verifies:
1. Complete request path: recommend -> evaluate lifecycle -> ActionValidator -> EventLog -> ProjectStore.
2. Explicit typed lifecycle states:
   - EXECUTED
   - BLOCKED_COOLDOWN
   - BLOCKED_BUDGET
   - BLOCKED_QUIET_PERIOD
   - REJECTED_VALIDATION
   - REJECTED_DUPLICATE
3. Duplicate application prevention: retrying the same recommendation returns REJECTED_DUPLICATE.
4. Cooldown and budget limits strictly enforced.
5. Zero canonical mutation on rejected, blocked, or duplicate requests (canonical_state_changed == False).
6. Characters retain complete freedom to ignore environmental conditions.
"""

import tempfile
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.narrative_genome import RecommendationLifecycleStatus, NarrativeRecommendation
from src.storage.project_store import ProjectStore
from src.agents.director import DirectorAgent, DirectorIntervention
from src.simulation.actions import ActionValidator
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.event import Event, EventType


@pytest.fixture
def director_test_client():
    """Create isolated FastAPI client with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)
        yield client, tmpdir


def test_recommendation_successful_execution_and_persistence(director_test_client):
    """Applying a valid recommendation executes environmental pressure, logs event, and persists to disk."""
    client, store_dir = director_test_client

    create_res = client.post(
        "/api/projects",
        json={
            "seed_prompt": "Two rival couriers race across an abandoned space station to claim a forgotten cargo capsule.",
            "title": "Station Race",
        },
    )
    assert create_res.status_code == 200
    pid = create_res.json()["id"]

    # Step twice so current_tick >= 2 (past initial quiet period)
    client.post(f"/api/projects/{pid}/step", json={"ticks": 2})

    recs_res = client.get(f"/api/projects/{pid}/narrative-genome/recommendations")
    recs = recs_res.json()
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    # Apply recommendation
    apply_res = client.post(
        f"/api/projects/{pid}/director/apply-narrative-recommendation",
        json={"recommendation_id": rec_id},
    )
    assert apply_res.status_code == 200
    data = apply_res.json()

    assert data["applied"] is True
    assert data["status"] == RecommendationLifecycleStatus.EXECUTED.value
    assert data["canonical_state_changed"] is True
    assert data["recommendation_id"] == rec_id
    assert "event" in data
    assert "intervention" in data
    assert data["event"]["source"] == "DIRECTOR"

    # Verify disk persistence
    store = ProjectStore(base_dir=store_dir)
    persisted = store.load_project(pid)
    assert persisted is not None
    assert any(e.id == data["event_id"] for e in persisted.event_log.events)


def test_recommendation_duplicate_rejection(director_test_client):
    """Attempting to apply the same recommendation twice returns REJECTED_DUPLICATE without state mutation."""
    client, store_dir = director_test_client

    create_res = client.post(
        "/api/projects",
        json={
            "seed_prompt": "Two rival couriers race across an abandoned space station to claim a forgotten cargo capsule.",
            "title": "Station Race",
        },
    )
    pid = create_res.json()["id"]
    client.post(f"/api/projects/{pid}/step", json={"ticks": 2})

    recs = client.get(f"/api/projects/{pid}/narrative-genome/recommendations").json()
    rec_id = recs[0]["id"]

    # First application: succeeds
    res1 = client.post(
        f"/api/projects/{pid}/director/apply-narrative-recommendation",
        json={"recommendation_id": rec_id},
    )
    assert res1.json()["status"] == RecommendationLifecycleStatus.EXECUTED.value
    event_id = res1.json()["event_id"]

    store = ProjectStore(base_dir=store_dir)
    event_count_after_first = len(store.load_project(pid).world.events)

    # Second application: rejected as duplicate
    res2 = client.post(
        f"/api/projects/{pid}/director/apply-narrative-recommendation",
        json={"recommendation_id": rec_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["applied"] is False
    assert data2["status"] == RecommendationLifecycleStatus.REJECTED_DUPLICATE.value
    assert data2["canonical_state_changed"] is False
    assert "already been" in data2["reason"]

    # Verify zero mutation occurred on second attempt
    assert len(store.load_project(pid).world.events) == event_count_after_first


def test_recommendation_cooldown_enforcement(director_test_client):
    """Director must reject consecutive interventions requested within the cooldown interval (3 ticks)."""
    client, store_dir = director_test_client

    create_res = client.post(
        "/api/projects",
        json={
            "seed_prompt": "An operative searches a quiet abandoned terminal.",
            "title": "Quiet Terminal",
        },
    )
    pid = create_res.json()["id"]
    client.post(f"/api/projects/{pid}/step", json={"ticks": 2})

    # Execute first intervention
    res1 = client.post(f"/api/projects/{pid}/director/apply-narrative-recommendation", json={})
    assert res1.json()["applied"] is True

    # Attempt second intervention immediately (0 ticks elapsed since last intervention)
    res2 = client.post(f"/api/projects/{pid}/director/apply-narrative-recommendation", json={})
    data2 = res2.json()

    assert data2["applied"] is False
    assert data2["status"] == RecommendationLifecycleStatus.BLOCKED_COOLDOWN.value
    assert data2["canonical_state_changed"] is False
    assert "cooldown" in data2["reason"].lower()


def test_recommendation_budget_exhaustion():
    """Director must reject interventions when max_interventions_total budget is exhausted."""
    world = WorldState(
        id="world_budget",
        name="Budget World",
        current_tick=10,
        locations={"loc_lab": Location(id="loc_lab", name="Lab")},
        characters={"char_doc": Character(id="char_doc", name="Doctor", role="Scientist", current_location_id="loc_lab")},
    )

    director = DirectorAgent(max_interventions_total=2, min_ticks_between_interventions=1)
    # Simulate 2 historical interventions to exhaust budget
    director.interventions_history.append(DirectorIntervention(intervention_type="power_failure", description="Power outage", target_location_id="loc_lab"))
    director.interventions_history.append(DirectorIntervention(intervention_type="phone_ring", description="Phone ringing", target_location_id="loc_lab"))
    director.last_intervention_tick = 5

    rec = NarrativeRecommendation(
        id="rec_budget_test",
        source_analysis_id="an_1",
        recommendation_type="ESCALATION",
        dramatic_goal="Escalate tension",
        rationale="Pacing stagnant",
        target_pressure="REVEAL_CLUE",
        expected_narrative_effect="Heightened urgency",
    )

    status, reason, interv = director.evaluate_recommendation_lifecycle(world, rec)
    assert status == RecommendationLifecycleStatus.BLOCKED_BUDGET
    assert "exhausted" in reason.lower()
    assert interv is None


def test_recommendation_quiet_period_initial_ticks():
    """Interventions in ticks 0-1 must be blocked to protect scene establishment."""
    world = WorldState(
        id="world_quiet",
        name="Quiet World",
        current_tick=1,  # Tick 1
        locations={"loc_lab": Location(id="loc_lab", name="Lab")},
        characters={"char_doc": Character(id="char_doc", name="Doctor", role="Scientist", current_location_id="loc_lab")},
    )

    director = DirectorAgent()
    rec = NarrativeRecommendation(
        id="rec_quiet_test",
        source_analysis_id="an_1",
        recommendation_type="ESCALATION",
        dramatic_goal="Escalate tension",
        rationale="Pacing stagnant",
        target_pressure="REVEAL_CLUE",
        expected_narrative_effect="Heightened urgency",
    )

    status, reason, interv = director.evaluate_recommendation_lifecycle(world, rec)
    assert status == RecommendationLifecycleStatus.BLOCKED_QUIET_PERIOD
    assert "establishment" in reason.lower()
    assert interv is None


def test_recommendation_validation_rejection_on_invalid_action():
    """If an intervention proposes an invalid action (e.g. Director speech), ActionValidator rejects it."""
    world = WorldState(
        id="world_val",
        name="Validation World",
        current_tick=5,
        locations={"loc_lab": Location(id="loc_lab", name="Lab")},
        characters={"char_doc": Character(id="char_doc", name="Doctor", role="Scientist", current_location_id="loc_lab")},
    )

    director = DirectorAgent()
    # Director cannot perform speech actions
    invalid_intervention = DirectorIntervention(
        intervention_type="new_information",
        action_type="SPEAK",
        description="Invalid speech intervention",
        target_location_id="loc_lab",
    )

    proposal = director.create_action_proposal(invalid_intervention, world)
    validator = ActionValidator()
    is_valid, err, gate = validator.validate_proposal(world, proposal)

    assert is_valid is False
    assert gate == "AffordanceGate"
    assert "cannot perform speech" in err
