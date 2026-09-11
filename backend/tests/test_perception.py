"""Tests for Milestone 3: Perception and Knowledge Boundaries"""
import pytest
from src.demo_world import create_demo_world
from src.domain import Event, EventType
from src.simulation import KnowledgeFilter, EventRecorder


class TestKnowledgeFilterPrivacy:
    """Tests proving strict knowledge partition and perception boundaries"""

    def test_maya_cannot_see_arjun_private_state(self):
        """Test that Maya's observation does not leak Arjun's secrets, beliefs, or goals"""
        world = create_demo_world()
        obs = KnowledgeFilter.build_observation(world, "char_maya")

        # Arjun is co-located in room 307
        assert len(obs.visible_characters) == 1
        vis_arjun = obs.visible_characters[0]
        assert vis_arjun.id == "char_arjun"
        assert vis_arjun.name == "Arjun"

        # Check that vis_arjun has NO secret/belief/memory/goal fields
        assert not hasattr(vis_arjun, "secrets")
        assert not hasattr(vis_arjun, "beliefs")
        assert not hasattr(vis_arjun, "memories")
        assert not hasattr(vis_arjun, "goals")

        # Verify observation dict does not contain Arjun's secrets
        dumped = obs.model_dump()
        dumped_str = str(dumped)
        assert "bel_arjun_001" not in dumped_str
        assert "goal_arjun_001" not in dumped_str

    def test_arjun_cannot_see_maya_private_secrets(self):
        """Test that Arjun cannot observe Maya's private secrets or confidential beliefs"""
        world = create_demo_world()
        obs = KnowledgeFilter.build_observation(world, "char_arjun")

        assert len(obs.visible_characters) == 1
        vis_maya = obs.visible_characters[0]
        assert vis_maya.id == "char_maya"

        # Ensure Maya's corporate fraud secret is strictly absent
        dumped_str = str(obs.model_dump())
        assert "sec_maya_001" not in dumped_str
        assert "corporate fraud that implicates the CEO" not in dumped_str

    def test_actors_cannot_observe_events_in_inaccessible_locations(self):
        """Test that events occurring in other rooms are not perceivable"""
        world = create_demo_world()
        recorder = EventRecorder(world)

        # Move Arjun to the hallway
        world.characters["char_arjun"].current_location_id = "loc_hallway"

        # Log an event inside Room 307 (only Maya is there)
        recorder.record_event(
            event_type=EventType.CHARACTER_SPOKE,
            actor_ids=["char_maya"],
            location_id="loc_room307",
            description="Maya whispers a secret phone call.",
        )

        # Log an event in the Hallway (Arjun is there)
        recorder.record_event(
            event_type=EventType.OTHER,
            actor_ids=["char_arjun"],
            location_id="loc_hallway",
            description="Arjun checks his watch in the hallway.",
        )

        arjun_obs = KnowledgeFilter.build_observation(world, "char_arjun")
        arjun_event_descs = [e.description for e in arjun_obs.recent_events]

        assert "Arjun checks his watch in the hallway." in arjun_event_descs
        assert "Maya whispers a secret phone call." not in arjun_event_descs

    def test_co_located_objects_perceived(self):
        """Test that co-located objects are visible, but objects in other rooms are not"""
        world = create_demo_world()

        # Arjun and Maya in Room 307
        obs = KnowledgeFilter.build_observation(world, "char_arjun")
        visible_obj_ids = [o.id for o in obs.visible_objects]
        assert "obj_documents" in visible_obj_ids
        assert "obj_phone" in visible_obj_ids

        # Move phone to Hallway
        world.objects["obj_phone"].location_id = "loc_hallway"
        obs_after = KnowledgeFilter.build_observation(world, "char_arjun")
        visible_after_ids = [o.id for o in obs_after.visible_objects]
        assert "obj_phone" not in visible_after_ids
        assert "obj_documents" in visible_after_ids
