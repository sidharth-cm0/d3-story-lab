"""Deterministic BM25 lexical retriever and metadata filter engine for D3 Story Lab RAG.

ENFORCES:
1. Pure Python BM25-style lexical ranking (Robertson-Spärck Jones IDF with k1=1.5, b=0.75).
2. Deterministic result ordering with stable tie-breaking (score descending, then record ID ascending).
3. Metadata filtering by dramatic function, conflict type, genre, and tension direction.
4. Explicit no-result behavior when queries or relevance fall below thresholds.
"""

from __future__ import annotations
import math
import re
from typing import Dict, List, Set, Optional, Tuple, Any

from .models import (
    NarrativeKnowledgeRecord,
    RAGSearchFilter,
    RAGSearchResult,
)

ENGLISH_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
}

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, discarding punctuation and short tokens."""
    if not text:
        return []
    tokens = TOKEN_PATTERN.findall(text.lower())
    return [t for t in tokens if len(t) > 2 and t not in ENGLISH_STOP_WORDS]


class BM25Index:
    """In-memory BM25 lexical index built over NarrativeKnowledgeRecord items."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.records: Dict[str, NarrativeKnowledgeRecord] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.doc_term_freqs: Dict[str, Dict[str, int]] = {}
        self.inverted_index: Dict[str, Set[str]] = {}
        self.doc_count: int = 0

    def build_index(self, records: List[NarrativeKnowledgeRecord]) -> None:
        """Build the inverted index deterministically from a list of records."""
        self.records = {r.id: r for r in records}
        self.doc_count = len(records)
        self.doc_lengths.clear()
        self.doc_term_freqs.clear()
        self.inverted_index.clear()

        total_tokens = 0
        for rec in records:
            # Combine searchable fields with title weighting
            text = f"{rec.title} {rec.title} {rec.content} {' '.join(rec.genre_tags)} {' '.join(rec.conflict_types)} {' '.join(rec.causal_relations)}"
            tokens = tokenize(text)
            length = len(tokens)
            self.doc_lengths[rec.id] = length
            total_tokens += length

            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
                if token not in self.inverted_index:
                    self.inverted_index[token] = set()
                self.inverted_index[token].add(rec.id)

            self.doc_term_freqs[rec.id] = tf

        self.avg_doc_length = (total_tokens / self.doc_count) if self.doc_count > 0 else 1.0

    def get_idf(self, term: str) -> float:
        """Calculate Robertson-Spärck Jones Inverse Document Frequency with smoothing."""
        n_q = len(self.inverted_index.get(term, set()))
        if n_q == 0:
            return 0.0
        # Formula: ln( (N - n(q) + 0.5) / (n(q) + 0.5) + 1 )
        return math.log(((self.doc_count - n_q + 0.5) / (n_q + 0.5)) + 1.0)

    def score_document(self, query_tokens: List[str], doc_id: str) -> Tuple[float, List[str]]:
        """Calculate BM25 score for a specific document against query tokens."""
        if doc_id not in self.doc_lengths:
            return 0.0, []

        doc_len = self.doc_lengths[doc_id]
        tf_dict = self.doc_term_freqs.get(doc_id, {})
        denom_norm = 1.0 - self.b + (self.b * (doc_len / self.avg_doc_length if self.avg_doc_length > 0 else 1.0))

        score = 0.0
        matched_tokens: List[str] = []

        for term in query_tokens:
            if term not in tf_dict:
                continue
            tf = tf_dict[term]
            idf = self.get_idf(term)
            term_score = idf * ((tf * (self.k1 + 1.0)) / (tf + (self.k1 * denom_norm)))
            score += term_score
            matched_tokens.append(term)

        return score, matched_tokens


class NarrativeRetriever:
    """Multi-stage retrieval and filter engine for Narrative Knowledge."""

    def __init__(self, records: Optional[List[NarrativeKnowledgeRecord]] = None):
        self.bm25 = BM25Index()
        if records:
            self.rebuild_index(records)

    def rebuild_index(self, records: List[NarrativeKnowledgeRecord]) -> None:
        """Re-index the collection."""
        self.bm25.build_index(records)

    def search(
        self,
        search_filter: RAGSearchFilter,
        semantic_scores: Optional[Dict[str, float]] = None,
    ) -> List[RAGSearchResult]:
        """Perform metadata filtering, lexical ranking, optional semantic blending, and deterministic sorting."""
        if self.bm25.doc_count == 0:
            return []

        # 1. Metadata candidate filtering
        candidate_ids = self._filter_candidates(search_filter)
        if not candidate_ids:
            return []

        query = (search_filter.query or "").strip()
        query_tokens = tokenize(query)

        results: List[RAGSearchResult] = []

        # 2. Score computation across candidates
        candidate_scores: List[Tuple[str, float, List[str], float]] = []
        for doc_id in candidate_ids:
            if query_tokens:
                raw_bm25, matched_terms = self.bm25.score_document(query_tokens, doc_id)
            else:
                raw_bm25, matched_terms = (0.5, [])

            sem_score = 0.0
            if semantic_scores and doc_id in semantic_scores:
                sem_score = max(0.0, min(1.0, semantic_scores[doc_id]))

            candidate_scores.append((doc_id, raw_bm25, matched_terms, sem_score))

        # Calibrated normalization: dynamic candidate-relative scaling
        max_candidate_bm25 = max([cs[1] for cs in candidate_scores], default=0.0)

        for doc_id, raw_bm25, matched_terms, sem_score in candidate_scores:
            rec = self.bm25.records[doc_id]
            reasons: List[str] = []

            if query_tokens:
                if max_candidate_bm25 > 0:
                    norm_lexical = min(1.0, raw_bm25 / max_candidate_bm25)
                else:
                    norm_lexical = 0.0
                if matched_terms:
                    reasons.append(f"Lexical match on: {', '.join(sorted(matched_terms))}")
            else:
                norm_lexical = 0.5
                raw_bm25 = 0.5

            if sem_score > 0.4:
                reasons.append(f"Semantic similarity: {sem_score:.2f}")

            # 3. Hybrid score combination
            if search_filter.mode == "lexical" or not semantic_scores:
                final_score = norm_lexical
            elif search_filter.mode == "semantic":
                final_score = sem_score
            else:  # hybrid
                if query_tokens and semantic_scores:
                    final_score = (norm_lexical * 0.55) + (sem_score * 0.45)
                elif semantic_scores:
                    final_score = sem_score
                else:
                    final_score = norm_lexical

            # Boost slightly for exact metadata alignment
            if search_filter.dramatic_functions and rec.dramatic_function in search_filter.dramatic_functions:
                final_score += 0.05
                reasons.append(f"Target dramatic function '{rec.dramatic_function}' matched")

            if search_filter.conflict_types:
                matched_c = set(rec.conflict_types).intersection(set(search_filter.conflict_types))
                if matched_c:
                    final_score += 0.05
                    reasons.append(f"Conflict types {matched_c} matched")

            # Check threshold
            if final_score >= search_filter.min_score or (not query and not search_filter.min_score):
                results.append(
                    RAGSearchResult(
                        record=rec,
                        score=round(final_score, 4),
                        lexical_score=round(norm_lexical, 4),
                        semantic_score=round(sem_score, 4),
                        match_reasons=reasons,
                    )
                )

        # 5. Deterministic tie-breaking: score descending, then pattern ID ascending
        results.sort(key=lambda r: (-r.score, r.record.id))
        return results[: search_filter.top_k]

    def _filter_candidates(self, sf: RAGSearchFilter) -> Set[str]:
        """Apply deterministic metadata constraints across records."""
        candidates = set(self.bm25.records.keys())

        if sf.dramatic_functions:
            funcs = {f.upper() for f in sf.dramatic_functions}
            candidates = {cid for cid in candidates if self.bm25.records[cid].dramatic_function.upper() in funcs}

        if sf.conflict_types:
            req_conflicts = {c.lower() for c in sf.conflict_types}
            candidates = {
                cid for cid in candidates
                if any(c.lower() in req_conflicts for c in self.bm25.records[cid].conflict_types)
            }

        if sf.genres:
            req_genres = {g.lower() for g in sf.genres}
            candidates = {
                cid for cid in candidates
                if "all" in self.bm25.records[cid].genre_tags or any(g.lower() in req_genres for g in self.bm25.records[cid].genre_tags)
            }

        if sf.tension_directions:
            req_tensions = {t.lower() for t in sf.tension_directions}
            candidates = {cid for cid in candidates if self.bm25.records[cid].tension_direction.lower() in req_tensions}

        return candidates
