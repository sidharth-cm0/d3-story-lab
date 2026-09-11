"""Comprehensive quality pass tests for emergent behavior, goal-driven actions, and anti-repetition."""

import pytest
from src.demo_world import create_demo_world
from src.domain.action import ActionType
from src.domain.event import EventType
from src.simulation.orchestrator import SimulationOrchestrator
from src.generator.initializer import WorldInitializerService
from src.narrative.observer import Observer
from src.evaluation.metrics import NarrativeEvaluator
from src.providers.mock import MockLLMProvider


class TestEmergentBehaviorQualityPass:
    def test_15_tick_hotel_intrigue_emergent_trace(self):
        """Run 15 ticks on Hotel Intrigue and verify dynamic emergent behaviors."""
        world = create_demo_world()
        provider = MockLLMProvider()
        orchestrator = SimulationOrchestrator(world=world, provider=provider)

        # Run 15 ticks
        results = orchestrator.run(max_ticks=15)
        assert len(results) >= 15
        assert world.current_tick >= 10

        events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))
        assert len(events) >= 10

        # 1. At least one character-to-character interaction (SPEAK)
        dialogue_events = [e for e in events if e.event_type == EventType.CHARACTER_SPOKE]
        assert len(dialogue_events) >= 1, "Expected at least one character-to-character dialogue interaction"

        # 2. At least one object interaction (TAKE, DROP, OPEN, CLOSE, or INSPECT)
        object_events = [
            e for e in events
            if e.event_type in (EventType.OBJECT_PICKED_UP, EventType.OBJECT_DROPPED, EventType.DOOR_OPENED, EventType.DOOR_CLOSED, EventType.CHARACTER_OBSERVED)
            or "inspect" in e.description.lower()
            or "picked up" in e.description.lower()
        ]
        assert len(object_events) >= 1, "Expected at least one object interaction"

        # 3. At least one belief change
        assert len(world.beliefs) > 2, "Expected new beliefs to form during simulation"

        # 4. At least one relationship or emotional change
        maya = world.characters["char_maya"]
        arjun = world.characters["char_arjun"]
        maya_rel = world.get_relationship(maya.id, arjun.id)
        assert maya_rel is not None
        # Either trust has shifted or emotional state has shifted
        emotional_shift = (maya.emotional_state.trust != 0.4 or arjun.emotional_state.trust != 0.4 or maya.emotional_state.curiosity != 0.9 or arjun.emotional_state.fear != 0.6)
        assert emotional_shift, "Expected emotional or relationship evolution"

        # 5. No pathological repeated WAIT loop
        wait_events = [e for e in events if "waits" in e.description.lower()]
        wait_rate = len(wait_events) / len(events)
        assert wait_rate < 0.25, f"Pathological wait loop detected: wait rate is {wait_rate * 100:.1f}% >= 25%"

        # 6. Evaluation metrics verify high diversity and low repetition
        observer = Observer(provider=provider)
        selection = observer.observe_events(events, world)
        evaluator = NarrativeEvaluator()
        report = evaluator.evaluate_simulation(world, selection)

        assert report.action_diversity_score >= 0.45
        assert report.repeated_action_rate <= 0.20
        assert report.meaningful_interaction_count >= 10
        assert len(report.quality_warnings) == 0

    def test_arbitrary_initialized_scenario_no_passive_waiting(self):
        """Verify that arbitrary initialized characters (e.g. Morgan and Jordan) take active, goal-driven actions."""
        provider = MockLLMProvider()
        initializer = WorldInitializerService(provider=provider)

        # Seed with two characters
        seed = "In an embassy secure communications vault, defecting analyst Morgan confronts security officer Jordan over an encrypted ledger."
        plan = initializer.generate_plan(seed)
        world = initializer.instantiate_world(plan)

        orchestrator = SimulationOrchestrator(world=world, provider=provider)

        # Run 10 ticks
        results = orchestrator.run(max_ticks=10)
        assert len(results) >= 10

        events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

        # Check that characters did NOT default to passive waiting
        wait_events = [e for e in events if "waits" in e.description.lower()]
        wait_ratio = len(wait_events) / len(events)
        assert wait_ratio < 0.20, f"Arbitrary characters fell back to passive waiting: {wait_ratio * 100:.1f}%"

        # Both characters should have taken purposeful actions (speaking, inspecting, moving, or handling objects)
        actor_ids_active = {actor_id for e in events for actor_id in e.actor_ids}
        assert len(actor_ids_active) >= 2, "Both actors must be actively participating"

    def test_repetition_tracker_penalizes_consecutive_waits(self):
        """Test that RepetitionTracker applies severe penalties to consecutive WAITs."""
        from src.agents.repetition import RepetitionTracker

        tracker = RepetitionTracker()
        # Initially no penalty
        p0 = tracker.get_penalty("actor1", ActionType.WAIT)
        assert p0 == 0.4  # base penalty

        # Record a WAIT
        tracker.record_action("actor1", ActionType.WAIT)
        p1 = tracker.get_penalty("actor1", ActionType.WAIT)
        assert p1 > 1.0, f"Consecutive WAIT penalty should be high: {p1}"

        # Record a second WAIT
        tracker.record_action("actor1", ActionType.WAIT)
        p2 = tracker.get_penalty("actor1", ActionType.WAIT)
        assert p2 > 1.8, f"Two consecutive WAITs should be severely penalized: {p2}"

        # If non-wait action is recorded, wait penalty resets
        tracker.record_action("actor1", ActionType.SPEAK, target_id="actor2")
        p3 = tracker.get_penalty("actor1", ActionType.WAIT)
        assert p3 == 0.4
