"""Tests for Milestone 4: Memory System"""
import pytest
from src.demo_world import create_demo_world
from src.domain import Memory
from src.memory import MemoryService, MemoryRetriever, MemoryCompressor


class TestMemorySystem:
    """Tests verifying memory formation, retrieval scoring, privacy, and compression"""

    def test_memory_formation_and_ownership(self):
        """Test forming memories and confirming canonical storage and ownership"""
        world = create_demo_world()
        service = MemoryService(world)

        mem = service.form_memory(
            character_id="char_arjun",
            summary="I saw Maya hide the briefcase behind the desk.",
            importance=0.9,
            emotional_weight=0.6,
            participants=["char_maya"],
            tags=["investigation", "briefcase"],
        )

        assert mem.id in world.memories
        assert mem.id in world.characters["char_arjun"].memories
        assert mem.id not in world.characters["char_maya"].memories

    def test_memory_privacy_isolation(self):
        """Test that Arjun's memories are completely inaccessible from Maya's retrieval"""
        world = create_demo_world()
        service = MemoryService(world)

        # Create private memory for Arjun
        service.form_memory(
            character_id="char_arjun",
            summary="Arjun remembers the informant's secret code 9412.",
            importance=0.95,
            emotional_weight=0.0,
            tags=["secret_code"],
        )

        # Maya retrieves memories
        maya_mems = service.retrieve_relevant_memories("char_maya", query="secret code")
        assert len(maya_mems) == 0

        # Arjun retrieves memories
        arjun_mems = service.retrieve_relevant_memories("char_arjun", query="secret code")
        assert len(arjun_mems) == 1
        assert "9412" in arjun_mems[0].summary

    def test_retrieval_scoring_formula(self):
        """Test that scoring correctly prioritizes relevance, importance, and recency"""
        world = create_demo_world()
        world.current_tick = 20
        service = MemoryService(world)

        # Low importance, old, irrelevant
        m_old = service.form_memory(
            character_id="char_arjun",
            summary="Drank coffee in the hotel lobby.",
            importance=0.1,
            emotional_weight=0.0,
            tags=["routine"],
        )
        # Manually backdate tick
        world.memories[m_old.id] = m_old.model_copy(update={"tick": 2})

        # High importance, relevant, recent
        m_critical = service.form_memory(
            character_id="char_arjun",
            summary="Found the corporate fraud documents with CEO signatures.",
            importance=0.95,
            emotional_weight=0.8,
            tags=["fraud", "ceo", "documents"],
        )
        world.memories[m_critical.id] = m_critical.model_copy(update={"tick": 19})

        # Retrieve with query "fraud documents"
        retrieved = service.retrieve_relevant_memories("char_arjun", query="fraud documents", limit=2)
        assert len(retrieved) == 2
        # Critical memory must be ranked first
        assert retrieved[0].id == m_critical.id
        assert "corporate fraud" in retrieved[0].summary

    def test_memory_compression(self):
        """Test compressing multiple older episodic memories into a single summary"""
        world = create_demo_world()
        world.current_tick = 25
        service = MemoryService(world)

        # Create 4 older memories for Maya
        for i in range(4):
            mem = service.form_memory(
                character_id="char_maya",
                summary=f"Checked hallway camera #{i} for security patrols.",
                importance=0.4,
                emotional_weight=-0.2,
                tags=["security"],
            )
            world.memories[mem.id] = mem.model_copy(update={"tick": i + 1})

        maya = world.characters["char_maya"]
        initial_mem_count = len(maya.memories)
        assert initial_mem_count >= 4

        # Compress memories older than 10 ticks
        summary = service.compress_old_memories("char_maya", older_than_ticks=10)
        assert summary is not None
        assert "compressed_summary" in summary.tags
        assert "Checked hallway camera" in summary.summary
        assert summary.tick == 25

        # Confirm character memory list is consolidated
        assert len(maya.memories) < initial_mem_count
        assert summary.id in maya.memories
