"""Narrative RAG package for D3 Story Lab."""

from .models import (
    EvidenceCategory,
    ClaimVerificationStatus,
    RAGAnswerStatus,
    NarrativeKnowledgeRecord,
    EvidenceReference,
    GroundedClaim,
    RAGSearchFilter,
    RAGSearchResult,
    GroundedRAGResponse,
)
from .ingestion import NarrativeKnowledgeIngester, IngestionError
from .retrieval import NarrativeRetriever, BM25Index
from .embeddings import EmbeddingProvider, LocalFeatureEmbeddingProvider
from .grounding import GroundedNarrativeEngine, EvidenceValidator
from .service import NarrativeRAGService

__all__ = [
    "EvidenceCategory",
    "ClaimVerificationStatus",
    "RAGAnswerStatus",
    "NarrativeKnowledgeRecord",
    "EvidenceReference",
    "GroundedClaim",
    "RAGSearchFilter",
    "RAGSearchResult",
    "GroundedRAGResponse",
    "NarrativeKnowledgeIngester",
    "IngestionError",
    "NarrativeRetriever",
    "BM25Index",
    "EmbeddingProvider",
    "LocalFeatureEmbeddingProvider",
    "GroundedNarrativeEngine",
    "EvidenceValidator",
    "NarrativeRAGService",
]
