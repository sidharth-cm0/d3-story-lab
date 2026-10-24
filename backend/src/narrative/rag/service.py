"""High-level service interface for Grounded Narrative RAG in D3 Story Lab."""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .models import (
    NarrativeKnowledgeRecord,
    RAGSearchFilter,
    RAGSearchResult,
    GroundedRAGResponse,
)
from .ingestion import NarrativeKnowledgeIngester
from .retrieval import NarrativeRetriever
from .embeddings import EmbeddingProvider, LocalFeatureEmbeddingProvider
from .grounding import GroundedNarrativeEngine
from ...storage.project_store import ProjectData


class NarrativeRAGService:
    """Singleton-capable service providing ingestion, retrieval, and grounded inquiry."""

    _instance: Optional[NarrativeRAGService] = None

    @classmethod
    def get_instance(cls) -> NarrativeRAGService:
        """Return or create singleton instance initialized with core knowledge."""
        if cls._instance is None:
            svc = cls()
            svc.load_core_knowledge()
            cls._instance = svc
        return cls._instance

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        patterns_path: Optional[Union[str, Path]] = None,
    ):
        self.ingester = NarrativeKnowledgeIngester()
        self.embedding_provider: EmbeddingProvider = embedding_provider or LocalFeatureEmbeddingProvider()
        self.retriever = NarrativeRetriever()
        self._pattern_embeddings: Dict[str, List[float]] = {}
        self.patterns_path = patterns_path

    def load_core_knowledge(self, path: Optional[Union[str, Path]] = None) -> int:
        """Ingest core patterns and index them into lexical and semantic stores."""
        target_path = path or self.patterns_path
        records = self.ingester.load_defaults(target_path)
        self.retriever.rebuild_index(records)

        # Precompute local semantic embeddings
        if self.embedding_provider and self.embedding_provider.is_available:
            self._pattern_embeddings.clear()
            for r in records:
                text_to_embed = f"{r.title}. {r.content} Genre: {' '.join(r.genre_tags)}"
                self._pattern_embeddings[r.id] = self.embedding_provider.embed_text(text_to_embed)

        return len(records)

    def ingest_record(self, raw: Dict[str, Any], source_ref: str = "custom") -> NarrativeKnowledgeRecord:
        """Ingest a single pattern and update indexes."""
        rec = self.ingester.ingest_record(raw, source_ref=source_ref)
        self.retriever.rebuild_index(list(self.ingester.records.values()))
        if self.embedding_provider and self.embedding_provider.is_available:
            self._pattern_embeddings[rec.id] = self.embedding_provider.embed_text(f"{rec.title}. {rec.content}")
        return rec

    def get_pattern(self, pattern_id: str) -> Optional[NarrativeKnowledgeRecord]:
        """Fetch pattern by ID."""
        return self.ingester.get(pattern_id)

    def list_patterns(self) -> List[NarrativeKnowledgeRecord]:
        """Return all patterns sorted by ID."""
        return sorted(self.ingester.records.values(), key=lambda r: r.id)

    def search_patterns(self, search_filter: RAGSearchFilter) -> List[RAGSearchResult]:
        """Search patterns with metadata filtering and hybrid/lexical ranking."""
        semantic_scores: Optional[Dict[str, float]] = None

        if search_filter.query and self.embedding_provider and self.embedding_provider.is_available and search_filter.mode != "lexical":
            query_vec = self.embedding_provider.embed_text(search_filter.query)
            semantic_scores = {}
            for pid, pat_vec in self._pattern_embeddings.items():
                semantic_scores[pid] = self.embedding_provider.cosine_similarity(query_vec, pat_vec)

        return self.retriever.search(search_filter, semantic_scores=semantic_scores)

    def search(self, search_filter: RAGSearchFilter) -> List[RAGSearchResult]:
        """Alias for search_patterns."""
        return self.search_patterns(search_filter)

    def query_project(
        self,
        project: ProjectData,
        query: str,
        search_filter: Optional[RAGSearchFilter] = None,
        filter: Optional[RAGSearchFilter] = None,
    ) -> GroundedRAGResponse:
        """Answer a narrative intelligence query grounded against project world state and retrieved patterns."""
        sf = search_filter or filter or RAGSearchFilter(query=query, top_k=5)
        if not sf.query:
            sf.query = query

        search_results = self.search_patterns(sf)
        retrieved_patterns = [res.record for res in search_results]

        response = GroundedNarrativeEngine.answer_grounded_query(
            query=query,
            world=project.world,
            conflict_graph=project.conflict_graph,
            retrieved_patterns=retrieved_patterns,
            knowledge_catalog=self.ingester.records,
        )
        response.project_id = project.metadata.id
        return response

    def benchmark_retrieval(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Benchmark and compare lexical vs semantic vs hybrid ranking for transparency."""
        lexical_filter = RAGSearchFilter(query=query, mode="lexical", top_k=top_k)
        semantic_filter = RAGSearchFilter(query=query, mode="semantic", top_k=top_k)
        hybrid_filter = RAGSearchFilter(query=query, mode="hybrid", top_k=top_k)

        lex_results = self.search_patterns(lexical_filter)
        sem_results = self.search_patterns(semantic_filter)
        hyb_results = self.search_patterns(hybrid_filter)

        return {
            "query": query,
            "embedding_model": self.embedding_provider.model_id if self.embedding_provider else "none",
            "index_version": self.embedding_provider.index_version if self.embedding_provider else "none",
            "lexical": [{"id": r.record.id, "title": r.record.title, "score": r.score} for r in lex_results],
            "semantic": [{"id": r.record.id, "title": r.record.title, "score": r.score} for r in sem_results],
            "hybrid": [{"id": r.record.id, "title": r.record.title, "score": r.score} for r in hyb_results],
        }

    def benchmark_lexical_vs_semantic(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Alias for benchmark_retrieval."""
        return self.benchmark_retrieval(query, top_k=top_k)
