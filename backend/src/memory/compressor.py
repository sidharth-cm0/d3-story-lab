import uuid
from typing import List, Optional
from ..domain import Memory


class MemoryCompressor:
    """Condenses older episodic memories into bounded long-term summary memories"""

    @staticmethod
    def compress(
        memories: List[Memory],
        character_id: str,
        current_tick: int,
        summary_prefix: str = "Summary of past events: ",
    ) -> Optional[Memory]:
        """Compress a list of episodic memories into a single consolidated memory"""
        if not memories:
            return None

        all_summaries = [m.summary for m in memories]
        combined_text = summary_prefix + "; ".join(all_summaries)

        # Average importance and emotional weight
        avg_importance = sum(m.importance for m in memories) / len(memories)
        avg_emotion = sum(m.emotional_weight for m in memories) / len(memories)

        # Collect unique participants and tags
        participants = sorted(list({p for m in memories for p in m.participants}))
        tags = sorted(list({t for m in memories for t in m.tags} | {"compressed_summary"}))

        return Memory(
            id=f"mem_summary_{current_tick}_{uuid.uuid4().hex[:6]}",
            character_id=character_id,
            event_id=None,
            summary=combined_text,
            importance=round(avg_importance, 2),
            emotional_weight=round(avg_emotion, 2),
            participants=participants,
            tick=current_tick,
            tags=tags,
        )
