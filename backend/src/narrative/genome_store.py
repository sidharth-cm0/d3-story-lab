"""Narrative Genome Repository and local store implementation for D3 Story Lab.

Provides:
1. Abstract NarrativeGenomeRepository protocol enabling future drop-in vector/semantic search.
2. Deterministic, inspectable LocalJsonGenomeRepository loading from local JSON.
3. Invariant: Pure read-only knowledge retrieval, zero mutation of canonical state.
"""

from __future__ import annotations
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Set

from ..domain.narrative_genome import (
    NarrativeGenomeRecord,
    DramaticFunction,
    ConflictType,
    ScenePurpose,
    TensionDirection,
)


class NarrativeGenomeRepository(ABC):
    """Abstract repository for narrative genome patterns.

    Enables future drop-in RAG / semantic vector retrieval without modifying analyzers or advisors.
    """

    @abstractmethod
    def get_pattern(self, pattern_id: str) -> Optional[NarrativeGenomeRecord]:
        """Fetch a single genome pattern by ID."""
        pass

    @abstractmethod
    def list_patterns(self) -> List[NarrativeGenomeRecord]:
        """Return all available genome patterns."""
        pass

    @abstractmethod
    def search(
        self,
        dramatic_function: Optional[DramaticFunction] = None,
        conflict_types: Optional[List[ConflictType]] = None,
        scene_purposes: Optional[List[ScenePurpose]] = None,
        genre_tags: Optional[List[str]] = None,
        tension_direction: Optional[TensionDirection] = None,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> List[NarrativeGenomeRecord]:
        """Search patterns matching dramatic criteria."""
        pass


class LocalJsonGenomeRepository(NarrativeGenomeRepository):
    """Local JSON-backed genome repository for deterministic, inspectable storage."""

    def __init__(self, data_path: Optional[str] = None):
        if data_path:
            self._path = Path(data_path)
        else:
            default_paths = [
                Path("/workspaces/d3-story-lab/backend/data/narrative_genome/core_patterns.json"),
                Path(__file__).resolve().parent.parent.parent / "data" / "narrative_genome" / "core_patterns.json",
            ]
            self._path = next((p for p in default_paths if p.exists()), default_paths[0])

        self._patterns: Dict[str, NarrativeGenomeRecord] = {}
        self._load()

    def _load(self) -> None:
        """Load patterns deterministically from JSON file."""
        if not self._path.exists():
            return

        with open(self._path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        for item in raw_data:
            rec = NarrativeGenomeRecord.model_validate(item)
            self._patterns[rec.id] = rec

    def get_pattern(self, pattern_id: str) -> Optional[NarrativeGenomeRecord]:
        """Retrieve pattern by identifier."""
        return self._patterns.get(pattern_id)

    def list_patterns(self) -> List[NarrativeGenomeRecord]:
        """Return all patterns sorted by ID."""
        return [self._patterns[pid] for pid in sorted(self._patterns.keys())]

    def search(
        self,
        dramatic_function: Optional[DramaticFunction] = None,
        conflict_types: Optional[List[ConflictType]] = None,
        scene_purposes: Optional[List[ScenePurpose]] = None,
        genre_tags: Optional[List[str]] = None,
        tension_direction: Optional[TensionDirection] = None,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> List[NarrativeGenomeRecord]:
        """Deterministic heuristic scoring and filtering across loaded patterns."""
        scored: List[tuple[float, NarrativeGenomeRecord]] = []

        conflict_set = set(conflict_types or [])
        purpose_set = set(scene_purposes or [])
        genre_set = {g.lower() for g in (genre_tags or [])}
        q_tokens = {t.lower() for t in (query or "").split() if len(t) > 3}

        for rec in self._patterns.values():
            score = 0.0

            # 1. Dramatic function match
            if dramatic_function:
                if rec.dramatic_function == dramatic_function:
                    score += 3.0
                elif hasattr(rec.dramatic_function, "value") and rec.dramatic_function.value == dramatic_function:
                    score += 3.0

            # 2. Conflict types overlap
            if conflict_set:
                matched_conflicts = len(conflict_set.intersection(set(rec.conflict_types)))
                score += matched_conflicts * 1.5

            # 3. Scene purposes overlap
            if purpose_set:
                matched_purposes = len(purpose_set.intersection(set(rec.scene_purposes)))
                score += matched_purposes * 1.2

            # 4. Tension direction match
            if tension_direction:
                if rec.tension_direction == tension_direction:
                    score += 1.0

            # 5. Genre tag match
            if genre_set:
                rec_genres = {g.lower() for g in rec.genre_tags}
                if "all" in rec_genres or rec_genres.intersection(genre_set):
                    score += 0.8

            # 6. Query text match
            if q_tokens:
                desc_tokens = {t.lower() for t in f"{rec.name} {rec.description}".split()}
                matched_text = len(q_tokens.intersection(desc_tokens))
                score += matched_text * 0.5

            if score > 0.0 or (not dramatic_function and not conflict_types and not query):
                scored.append((score, rec))

        # Sort by score descending, then by pattern ID ascending for determinism
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [r for _, r in scored[:limit]]
