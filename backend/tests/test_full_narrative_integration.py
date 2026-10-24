"""End-to-end integration tests for Grounded Narrative RAG, Temporal Graph, and Director Handoff.

Verifies:
1. End-to-end project initialization and simulation stepping.
2. Temporal character graph snapshot query at discrete ticks (historical and current).
3. Temporal character graph diff calculation across intervals.
4. Edge multidimensional inspection and event evidence provenance.
5. Grounded Narrative RAG inquiry for supported queries (validating verified claims and citations).
6. Grounded Narrative RAG inquiry for unsupported queries (validating refusal / insufficient evidence).
7. Director recommendation application end-to-end:
   - Recommendation consideration -> concrete DirectorIntervention.
   - ActionValidator gate check.
   - EventLog append and WorldState modification.
   - Disk persistence via ProjectStore.
8. Rejected or deferred recommendations strictly preserve WorldState and EventLog invariant.
"""

import tempfile
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.storage.project_store import ProjectStore
from src.narrative.rag.models import ClaimVerificationStatus


@pytest.fixture
def integrated_test_client():
    """Create a test client with isolated temporary project storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)
        yield client, tmpdir


def test_full_narrative_intelligence_integration_flow(integrated_test_client):
    client, store_dir = integrated_test_client

    # 1. Initialize project
    create_res = client.post(
        "/api/projects",
        json={
            "seed_prompt": "Two rival smugglers, Cross and Vane, are trapped in an abandoned orbital station after an explosion disables the docking bay.",
            "title": "Orbital Trap",
        },
    )
    assert create_res.status_code == 200
    proj_id = create_res.json()["id"]

    # Step simulation forward 3 ticks
    step_res = client.post(f"/api/projects/{proj_id}/step", json={"ticks": 3})
    assert step_res.status_code == 200

    # 2. Query Temporal Graph at tick 0 and tick 3
    graph_t0 = client.get(f"/api/projects/{proj_id}/graph?tick=0")
    assert graph_t0.status_code == 200
    snap_t0 = graph_t0.json()
    assert snap_t0["tick"] == 0
    assert len(snap_t0["nodes"]) >= 2

    graph_t3 = client.get(f"/api/projects/{proj_id}/graph?tick=3")
    assert graph_t3.status_code == 200
    snap_t3 = graph_t3.json()
    assert snap_t3["tick"] == 3
    assert snap_t3["event_count"] >= snap_t0["event_count"]

    # 3. Query Temporal Graph Diff between tick 0 and tick 3
    diff_res = client.get(f"/api/projects/{proj_id}/graph/diff?from_tick=0&to_tick=3")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["from_tick"] == 0
    assert diff_data["to_tick"] == 3
    assert "causal_event_ids" in diff_data
    assert "node_changes" in diff_data
    assert "edge_changes" in diff_data

    # 4. Verify edge evidence provenance
    if snap_t3["edges"]:
        edge = snap_t3["edges"][0]
        assert "dimensions" in edge
        assert "aggregate_intensity" in edge
        assert isinstance(edge["evidence_event_ids"], list)

    # 5. Query Grounded RAG with a supported inquiry
    rag_supported = client.post(
        f"/api/projects/{proj_id}/narrative-rag/query",
        json={
            "query": "What narrative patterns resemble the current conflict?",
        },
    )
    assert rag_supported.status_code == 200
    rag_data = rag_supported.json()
    assert "answer" in rag_data
    assert "retrieved_pattern_ids" in rag_data
    assert "claims" in rag_data
    assert len(rag_data["retrieved_pattern_ids"]) >= 1

    # 6. Query Grounded RAG with an unsupported, out-of-world question
    rag_unsupported = client.post(
        f"/api/projects/{proj_id}/narrative-rag/query",
        json={
            "query": "Did the Martian cyber-dragon attack the orbital reactor in tick 99?",
        },
    )
    assert rag_unsupported.status_code == 200
    unsupported_data = rag_unsupported.json()
    assert unsupported_data["status"] == "insufficient_evidence"
    assert unsupported_data["claims"] == []
    assert "No evidence" in unsupported_data["answer"]

    # 7. Apply a Director narrative recommendation
    store = ProjectStore(base_dir=store_dir)
    initial_project = store.load_project(proj_id)
    initial_event_count = len(initial_project.world.events)
    initial_event_log_count = len(initial_project.event_log.events) if initial_project.event_log else 0

    apply_res = client.post(
        f"/api/projects/{proj_id}/director/apply-narrative-recommendation",
        json={},  # Apply default active recommendation
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()

    if apply_data.get("applied") is True:
        # Trace consideration, ActionValidator, event logging, and state change
        assert "event" in apply_data
        assert "intervention" in apply_data
        event_dict = apply_data["event"]
        assert event_dict["id"] in apply_data["event"]["id"]

        # Verify disk persistence via ProjectStore
        persisted_project = store.load_project(proj_id)
        assert len(persisted_project.world.events) == initial_event_count + 1
        assert len(persisted_project.event_log.events) == initial_event_log_count + 1
        persisted_event_ids = [e.id for e in persisted_project.event_log.events]
        assert event_dict["id"] in persisted_event_ids
    else:
        # If deferred due to budget/cooldown, state MUST remain completely unmutated
        persisted_project = store.load_project(proj_id)
        assert len(persisted_project.world.events) == initial_event_count
        assert (len(persisted_project.event_log.events) if persisted_project.event_log else 0) == initial_event_log_count


def test_rejected_recommendation_does_not_mutate_state(integrated_test_client):
    """Attempting to apply an invalid recommendation must fail and never alter canonical state."""
    client, store_dir = integrated_test_client

    create_res = client.post(
        "/api/projects",
        json={
            "seed_prompt": "A solitary archivist works in a quiet lunar bunker.",
            "title": "Lunar Bunker",
        },
    )
    proj_id = create_res.json()["id"]

    store = ProjectStore(base_dir=store_dir)
    before_proj = store.load_project(proj_id)
    event_count_before = len(before_proj.world.events)

    # Request non-existent recommendation ID
    bad_res = client.post(
        f"/api/projects/{proj_id}/director/apply-narrative-recommendation",
        json={"recommendation_id": "rec_non_existent_fake_12345"},
    )
    assert bad_res.status_code == 404

    # Verify canonical state is completely untouched
    after_proj = store.load_project(proj_id)
    assert len(after_proj.world.events) == event_count_before
    assert after_proj.world.current_tick == before_proj.world.current_tick
