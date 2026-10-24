"""Labeled evaluation benchmark for Narrative RAG retrieval quality.

Evaluates and compares:
1. Pure BM25 Lexical Ranking
2. Local Feature Hashing Embeddings
3. Calibrated Hybrid Ranking

Measures:
- Precision@1, Precision@3, Recall@3, and Mean Reciprocal Rank (MRR).
- Deterministic tie-breaking and ranking stability.
- Out-of-domain zero-result relevance thresholding.
- Duplicate ingestion idempotency.
"""

from typing import List, Set, Dict, Any, Optional
import pytest
from src.narrative.rag.models import (
    NarrativeKnowledgeRecord,
    RAGSearchFilter,
    RAGSearchResult,
)
from src.narrative.rag.ingestion import NarrativeKnowledgeIngester
from src.narrative.rag.retrieval import NarrativeRetriever
from src.narrative.rag.embeddings import LocalFeatureEmbeddingProvider


# 1. Labeled Evaluation Benchmark Dataset
BENCHMARK_CASES = [
    {
        "id": "case_01",
        "query": "secret concealment mounting suspicion between allies",
        "expected_ids": {"NG-001"},
        "irrelevant_ids": {"NG-004", "NG-008"},
        "filter_kwargs": {},
    },
    {
        "id": "case_02",
        "query": "temporal countdown forces immediate action before operational window closes",
        "expected_ids": {"NG-004"},
        "irrelevant_ids": {"NG-001", "NG-009"},
        "filter_kwargs": {},
    },
    {
        "id": "case_03",
        "query": "costly dilemma tests loyalty of trusted ally under pressure",
        "expected_ids": {"NG-003"},
        "irrelevant_ids": {"NG-004", "NG-011"},
        "filter_kwargs": {},
    },
    {
        "id": "case_04",
        "query": "abrupt power inversion shifts dominant position to underdog",
        "expected_ids": {"NG-006"},
        "irrelevant_ids": {"NG-009", "NG-004"},
        "filter_kwargs": {"dramatic_functions": ["REVERSAL"]},
    },
    {
        "id": "case_05",
        "query": "tactical action fails due to obstacle and resistance",
        "expected_ids": {"NG-005"},
        "irrelevant_ids": {"NG-008", "NG-006"},
        "filter_kwargs": {"dramatic_functions": ["COMPLICATION"]},
    },
    {
        "id": "case_06",
        "query": "earlier item or clue returns to resolve deadlock",
        "expected_ids": {"NG-008"},
        "irrelevant_ids": {"NG-001", "NG-013"},
        "filter_kwargs": {"dramatic_functions": ["PAYOFF"]},
    },
    {
        "id": "case_07",
        "query": "decompression interval allows recovery after high confrontation",
        "expected_ids": {"NG-009"},
        "irrelevant_ids": {"NG-004", "NG-001"},
        "filter_kwargs": {"dramatic_functions": ["TRANSITION"]},
    },
    {
        "id": "case_08",
        "query": "acute competition over strictly limited key fuel and resources",
        "expected_ids": {"NG-011"},
        "irrelevant_ids": {"NG-009", "NG-002"},
        "filter_kwargs": {"conflict_types": ["resource"]},
    },
    {
        "id": "case_09_ood",
        "query": "quantum entanglement hyperdrive warp bubble coordinates",
        "expected_ids": set(),
        "irrelevant_ids": {"NG-001", "NG-002", "NG-003"},
        "filter_kwargs": {"min_score": 0.70},
    },
    {
        "id": "case_10_ood",
        "query": "recipe for sourdough bread with wild yeast fermentation",
        "expected_ids": set(),
        "irrelevant_ids": {"NG-001", "NG-002", "NG-003"},
        "filter_kwargs": {"min_score": 0.70},
    },
]


def compute_metrics(
    retriever: NarrativeRetriever,
    embedder: Optional[LocalFeatureEmbeddingProvider],
    mode: str,
) -> Dict[str, float]:
    """Compute Precision@1, Precision@3, Recall@3, and MRR for a retrieval configuration."""
    eval_cases = [c for c in BENCHMARK_CASES if c["expected_ids"]]
    p_at_1_sum = 0.0
    p_at_3_sum = 0.0
    r_at_3_sum = 0.0
    mrr_sum = 0.0

    # Pre-embed collection for semantic/hybrid modes
    doc_embeddings: Dict[str, List[float]] = {}
    if embedder:
        for r_id, rec in retriever.bm25.records.items():
            doc_embeddings[r_id] = embedder.embed_text(f"{rec.title} {rec.content} {' '.join(rec.genre_tags)}")

    for case in eval_cases:
        query = case["query"]
        expected = case["expected_ids"]
        filter_kwargs = dict(case["filter_kwargs"])

        sem_scores = None
        if embedder and mode in ("semantic", "hybrid"):
            q_vec = embedder.embed_text(query)
            sem_scores = {
                r_id: embedder.cosine_similarity(q_vec, d_vec)
                for r_id, d_vec in doc_embeddings.items()
            }

        sf = RAGSearchFilter(query=query, mode=mode, top_k=3, **filter_kwargs)
        results = retriever.search(sf, semantic_scores=sem_scores)
        retrieved_ids = [r.record.id for r in results]

        # Precision@1
        top_1 = retrieved_ids[:1]
        p_at_1 = len(set(top_1).intersection(expected)) / 1.0 if top_1 else 0.0
        p_at_1_sum += p_at_1

        # Precision@3
        top_3 = retrieved_ids[:3]
        p_at_3 = len(set(top_3).intersection(expected)) / len(top_3) if top_3 else 0.0
        p_at_3_sum += p_at_3

        # Recall@3
        r_at_3 = len(set(top_3).intersection(expected)) / len(expected) if expected else 1.0
        r_at_3_sum += r_at_3

        # Reciprocal Rank
        rr = 0.0
        for rank, r_id in enumerate(retrieved_ids, start=1):
            if r_id in expected:
                rr = 1.0 / rank
                break
        mrr_sum += rr

    n = len(eval_cases)
    return {
        "precision@1": round(p_at_1_sum / n, 4),
        "precision@3": round(p_at_3_sum / n, 4),
        "recall@3": round(r_at_3_sum / n, 4),
        "mrr": round(mrr_sum / n, 4),
    }


def test_retrieval_benchmark_and_model_comparison():
    """Run benchmark comparison across BM25, Local Feature Hashing, and Calibrated Hybrid."""
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()
    assert len(records) >= 12, "Should have loaded core genome patterns"

    retriever = NarrativeRetriever(records)
    embedder = LocalFeatureEmbeddingProvider()

    bm25_metrics = compute_metrics(retriever, embedder, mode="lexical")
    hash_metrics = compute_metrics(retriever, embedder, mode="semantic")
    hybrid_metrics = compute_metrics(retriever, embedder, mode="hybrid")

    print("\n" + "=" * 65)
    print("RETRIEVAL EVALUATION BENCHMARK RESULTS (D3 STORY LAB)")
    print("=" * 65)
    print(f"{'Method':<25} | {'P@1':<7} | {'P@3':<7} | {'R@3':<7} | {'MRR':<7}")
    print("-" * 65)
    print(f"{'Pure BM25 Lexical':<25} | {bm25_metrics['precision@1']:<7.2%} | {bm25_metrics['precision@3']:<7.2%} | {bm25_metrics['recall@3']:<7.2%} | {bm25_metrics['mrr']:<7.4f}")
    print(f"{'Local Feature Hashing':<25} | {hash_metrics['precision@1']:<7.2%} | {hash_metrics['precision@3']:<7.2%} | {hash_metrics['recall@3']:<7.2%} | {hash_metrics['mrr']:<7.4f}")
    print(f"{'Calibrated Hybrid':<25} | {hybrid_metrics['precision@1']:<7.2%} | {hybrid_metrics['precision@3']:<7.2%} | {hybrid_metrics['recall@3']:<7.2%} | {hybrid_metrics['mrr']:<7.4f}")
    print("=" * 65)

    # Assertions on retrieval quality
    assert bm25_metrics["precision@1"] >= 0.75, "BM25 should achieve at least 75% P@1 on labeled narrative patterns"
    assert bm25_metrics["recall@3"] >= 0.85, "BM25 should achieve at least 85% R@3 on labeled narrative patterns"
    assert hybrid_metrics["recall@3"] >= 0.85, "Hybrid should achieve high recall across labeled set"


def test_out_of_domain_queries_return_empty():
    """Unrelated out-of-domain queries with minimum score threshold must return zero results."""
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()
    retriever = NarrativeRetriever(records)

    ood_cases = [c for c in BENCHMARK_CASES if not c["expected_ids"]]
    assert len(ood_cases) == 2

    for case in ood_cases:
        sf = RAGSearchFilter(query=case["query"], min_score=0.70)
        results = retriever.search(sf)
        assert results == [], f"Expected empty result for OOD query: {case['query']}"


def test_duplicate_ingestion_idempotency():
    """Ingesting the same record set multiple times must not inflate counts or distort BM25 IDF."""
    ingester = NarrativeKnowledgeIngester()
    records_1 = ingester.load_defaults()
    initial_count = len(records_1)

    # Ingest duplicate records with identical IDs
    ingester.ingest_batch(records_1)
    retriever = NarrativeRetriever(list(ingester.records.values()))

    assert len(retriever.bm25.records) == initial_count
    assert retriever.bm25.doc_count == initial_count

    # Querying should yield stable single results per pattern ID
    results = retriever.search(RAGSearchFilter(query="secret escalation suspicion", top_k=5))
    returned_ids = [r.record.id for r in results]
    assert len(returned_ids) == len(set(returned_ids)), "Result list should have unique pattern IDs"


def test_ranking_stability_under_permutations():
    """Permuting the indexing order of records must not alter the final search ranking."""
    ingester = NarrativeKnowledgeIngester()
    records = ingester.load_defaults()

    retriever_original = NarrativeRetriever(records)
    res_orig = retriever_original.search(RAGSearchFilter(query="loyalty dilemma alliance betrayal", top_k=4))

    # Reverse record ingestion order
    retriever_reversed = NarrativeRetriever(list(reversed(records)))
    res_rev = retriever_reversed.search(RAGSearchFilter(query="loyalty dilemma alliance betrayal", top_k=4))

    assert [r.record.id for r in res_orig] == [r.record.id for r in res_rev]
    for r1, r2 in zip(res_orig, res_rev):
        assert r1.score == r2.score
