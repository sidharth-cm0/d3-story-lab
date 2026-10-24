"""Automated test suite for Grounded RAG in D3 Story Lab.

Tests:
1. Ingestion: validation, normalization, rejection of invalid/duplicate IDs, idempotency.
2. Retrieval: BM25 lexical scoring, metadata filtering, top-k limits, deterministic ordering.
3. Embeddings: deterministic local vector generation, cosine similarity, index versioning.
4. Grounding: EvidenceValidator checking existing vs fabricated IDs, claim verification.
5. Grounded Q&A: answering conflict, setup/payoff, environmental pressure, and belief queries.
6. Invariants: strict non-mutation of canonical WorldState and EventLog.
"""

import pytest
from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.secret import Secret
from src.domain.event import Event, EventType
from src.domain.conflict import ConflictGraph, ConflictEdge, ConflictDimension
from src.storage.project_store import ProjectData, ProjectMetadata
from src.narrative.rag.models import (
    EvidenceCategory,
    ClaimVerificationStatus,
    RAGAnswerStatus,
    NarrativeKnowledgeRecord,
    RAGSearchFilter,
    GroundedClaim,
    EvidenceReference,
)
from src.narrative.rag.ingestion import NarrativeKnowledgeIngester, IngestionError
from src.narrative.rag.retrieval import NarrativeRetriever, tokenize
from src.narrative.rag.embeddings import LocalFeatureEmbeddingProvider
from src.narrative.rag.grounding import EvidenceValidator, GroundedNarrativeEngine
from src.narrative.rag.service import NarrativeRAGService


def test_rag_ingestion_and_idempotency():
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()
    assert len(records) > 0
    first_count = len(records)

    # Ingesting same file again must be idempotent and not create duplicate IDs
    second_records = ingester.load_defaults()
    assert len(second_records) == first_count
    assert ingester.count() == first_count


def test_rag_ingestion_validation_rejects_malformed_records():
    ingester = NarrativeKnowledgeIngester()

    # Missing ID
    with pytest.raises(IngestionError, match="missing required string 'id'"):
        ingester.ingest_record({"name": "No ID Pattern", "description": "test", "dramatic_function": "SETUP"})

    # Missing title/name
    with pytest.raises(IngestionError, match="missing required string 'title' or 'name'"):
        ingester.ingest_record({"id": "BAD-01", "description": "test", "dramatic_function": "SETUP"})

    # Missing dramatic_function
    with pytest.raises(IngestionError, match="missing required 'dramatic_function'"):
        ingester.ingest_record({"id": "BAD-02", "name": "Test", "description": "test"})

    # Invalid confidence range
    with pytest.raises(IngestionError, match="confidence .* must be between 0.0 and 1.0"):
        ingester.ingest_record({
            "id": "BAD-03",
            "name": "Test",
            "description": "test",
            "dramatic_function": "SETUP",
            "confidence": 1.5,
        })


def test_bm25_lexical_retrieval_and_filtering():
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()
    retriever = NarrativeRetriever(records)

    # 1. Exact query keyword match
    results = retriever.search(RAGSearchFilter(query="concealed information secret", top_k=3, mode="lexical"))
    assert len(results) > 0
    top = results[0]
    assert "NG-001" in top.record.id or "conceal" in top.record.content.lower()
    assert top.score > 0.0

    # 2. Metadata filter by dramatic function
    rev_results = retriever.search(
        RAGSearchFilter(dramatic_functions=["REVELATION"], top_k=5, mode="lexical")
    )
    assert len(rev_results) > 0
    for r in rev_results:
        assert r.record.dramatic_function.upper() == "REVELATION"

    # 3. Filter by genre
    noir_results = retriever.search(
        RAGSearchFilter(genres=["noir"], top_k=5, mode="lexical")
    )
    assert len(noir_results) > 0
    for r in noir_results:
        assert "noir" in r.record.genre_tags or "all" in r.record.genre_tags

    # 4. Filter by conflict type
    info_results = retriever.search(
        RAGSearchFilter(conflict_types=["informational"], top_k=5, mode="lexical")
    )
    assert len(info_results) > 0
    for r in info_results:
        assert "informational" in r.record.conflict_types


def test_retrieval_deterministic_tie_breaking_and_threshold():
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()
    retriever = NarrativeRetriever(records)

    # Run query twice; ordering must be identical
    res1 = retriever.search(RAGSearchFilter(query="pressure deadline urgency", top_k=4))
    res2 = retriever.search(RAGSearchFilter(query="pressure deadline urgency", top_k=4))
    assert [r.record.id for r in res1] == [r.record.id for r in res2]

    # Extreme threshold returns empty list cleanly
    empty_res = retriever.search(RAGSearchFilter(query="random gibberish term xyz99", min_score=0.99))
    assert empty_res == []


def test_local_feature_embeddings():
    embedder = LocalFeatureEmbeddingProvider()
    assert embedder.is_available is True
    assert embedder.model_id == "d3-local-feature-128d"
    assert embedder.index_version == "v1-local-hash"

    vec1 = embedder.embed_text("A tense interrogation between two rival detectives in a warehouse.")
    vec2 = embedder.embed_text("A tense interrogation of a detective under pressure.")
    vec3 = embedder.embed_text("A tranquil garden with blooming cherry blossoms and calm waters.")

    assert len(vec1) == 128
    sim_close = embedder.cosine_similarity(vec1, vec2)
    sim_far = embedder.cosine_similarity(vec1, vec3)

    assert sim_close > sim_far
    # Self similarity is 1.0
    assert abs(embedder.cosine_similarity(vec1, vec1) - 1.0) < 1e-4


def test_evidence_validator_detects_fabricated_and_missing_ids():
    world = WorldState(
        id="w_test",
        name="Test Room",
        description="A room",
        locations={"loc_1": Location(id="loc_1", name="Room", description="A room", connected_locations=[])},
        characters={"char_alice": Character(id="char_alice", name="Alice", role="Detective", current_location_id="loc_1")},
        events={
            "evt_01": Event(
                id="evt_01",
                tick=1,
                event_type=EventType.OTHER,
                actor_ids=["char_alice"],
                location_id="loc_1",
                description="Alice found the key",
            )
        },
    )

    evidence_catalog = {
        "ev_ref_evt_01": EvidenceReference(
            id="ev_ref_evt_01",
            category=EvidenceCategory.CANONICAL_FACT,
            entity_type="event",
            entity_id="evt_01",
            tick=1,
            summary="Alice found the key",
        ),
        "ev_ref_fake": EvidenceReference(
            id="ev_ref_fake",
            category=EvidenceCategory.CANONICAL_FACT,
            entity_type="event",
            entity_id="evt_fabricated_999",
            tick=1,
            summary="Fabricated event",
        ),
    }

    # 1. Valid claim citing real event
    valid_claim = GroundedClaim(
        claim_id="c1",
        claim_text="Alice found the key in tick 1.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_ref_evt_01"],
    )
    res_valid = EvidenceValidator.verify_claim(valid_claim, world, evidence_catalog, {})
    assert res_valid.verification_status == ClaimVerificationStatus.VERIFIED

    # 2. Fabricated claim citing non-existent event ID
    fake_claim = GroundedClaim(
        claim_id="c2",
        claim_text="Alice escaped through the tunnel in tick 9.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_ref_fake"],
    )
    res_fake = EvidenceValidator.verify_claim(fake_claim, world, evidence_catalog, {})
    assert res_fake.verification_status == ClaimVerificationStatus.UNSUPPORTED
    assert "evt_fabricated_999" in (res_fake.verification_notes or "")

    # 3. Unsubstantiated claim with no cited evidence IDs
    empty_claim = GroundedClaim(
        claim_id="c3",
        claim_text="An event occurred without citation.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=[],
    )
    res_empty = EvidenceValidator.verify_claim(empty_claim, world, evidence_catalog, {})
    assert res_empty.verification_status == ClaimVerificationStatus.UNSUPPORTED


def test_evidence_validator_firewall_and_contradiction_auditing():
    """Verify evidence validator enforces strict firewall boundaries and detects contradictions."""
    world = WorldState(
        id="world_audit",
        name="Audit World",
        current_tick=5,
        locations={
            "loc_wh": Location(id="loc_wh", name="Warehouse", description="Warehouse"),
            "loc_dock": Location(id="loc_dock", name="Docks", description="Docks"),
        },
        characters={
            "char_alice": Character(
                id="char_alice",
                name="Alice",
                role="Infiltrator",
                current_location_id="loc_dock",
            ),
            "char_bob": Character(
                id="char_bob",
                name="Bob",
                role="Guard",
                current_location_id="loc_wh",
            ),
        },
        secrets={
            "sec_vault": Secret(id="sec_vault", character_id="char_alice", statement="Code is 4492"),
        },
        events={
            "evt_01": Event(
                id="evt_01",
                tick=1,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_alice"],
                location_id="loc_wh",
                description="Alice moved to Warehouse",
            ),
            "evt_02": Event(
                id="evt_02",
                tick=4,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_alice"],
                location_id="loc_dock",
                description="Alice moved from Warehouse to Docks",
            ),
            "evt_03": Event(
                id="evt_03",
                tick=2,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_bob"],
                location_id="loc_wh",
                description="Bob radioed dispatch",
            ),
        },
    )

    # Populate Alice's subjective knowledge
    world.characters["char_alice"].acquire_knowledge(
        proposition_id="prop_alarm_disabled",
        certainty=0.9,
        believed_truth_value=True,
    )
    # Populate Bob's subjective knowledge (different truth value)
    world.characters["char_bob"].acquire_knowledge(
        proposition_id="prop_alarm_disabled",
        certainty=1.0,
        believed_truth_value=False,
    )

    k_catalog = {
        "NG-001": NarrativeKnowledgeRecord(
            id="NG-001",
            title="Sudden Revelation",
            content="A hidden truth is abruptly discovered.",
            pattern_type="plot_turn",
            dramatic_function="REVELATION",
            conflict_types=["epistemic"],
            tension_direction="rising",
            genre_tags=["mystery"],
            source_type="curated_patterns",
            source_reference="Genome",
            license="MIT",
            provenance={"curator": "core"},
        )
    }

    evidence_catalog = {
        "ev_evt_01": EvidenceReference(
            id="ev_evt_01",
            category=EvidenceCategory.CANONICAL_FACT,
            entity_type="event",
            entity_id="evt_01",
            tick=1,
            summary="Alice arrived at Warehouse",
        ),
        "ev_evt_02": EvidenceReference(
            id="ev_evt_02",
            category=EvidenceCategory.CANONICAL_FACT,
            entity_type="event",
            entity_id="evt_02",
            tick=4,
            summary="Alice relocated to Docks",
        ),
        "ev_evt_03": EvidenceReference(
            id="ev_evt_03",
            category=EvidenceCategory.CANONICAL_FACT,
            entity_type="event",
            entity_id="evt_03",
            tick=2,
            summary="Bob radioed dispatch",
        ),
        "pat_NG_001": EvidenceReference(
            id="pat_NG_001",
            category=EvidenceCategory.RETRIEVED_KNOWLEDGE,
            entity_type="pattern",
            entity_id="NG-001",
            summary="Sudden Revelation abstract pattern",
        ),
        "rec_pressure": EvidenceReference(
            id="rec_pressure",
            category=EvidenceCategory.RECOMMENDATION,
            entity_type="recommendation",
            entity_id="rec_deadline",
            summary="Director recommended announcing a deadline",
        ),
        "belief_alice": EvidenceReference(
            id="belief_alice",
            category=EvidenceCategory.CHARACTER_KNOWLEDGE,
            entity_type="belief",
            entity_id="prop_alarm_disabled",
            summary="Alice believes alarm is disabled",
            metadata={"character_id": "char_alice", "holder_id": "char_alice", "truth": True},
        ),
        "belief_bob": EvidenceReference(
            id="belief_bob",
            category=EvidenceCategory.CHARACTER_KNOWLEDGE,
            entity_type="belief",
            entity_id="prop_alarm_disabled",
            summary="Bob believes alarm is active",
            metadata={"character_id": "char_bob", "holder_id": "char_bob", "truth": False},
        ),
    }

    # 1. Category Mismatch: Retrieved principle cited as canonical story fact
    claim_cat_mismatch = GroundedClaim(
        claim_id="cm1",
        claim_text="Alice experienced a dramatic sudden revelation.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["pat_NG_001"],
    )
    res_cm1 = EvidenceValidator.verify_claim(claim_cat_mismatch, world, evidence_catalog, k_catalog)
    assert res_cm1.verification_status == ClaimVerificationStatus.CATEGORY_MISMATCH
    assert "abstract retrieved knowledge principles cannot substantiate" in (res_cm1.verification_notes or "")

    # 2. Category Mismatch: Recommendation presented as executed canonical event
    claim_rec_mismatch = GroundedClaim(
        claim_id="cm2",
        claim_text="Director successfully executed an announcement in simulation history.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["rec_pressure"],
    )
    res_cm2 = EvidenceValidator.verify_claim(claim_rec_mismatch, world, evidence_catalog, k_catalog)
    assert res_cm2.verification_status == ClaimVerificationStatus.CATEGORY_MISMATCH
    assert "unexecuted advisory recommendation" in (res_cm2.verification_notes or "")

    # 3. Character-Belief Firewall: Claim asserts Alice's belief using Bob's knowledge
    claim_firewall = GroundedClaim(
        claim_id="fw1",
        claim_text="Alice believes the alarm is active.",
        category=EvidenceCategory.CHARACTER_KNOWLEDGE,
        cited_evidence_ids=["belief_bob"],
        metadata={"subject_character_id": "char_alice"},
    )
    res_fw1 = EvidenceValidator.verify_claim(claim_firewall, world, evidence_catalog, k_catalog)
    assert res_fw1.verification_status == ClaimVerificationStatus.CONTRADICTORY
    assert "WorldView firewall violation" in (res_fw1.verification_notes or "")

    # 4. Outdated Evidence: Claim asserts Alice is currently at Warehouse citing Tick 1 event, superseded by Tick 4 move
    claim_outdated = GroundedClaim(
        claim_id="od1",
        claim_text="Alice is currently stationed at the Warehouse.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_evt_01"],
        metadata={
            "asserts_current_state": True,
            "target_character_id": "char_alice",
            "asserted_location_id": "loc_wh",
        },
    )
    res_od1 = EvidenceValidator.verify_claim(claim_outdated, world, evidence_catalog, k_catalog)
    assert res_od1.verification_status == ClaimVerificationStatus.OUTDATED
    assert "Outdated historical evidence" in (res_od1.verification_notes or "")

    # 5. Direct Contradiction: Secret claimed to be held by Bob when canonically held by Alice
    claim_contra = GroundedClaim(
        claim_id="ct1",
        claim_text="Bob holds the vault code secret.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_evt_03"],
        metadata={
            "secret_id": "sec_vault",
            "asserted_secret_holder_id": "char_bob",
        },
    )
    res_ct1 = EvidenceValidator.verify_claim(claim_contra, world, evidence_catalog, k_catalog)
    assert res_ct1.verification_status == ClaimVerificationStatus.CONTRADICTORY
    assert "canonically held by 'char_alice'" in (res_ct1.verification_notes or "")

    # 6. Valid Citation that Does NOT Support Claim: Citing Bob's dispatch call to claim Alice spoke to Bob
    claim_unsupported = GroundedClaim(
        claim_id="dc1",
        claim_text="Alice spoke to Bob in the corridor.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_evt_03"],
        metadata={"required_actor_ids": ["char_alice"]},
    )
    res_dc1 = EvidenceValidator.verify_claim(claim_unsupported, world, evidence_catalog, k_catalog)
    assert res_dc1.verification_status == ClaimVerificationStatus.UNSUPPORTED
    assert "Evidence disconnect" in (res_dc1.verification_notes or "")


def test_grounded_rag_service_project_queries():
    world = WorldState(
        id="w_demo",
        name="Warehouse",
        description="A rainy warehouse",
        current_tick=3,
        locations={"loc_wh": Location(id="loc_wh", name="Bay", description="Main Bay", connected_locations=[])},
        characters={
            "char_cross": Character(id="char_cross", name="Evelyn Cross", role="Detective", current_location_id="loc_wh"),
            "char_vane": Character(id="char_vane", name="Vincent Vane", role="Smuggler", current_location_id="loc_wh"),
        },
        secrets={
            "sec_dossier": Secret(id="sec_dossier", statement="The dossier is hidden under the floorboards", character_id="char_cross")
        },
        events={
            "evt_01": Event(id="evt_01", tick=1, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_cross"], description="Cross enters the bay"),
            "evt_02": Event(id="evt_02", tick=2, event_type=EventType.CHARACTER_MOVED, actor_ids=["char_vane"], description="Vane enters the bay"),
        },
    )

    conflict_graph = ConflictGraph(
        project_id="proj_demo",
        edges=[
            ConflictEdge(
                source_character_id="char_cross",
                target_character_id="char_vane",
                dimensions={ConflictDimension.GOAL_OPPOSITION: 0.8, ConflictDimension.RESOURCE_COMPETITION: 0.7},
                aggregate_intensity=0.75,
            )
        ],
    )

    proj = ProjectData(
        metadata=ProjectMetadata(
            id="proj_demo",
            title="Warehouse Demo",
            seed_prompt="A detective confronts a smuggler in a warehouse.",
            current_tick=3,
            total_events=2,
            total_scenes=0,
            total_panels=0,
        ),
        world=world,
        conflict_graph=conflict_graph,
    )

    service = NarrativeRAGService()
    service.load_core_knowledge()

    # Query 1: What narrative patterns resemble the current conflict?
    res_conf = service.query_project(proj, "What narrative patterns resemble the current conflict?")
    assert res_conf.status == RAGAnswerStatus.SUCCESS
    assert len(res_conf.claims) > 0
    assert len(res_conf.retrieved_pattern_ids) > 0
    for claim in res_conf.claims:
        assert claim.verification_status in (ClaimVerificationStatus.VERIFIED, ClaimVerificationStatus.INFERRED)

    # Query 2: Which unresolved conflicts have been developing?
    res_unres = service.query_project(proj, "Which unresolved conflicts have been developing?")
    assert res_unres.status == RAGAnswerStatus.SUCCESS
    assert "Cross vs Vincent Vane" in res_unres.answer or "char_cross" in res_unres.answer
    assert len(res_unres.unresolved_conflicts) > 0

    # Query 3: What types of environmental pressure could create meaningful choices?
    res_press = service.query_project(proj, "What types of environmental pressure could create meaningful choices?")
    assert res_press.status == RAGAnswerStatus.SUCCESS
    assert "advisory" in res_press.answer.lower() or "director" in res_press.answer.lower()

    # Query 4: Which setups have not yet received a payoff?
    res_setup = service.query_project(proj, "Which setups have not yet received a payoff?")
    assert res_setup.status == RAGAnswerStatus.SUCCESS
    assert "floorboards" in res_setup.answer or "dossier" in res_setup.answer

    # Query 5: Replay / benchmark retrieval comparison
    benchmark = service.benchmark_retrieval("interpersonal confrontation secret", top_k=3)
    assert "lexical" in benchmark
    assert "semantic" in benchmark
    assert "hybrid" in benchmark
    assert len(benchmark["hybrid"]) > 0


def test_rag_sovereignty_cannot_mutate_world_state():
    world = WorldState(
        id="w_immut",
        name="Imm",
        description="Imm",
        current_tick=2,
        locations={"loc_1": Location(id="loc_1", name="Room", description="Room", connected_locations=[])},
        characters={"char_1": Character(id="char_1", name="Char", role="Detective", current_location_id="loc_1")},
        events={
            "evt_01": Event(id="evt_01", tick=1, event_type=EventType.OTHER, description="Initial event")
        },
    )

    initial_event_count = len(world.events)
    initial_char_state = world.characters["char_1"].model_dump()

    proj = ProjectData(
        metadata=ProjectMetadata(
            id="proj_immut",
            title="Imm",
            seed_prompt="Test",
            current_tick=2,
            total_events=1,
            total_scenes=0,
            total_panels=0,
        ),
        world=world,
    )

    service = NarrativeRAGService()
    service.load_core_knowledge()

    # Run queries
    _ = service.query_project(proj, "What patterns resemble the conflict?")
    _ = service.query_project(proj, "What environmental pressures can be applied?")

    # Verify canonical invariants
    assert len(world.events) == initial_event_count
    assert world.characters["char_1"].model_dump() == initial_char_state


def test_rag_api_endpoints():
    """Verify RAG endpoints function through FastAPI TestClient."""
    import tempfile
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with tempfile.TemporaryDirectory() as tmpdir:
        app = create_app(store_dir=tmpdir)
        client = TestClient(app)

        # 1. Patterns endpoint
        res = client.get("/api/narrative-rag/patterns")
        assert res.status_code == 200
        patterns = res.json()
        assert len(patterns) >= 15
        pid = patterns[0]["id"]

        # 2. Pattern detail endpoint
        res_pat = client.get(f"/api/narrative-rag/patterns/{pid}")
        assert res_pat.status_code == 200
        assert res_pat.json()["id"] == pid

        # 3. Search endpoint
        search_res = client.post(
            "/api/narrative-rag/search",
            json={"query": "betrayal confrontation", "top_k": 3},
        )
        assert search_res.status_code == 200
        search_hits = search_res.json()
        assert len(search_hits) > 0
        assert "score" in search_hits[0]

        # 4. Benchmark endpoint
        bench_res = client.get("/api/narrative-rag/benchmark?query=suspicion+secret")
        assert bench_res.status_code == 200
        bench_data = bench_res.json()
        assert "lexical" in bench_data
        assert "semantic" in bench_data
        assert "hybrid" in bench_data

        # 5. Project grounded query endpoint
        create_res = client.post(
            "/api/projects",
            json={
                "seed_prompt": "Detective Cross tracks smuggler Vane in a foggy shipping harbor.",
                "title": "Harbor Mystery",
            },
        )
        assert create_res.status_code == 200
        proj_id = create_res.json()["id"]

        query_res = client.post(
            f"/api/projects/{proj_id}/narrative-rag/query",
            json={"query": "What narrative patterns resemble the current conflict?"},
        )
        assert query_res.status_code == 200
        rag_data = query_res.json()
        assert "answer" in rag_data
        assert "claims" in rag_data
        assert "status" in rag_data
