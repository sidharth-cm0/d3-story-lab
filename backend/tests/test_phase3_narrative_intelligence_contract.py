"""Tests for Phase 3: Narrative Intelligence Contract & Evaluation Baseline.

Verifies:
1. System Boundary Specifications: Roles for Simulation, WorldState, EventLog, Genome,
   RAG, Advisor, Director, Graph, and Scribe are formally defined and immutable.
2. Standardized Evidence References: Citations carry verifiable IDs (event, character, tick,
   relationship, knowledge record, analyzer version).
3. Evidence Category Firewall: Abstract patterns or recommendations cited as canonical facts
   are strictly classified as CATEGORY_MISMATCH.
4. Claim Verification Status: Claims without evidence are marked INFERRED; invalid IDs are UNSUPPORTED.
5. Evaluation Corpus: Versioned test scenarios (e.g. Missing Dossier, Hotel Intrigue) correctly instantiate
   with strict character knowledge boundaries.
6. Baseline Metrics Suite: Calculates all 11 required baseline dimensions (replay, validation,
   causality, patterns, citations, unsupported rate, no-answer rate, boundary violations,
   director audits, graph consistency, screenplay grounding).
7. Correct No-Answer Behavior: Proves that queries with zero canonical evidence return explicit no-answer.
"""

import pytest
from src.domain.world import WorldState
from src.domain.event import Event, EventType
from src.narrative.rag.models import (
    EvidenceCategory,
    ClaimVerificationStatus,
    GroundedClaim,
)
from src.narrative.intelligence_contract import (
    SystemBoundaryRole,
    SYSTEM_ROLE_SPECIFICATIONS,
    StandardizedEvidence,
    NarrativeContractVerifier,
    BaselineMetricsCalculator,
    NarrativeBaselineMetrics,
)
from src.narrative.evaluation_corpus import (
    SCENARIO_MISSING_DOSSIER_V1,
    SCENARIO_HOTEL_INTRIGUE_V1,
    EVALUATION_CORPUS,
    create_missing_dossier_world,
    create_hotel_intrigue_world,
)


def test_system_boundary_specifications():
    """All 9 system roles must have formal specifications with immutable non-mutation invariants."""
    expected_roles = {
        SystemBoundaryRole.SIMULATION,
        SystemBoundaryRole.WORLD_STATE,
        SystemBoundaryRole.EVENT_LOG,
        SystemBoundaryRole.NARRATIVE_GENOME,
        SystemBoundaryRole.RAG,
        SystemBoundaryRole.ADVISOR,
        SystemBoundaryRole.DIRECTOR,
        SystemBoundaryRole.CHARACTER_GRAPH,
        SystemBoundaryRole.SCRIBE,
    }
    assert set(SYSTEM_ROLE_SPECIFICATIONS.keys()) == expected_roles

    # Only Simulation has permission to directly mutate world state
    for role, spec in SYSTEM_ROLE_SPECIFICATIONS.items():
        if role != SystemBoundaryRole.SIMULATION:
            assert spec["can_mutate_world_state"] is False
            assert spec["responsibility"] is not None


def test_standardized_evidence_model():
    """Evidence citations must carry standardized identifiers and convert cleanly to RAG references."""
    evidence = StandardizedEvidence(
        id="ev_001",
        category=EvidenceCategory.CANONICAL_FACT,
        entity_type="event",
        entity_id="evt_vault_entry",
        tick=3,
        character_id="char_cross",
        analyzer_version="0.1.0",
        summary="Evelyn Cross unlocked the secondary access hatch.",
    )
    rag_ref = evidence.to_rag_reference()
    assert rag_ref.id == "ev_001"
    assert rag_ref.category == EvidenceCategory.CANONICAL_FACT
    assert rag_ref.entity_id == "evt_vault_entry"
    assert rag_ref.tick == 3
    assert rag_ref.metadata["character_id"] == "char_cross"


def test_claim_without_evidence_labeled_inferred():
    """Claims without explicit evidence IDs must be labeled INFERRED rather than VERIFIED."""
    world = create_missing_dossier_world()
    claim = GroundedClaim(
        claim_id="cl_01",
        claim_text="Tension between Cross and Vane is escalating rapidly.",
        category=EvidenceCategory.NARRATIVE_INTERPRETATION,
        cited_evidence_ids=[],
    )
    status, reason = NarrativeContractVerifier.audit_claim(world, claim, evidence_pool={})
    assert status == ClaimVerificationStatus.INFERRED
    assert "inference" in reason.lower()


def test_claim_with_nonexistent_evidence_labeled_unsupported():
    """Claims citing nonexistent evidence or missing entities must be labeled UNSUPPORTED."""
    world = create_missing_dossier_world()
    claim = GroundedClaim(
        claim_id="cl_02",
        claim_text="Cross destroyed the dossier at tick 12.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_nonexistent"],
    )
    status, reason = NarrativeContractVerifier.audit_claim(world, claim, evidence_pool={})
    assert status == ClaimVerificationStatus.UNSUPPORTED
    assert "not found" in reason.lower()


def test_category_firewall_detects_mismatch():
    """Citing an abstract retrieved principle or recommendation as an executed fact is rejected as CATEGORY_MISMATCH."""
    world = create_missing_dossier_world()

    # Evidence from retrieved knowledge
    ev_principle = StandardizedEvidence(
        id="ev_pattern_001",
        category=EvidenceCategory.RETRIEVED_KNOWLEDGE,
        entity_type="pattern",
        entity_id="NG-001",
        summary="Abstract dramatic ticking clock mechanism",
    )

    # Claim asserts this is a canonical story fact
    claim = GroundedClaim(
        claim_id="cl_mismatch",
        claim_text="A physical ticking bomb was placed in the vault.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_pattern_001"],
    )

    status, reason = NarrativeContractVerifier.audit_claim(
        world, claim, evidence_pool={"ev_pattern_001": ev_principle}
    )
    assert status == ClaimVerificationStatus.CATEGORY_MISMATCH
    assert "abstract narrative principle" in reason.lower()


def test_evaluation_corpus_initialization_and_boundaries():
    """Evaluation corpus scenarios correctly enforce initial state and character knowledge boundaries."""
    assert "scenario_missing_dossier_v1" in EVALUATION_CORPUS
    assert "scenario_hotel_intrigue_v1" in EVALUATION_CORPUS

    world = create_missing_dossier_world()
    spec = SCENARIO_MISSING_DOSSIER_V1

    # Verify character knowledge boundaries
    cross = world.characters["char_cross"]
    vane = world.characters["char_vane"]

    for restricted_id in spec.character_knowledge_boundaries["char_cross"]:
        assert restricted_id not in cross.known_facts
        assert restricted_id not in cross.secrets

    for restricted_id in spec.character_knowledge_boundaries["char_vane"]:
        assert restricted_id not in vane.known_facts

    # Enforced proposition exists
    assert "prop_safe_locked" in world.propositions
    assert world.propositions["prop_safe_locked"].enforced is True


def test_baseline_metrics_calculator_comprehensive():
    """Baseline metrics calculator evaluates all 11 required dimensions and returns overall score."""
    world = create_missing_dossier_world()

    # Populate two verified events
    ev1 = Event(
        id="evt_001",
        tick=1,
        event_type=EventType.CHARACTER_MOVED,
        actor_ids=["char_cross"],
        location_id="loc_hallway",
        description="Evelyn Cross quietly approached the vault door.",
    )
    ev2 = Event(
        id="evt_002",
        tick=2,
        event_type=EventType.CHARACTER_OBSERVED,
        actor_ids=["char_cross"],
        location_id="loc_vault",
        description="Evelyn Cross inspected the safe lock.",
        caused_by=["evt_001"],
    )
    world.events["evt_001"] = ev1
    world.events["evt_002"] = ev2

    ev_ref = StandardizedEvidence(
        id="ev_ref_1",
        category=EvidenceCategory.CANONICAL_FACT,
        entity_type="event",
        entity_id="evt_001",
        tick=1,
        summary="Cross approached the vault",
    )

    valid_claim = GroundedClaim(
        claim_id="cl_v1",
        claim_text="Cross reached the vault hallway.",
        category=EvidenceCategory.CANONICAL_FACT,
        cited_evidence_ids=["ev_ref_1"],
    )

    metrics = BaselineMetricsCalculator.compute_baseline_metrics(
        scenario_id="scenario_missing_dossier_v1",
        world=world,
        claims=[valid_claim],
        evidence_pool={"ev_ref_1": ev_ref},
        replay_identical=True,
        action_proposals_validated=5,
        action_validation_failures=0,
        unsupported_no_answer_correct=True,
        knowledge_boundary_violations=0,
        director_history=[
            {"applied": False, "status": "BLOCKED_QUIET_PERIOD"},
            {"applied": True, "status": "EXECUTED"},
        ],
    )

    assert isinstance(metrics, NarrativeBaselineMetrics)
    assert metrics.deterministic_replay_consistency == 1.0
    assert metrics.action_validation_correctness == 1.0
    assert metrics.causal_reference_validity == 1.0
    assert metrics.evidence_citation_validity == 1.0
    assert metrics.unsupported_claim_rate == 0.0
    assert metrics.correct_no_answer_rate == 1.0
    assert metrics.character_knowledge_violation_rate == 0.0
    assert metrics.director_interventions_attempted == 2
    assert metrics.director_interventions_executed == 1
    assert "BLOCKED_QUIET_PERIOD" in metrics.director_rejection_reasons
    assert metrics.overall_baseline_score >= 0.90


def test_correct_no_answer_handling():
    """Known no-answer queries from the evaluation corpus must return unsupported status."""
    world = create_missing_dossier_world()
    spec = SCENARIO_MISSING_DOSSIER_V1

    for no_ans_query in spec.known_no_answer_queries:
        # A claim answering a no-answer question without valid evidence IDs
        claim = GroundedClaim(
            claim_id="cl_unsupported",
            claim_text=f"Direct assertion to: {no_ans_query}",
            category=EvidenceCategory.CANONICAL_FACT,
            cited_evidence_ids=[],
        )
        status, _ = NarrativeContractVerifier.audit_claim(world, claim, evidence_pool={})
        # Must be treated as unverified/inferred rather than verified
        assert status in (ClaimVerificationStatus.INFERRED, ClaimVerificationStatus.UNSUPPORTED)
        assert status != ClaimVerificationStatus.VERIFIED
