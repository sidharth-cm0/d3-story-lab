"""Tests for Milestone 9: Director Agent"""
import pytest
from src.demo_world import create_demo_world
from src.domain import EventType
from src.agents.director import DirectorAgent, DirectorInterventionType
from src.simulation import EventRecorder


class TestDirectorAgent:
    """Tests verifying Director pacing oversight and external event injection"""

    def test_director_does_not_intervene_when_active(self):
        """Test Director remains passive when scene activity is healthy"""
        world = create_demo_world()
        director = DirectorAgent(inactivity_threshold=3)

        intervention = director.evaluate_pacing(world, inactivity_count=1)
        assert intervention is None

    def test_director_injects_knock_on_inactivity(self):
        """Test Director injects an external event when inactivity threshold is reached"""
        world = create_demo_world()
        recorder = EventRecorder(world)
        director = DirectorAgent(inactivity_threshold=2)

        intervention = director.evaluate_pacing(world, inactivity_count=2)
        assert intervention is not None
        assert intervention.intervention_type == DirectorInterventionType.KNOCK_ON_DOOR

        # Inject intervention
        event = director.inject_intervention(world, recorder, intervention)
        assert event.id in world.events
        assert event.actor_ids == []  # External environmental event
        assert "sharp, insistent knock" in event.description
        assert event.metadata.get("director_intervention") == "knock_on_door"

    def test_director_preserves_character_autonomy(self):
        """Test Director never touches character private state or dictates dialogue"""
        world = create_demo_world()
        recorder = EventRecorder(world)
        director = DirectorAgent()

        initial_arjun_goals = list(world.characters["char_arjun"].goals)
        initial_maya_secrets = list(world.characters["char_maya"].secrets)

        intervention = director.evaluate_pacing(world, inactivity_count=3)
        assert intervention is not None
        director.inject_intervention(world, recorder, intervention)

        # Character inner states must remain completely un-tampered
        assert world.characters["char_arjun"].goals == initial_arjun_goals
        assert world.characters["char_maya"].secrets == initial_maya_secrets
