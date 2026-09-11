"""Tests for Milestone 11: Reflection System"""
import pytest
from src.demo_world import create_demo_world
from src.memory import MemoryService
from src.agents import ReflectionSystem, ReflectionResult


class TestReflectionSystem:
    """Tests for character reflection and cognitive synthesis"""

    def test_should_reflect_cadence(self):
        """Test reflection triggers only on cadence tick and with sufficient memories"""
        system = ReflectionSystem(cadence_ticks=5)

        # Tick 4 (not multiple of 5)
        assert system.should_reflect(current_tick=4, unreflected_memory_count=3) is False

        # Tick 5, but only 1 memory
        assert system.should_reflect(current_tick=5, unreflected_memory_count=1) is False

        # Tick 5 with 3 memories
        assert system.should_reflect(current_tick=5, unreflected_memory_count=3) is True

    def test_reflection_synthesizes_belief_without_altering_events(self):
        """Test reflection creates new character-owned belief without modifying objective history"""
        world = create_demo_world()
        memory_service = MemoryService(world)
        system = ReflectionSystem()

        # Seed memories for Arjun
        memory_service.form_memory("char_arjun", "Maya refused to show the project files.", 0.8, -0.3)
        memory_service.form_memory("char_arjun", "Maya gave an evasive answer about the CEO.", 0.85, -0.4)

        initial_event_count = len(world.events)
        initial_beliefs_count = len(world.characters["char_arjun"].beliefs)

        res = system.reflect_for_character(world, "char_arjun", memory_service)
        assert res is not None
        assert "Maya is deliberately withholding information" in res.insight

        # Check that a new belief was formed and attached to Arjun
        assert len(world.characters["char_arjun"].beliefs) == initial_beliefs_count + 1
        newest_belief_id = world.characters["char_arjun"].beliefs[-1]
        assert world.beliefs[newest_belief_id].statement == res.insight
        assert world.beliefs[newest_belief_id].source == "reflection"

        # Check objective history: event count must NOT be altered or rewritten
        assert len(world.events) == initial_event_count

    def test_reflection_emotional_shift(self):
        """Test that reflection insight applies bounded emotional shifts"""
        world = create_demo_world()
        memory_service = MemoryService(world)
        system = ReflectionSystem()

        memory_service.form_memory("char_maya", "Arjun brought up the CEO's secret meetings.", 0.9, -0.5)
        memory_service.form_memory("char_maya", "Arjun searched the desk area.", 0.7, -0.3)

        initial_fear = world.characters["char_maya"].emotional_state.fear
        system.reflect_for_character(world, "char_maya", memory_service)

        # Fear should increase from reflection insight
        assert world.characters["char_maya"].emotional_state.fear > initial_fear
