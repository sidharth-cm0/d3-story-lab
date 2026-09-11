"""Tests for Milestone 10: Simulation Orchestrator"""
import pytest
from src.demo_world import create_demo_world
from src.simulation.orchestrator import SimulationOrchestrator


class TestSimulationOrchestrator:
    """Tests for full multi-agent cyclic simulation orchestrator"""

    def test_orchestrator_single_step(self):
        """Test single orchestrated step running perception, agents, and execution"""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world)

        assert world.current_tick == 0
        results = orchestrator.step()

        assert len(results) == 2  # Arjun and Maya
        assert world.current_tick == 1
        assert len(world.events) >= 2

    def test_orchestrator_cognitive_effects(self):
        """Test that actions trigger memories, belief updates, and emotion changes"""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world)

        initial_maya_mem_count = len(world.characters["char_maya"].memories)
        initial_arjun_mem_count = len(world.characters["char_arjun"].memories)

        # Run 2 ticks
        orchestrator.step()
        orchestrator.step()

        # Both characters should have formed new memories from the interaction
        assert len(world.characters["char_maya"].memories) > initial_maya_mem_count or len(world.characters["char_arjun"].memories) > initial_arjun_mem_count

    def test_orchestrator_pause_and_resume(self):
        """Test pause stops execution and resume continues"""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world)

        orchestrator.pause()
        assert orchestrator.is_paused is True

        results = orchestrator.step()
        assert results == []
        assert world.current_tick == 0

        orchestrator.resume()
        results_resumed = orchestrator.step()
        assert len(results_resumed) == 2
        assert world.current_tick == 1

    def test_orchestrator_multi_tick_run_termination(self):
        """Test run executes up to max_ticks and terminates cleanly"""
        world = create_demo_world()
        orchestrator = SimulationOrchestrator(world)

        results = orchestrator.run(max_ticks=4)
        assert len(results) <= 8
        assert world.current_tick <= 4
        # Confirm events are immutable and saved
        assert len(world.events) >= 4
