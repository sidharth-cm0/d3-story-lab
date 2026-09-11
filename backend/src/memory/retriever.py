"""Deterministic memory retrieval scoring and filtering"""
import re
from typing import List, Optional
from ..domain import Memory


class MemoryRetriever:
    """Retrieves and scores memories based on recency, importance, emotional weight, and relevance"""

    @staticmethod
    def score_memory(
        memory: Memory,
        current_tick: int,
        query: Optional[str] = None,
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        emotion_weight: float = 1.0,
    ) -> float:
        """Calculate transparent deterministic retrieval score"""
        # 1. Relevance: lexical match against query terms
        relevance = 0.5  # Default baseline if no query
        if query:
            query_words = set(re.findall(r"\w+", query.lower()))
            if query_words:
                target_text = (memory.summary + " " + " ".join(memory.tags)).lower()
                matches = sum(1 for w in query_words if w in target_text)
                relevance = matches / len(query_words)

        # 2. Recency decay: smooth hyperbolic decay based on tick distance
        tick_distance = max(0, current_tick - memory.tick)
        recency = 1.0 / (1.0 + 0.1 * tick_distance)

        # 3. Importance: 0.0 to 1.0
        importance = memory.importance

        # 4. Emotional significance: magnitude of emotional weight |w| in [0.0, 1.0]
        emotional_significance = abs(memory.emotional_weight)

        total_score = (
            relevance
            + (recency_weight * recency)
            + (importance_weight * importance)
            + (emotion_weight * emotional_significance)
        )
        return total_score

    @classmethod
    def retrieve(
        cls,
        memories: List[Memory],
        current_tick: int,
        query: Optional[str] = None,
        limit: int = 5,
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        emotion_weight: float = 1.0,
    ) -> List[Memory]:
        """Rank and return top memories for a character without leaking unrelated history"""
        scored = [
            (
                cls.score_memory(
                    mem,
                    current_tick,
                    query=query,
                    recency_weight=recency_weight,
                    importance_weight=importance_weight,
                    emotion_weight=emotion_weight,
                ),
                mem,
            )
            for mem in memories
        ]
        # Sort descending by score, tie-break by tick descending
        scored.sort(key=lambda item: (item[0], item[1].tick), reverse=True)
        return [mem for _, mem in scored[:limit]]
