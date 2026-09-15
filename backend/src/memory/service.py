"""MemoryService coordinating working, episodic, and long-term memory for characters"""
import uuid
import hashlib
from typing import List, Optional
from ..domain import WorldState, Memory
from .retriever import MemoryRetriever
from .compressor import MemoryCompressor


class MemoryService:
    """Service managing memory creation, retrieval, and compression for characters"""

    def __init__(self, world: WorldState, seed: Optional[int] = None):
        self.world = world
        self.seed = seed

    def form_memory(
        self,
        character_id: str,
        summary: str,
        importance: float,
        emotional_weight: float,
        event_id: Optional[str] = None,
        participants: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Memory:
        """Create a new memory, record canonically in WorldState, and attach ID to character"""
        if self.seed is not None:
            slug = hashlib.sha256(
                f"{self.seed}:{self.world.current_tick}:{character_id}:{len(self.world.memories)}:{summary}".encode()
            ).hexdigest()[:6]
        else:
            slug = uuid.uuid4().hex[:6]
        mem_id = f"mem_{self.world.current_tick}_{character_id}_{slug}"
        memory = Memory(
            id=mem_id,
            character_id=character_id,
            event_id=event_id,
            summary=summary,
            importance=max(0.0, min(1.0, importance)),
            emotional_weight=max(-1.0, min(1.0, emotional_weight)),
            participants=participants or [],
            tick=self.world.current_tick,
            tags=tags or [],
        )
        self.world.memories[memory.id] = memory

        char = self.world.characters.get(character_id)
        if char and memory.id not in char.memories:
            char.memories.append(memory.id)

        return memory

    def get_character_memories(self, character_id: str) -> List[Memory]:
        """Fetch all memories owned by a character"""
        return self.world.get_character_memories(character_id)

    def get_working_memory(self, character_id: str, limit: int = 3) -> List[Memory]:
        """Retrieve most recent memories forming character's immediate working memory"""
        mems = self.get_character_memories(character_id)
        # Sort descending by tick
        mems.sort(key=lambda m: m.tick, reverse=True)
        return mems[:limit]

    def retrieve_relevant_memories(
        self,
        character_id: str,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> List[Memory]:
        """Retrieve top ranked memories using transparent deterministic formula"""
        mems = self.get_character_memories(character_id)
        return MemoryRetriever.retrieve(
            mems,
            current_tick=self.world.current_tick,
            query=query,
            limit=limit,
        )

    def compress_old_memories(
        self,
        character_id: str,
        older_than_ticks: int = 10,
    ) -> Optional[Memory]:
        """Compress episodic memories older than a tick threshold into a long-term summary"""
        mems = self.get_character_memories(character_id)
        threshold_tick = max(0, self.world.current_tick - older_than_ticks)
        to_compress = [m for m in mems if m.tick <= threshold_tick and "compressed_summary" not in m.tags]

        if len(to_compress) < 3:
            return None

        summary_mem = MemoryCompressor.compress(to_compress, character_id, self.world.current_tick)
        if summary_mem:
            self.world.memories[summary_mem.id] = summary_mem
            char = self.world.characters.get(character_id)
            if char:
                # Replace compressed memories with summary memory in character's memory list
                compressed_ids = {m.id for m in to_compress}
                char.memories = [mid for mid in char.memories if mid not in compressed_ids]
                char.memories.append(summary_mem.id)

        return summary_mem
