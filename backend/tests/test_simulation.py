"""Tests for SimulationClock and SimulationTick domain models"""
import pytest
from pydantic import ValidationError
from src.domain import SimulationClock, SimulationTick


class TestSimulationClock:
    """Tests for SimulationClock functionality"""

    def test_initial_state(self):
        """Test initial clock state at creation"""
        clock = SimulationClock()
        assert clock.current_tick == 0
        assert clock.total_ticks == 0

    def test_one_advance(self):
        """Test advancing the clock once"""
        clock = SimulationClock()
        tick = clock.advance()

        assert clock.current_tick == 1
        assert clock.total_ticks == 1
        assert isinstance(tick, SimulationTick)
        assert tick.tick == 1

    def test_multiple_advances(self):
        """Test advancing the clock multiple times"""
        clock = SimulationClock()
        for expected_tick in range(1, 6):
            tick = clock.advance()
            assert clock.current_tick == expected_tick
            assert clock.total_ticks == expected_tick
            assert tick.tick == expected_tick

        assert clock.current_tick == 5
        assert clock.total_ticks == 5

    def test_reset(self):
        """Test resetting the clock"""
        clock = SimulationClock()
        clock.advance()
        clock.advance()
        clock.advance()
        assert clock.current_tick == 3
        assert clock.total_ticks == 3

        clock.reset()
        assert clock.current_tick == 0
        assert clock.total_ticks == 0

    def test_negative_tick_validation(self):
        """Test that negative tick values are rejected"""
        with pytest.raises(ValidationError):
            SimulationClock(current_tick=-1)

        with pytest.raises(ValidationError):
            SimulationClock(total_ticks=-1)


class TestSimulationTick:
    """Tests for SimulationTick model"""

    def test_tick_creation(self):
        """Test creating a tick instance"""
        tick = SimulationTick(tick=42, timestamp="2026-09-11T10:00:00Z")
        assert tick.tick == 42
        assert tick.timestamp == "2026-09-11T10:00:00Z"

    def test_tick_negative_validation(self):
        """Test that negative tick value raises ValidationError"""
        with pytest.raises(ValidationError):
            SimulationTick(tick=-1)
