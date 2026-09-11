"""Tests for demo world creation"""
import json
import pytest
from src.demo_world import create_demo_world


class TestDemoWorldCreation:
    """Tests for demo world factory"""

    def test_demo_world_creates_successfully(self):
        """Test that demo world can be created"""
        world = create_demo_world()
        assert world is not None
        assert world.id == "world_hotel_intrigue"

    def test_demo_world_has_locations(self):
        """Test that demo world has expected locations"""
        world = create_demo_world()
        assert len(world.locations) >= 2
        assert "loc_room307" in world.locations
        assert "loc_hallway" in world.locations

    def test_demo_world_room_307_details(self):
        """Test Hotel Room 307 details"""
        world = create_demo_world()
        room = world.locations["loc_room307"]
        assert room.name == "Hotel Room 307"
        assert "loc_hallway" in room.connected_locations

    def test_demo_world_has_characters(self):
        """Test that demo world has expected characters"""
        world = create_demo_world()
        assert len(world.characters) >= 2
        assert "char_arjun" in world.characters
        assert "char_maya" in world.characters

    def test_demo_world_arjun_details(self):
        """Test Arjun character details"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        assert arjun.name == "Arjun"
        assert arjun.role == "Corporate Investigator"
        assert arjun.current_location_id == "loc_room307"
        assert "ambitious" in arjun.personality_traits
        assert arjun.personality_traits["ambitious"] == 0.8

    def test_demo_world_maya_details(self):
        """Test Maya character details"""
        world = create_demo_world()
        maya = world.characters["char_maya"]
        assert maya.name == "Maya"
        assert maya.role == "Corporate Attorney"
        assert maya.current_location_id == "loc_room307"

    def test_demo_world_emotional_states(self):
        """Test that characters have emotional states"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        maya = world.characters["char_maya"]

        assert arjun.emotional_state.curiosity > 0.8
        assert maya.emotional_state.fear > 0.6

    def test_demo_world_has_objects(self):
        """Test that demo world has expected objects"""
        world = create_demo_world()
        assert len(world.objects) >= 4
        assert "obj_documents" in world.objects
        assert "obj_phone" in world.objects
        assert "obj_suitcase" in world.objects
        assert "obj_door" in world.objects

    def test_demo_world_documents_object(self):
        """Test documents object properties"""
        world = create_demo_world()
        docs = world.objects["obj_documents"]
        assert docs.name == "Documents"
        assert docs.location_id == "loc_room307"
        assert docs.portable is True
        assert docs.properties["sensitive"] == "true"

    def test_demo_world_door_object(self):
        """Test door object properties"""
        world = create_demo_world()
        door = world.objects["obj_door"]
        assert door.name == "Door"
        assert door.portable is False

    def test_demo_world_has_goals(self):
        """Test that characters have goals"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        maya = world.characters["char_maya"]

        assert len(arjun.goals) >= 1
        assert len(maya.goals) >= 1

    def test_demo_world_has_beliefs(self):
        """Test that characters have beliefs"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        maya = world.characters["char_maya"]

        assert len(arjun.beliefs) >= 1
        assert len(maya.beliefs) >= 1

    def test_demo_world_has_secrets(self):
        """Test that characters have secrets"""
        world = create_demo_world()
        maya = world.characters["char_maya"]
        assert len(maya.secrets) >= 1

    def test_demo_world_has_relationships(self):
        """Test that characters have relationships"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        maya = world.characters["char_maya"]

        assert len(arjun.relationships) >= 1
        assert len(maya.relationships) >= 1

    def test_demo_world_entities_stored_in_world(self):
        """Test that all created entities are canonically stored in WorldState"""
        world = create_demo_world()
        # Goals
        assert "goal_arjun_001" in world.goals
        assert "goal_maya_001" in world.goals
        assert world.goals["goal_arjun_001"].character_id == "char_arjun"
        assert world.goals["goal_maya_001"].character_id == "char_maya"

        # Beliefs
        assert "bel_arjun_001" in world.beliefs
        assert "bel_maya_001" in world.beliefs
        assert world.beliefs["bel_arjun_001"].confidence == 0.85
        assert world.beliefs["bel_maya_001"].confidence == 0.9

        # Secrets
        assert "sec_maya_001" in world.secrets
        assert world.secrets["sec_maya_001"].importance == 1.0

        # Relationships
        assert "rel_001" in world.relationships
        assert world.relationships["rel_001"].character_a_id == "char_arjun"
        assert world.relationships["rel_001"].character_b_id == "char_maya"

    def test_demo_world_character_entity_resolution(self):
        """Test that character entities can be resolved from WorldState by ID"""
        world = create_demo_world()

        arjun_goals = world.get_character_goals("char_arjun")
        assert len(arjun_goals) == 1
        assert arjun_goals[0].id == "goal_arjun_001"

        maya_secrets = world.get_character_secrets("char_maya")
        assert len(maya_secrets) == 1
        assert maya_secrets[0].id == "sec_maya_001"

        arjun_beliefs = world.get_character_beliefs("char_arjun")
        assert len(arjun_beliefs) == 1
        assert arjun_beliefs[0].id == "bel_arjun_001"

        arjun_rels = world.get_character_relationships("char_arjun")
        assert len(arjun_rels) == 1
        assert arjun_rels[0].id == "rel_001"

    def test_demo_world_json_serialization(self):
        """Test that demo world can be serialized to JSON"""
        world = create_demo_world()
        json_str = world.model_dump_json()
        assert isinstance(json_str, str)

        # Parse and verify structure
        parsed = json.loads(json_str)
        assert parsed["id"] == "world_hotel_intrigue"
        assert len(parsed["locations"]) >= 2
        assert len(parsed["characters"]) >= 2
        assert len(parsed["objects"]) >= 4
        assert len(parsed["goals"]) >= 2
        assert len(parsed["beliefs"]) >= 2
        assert len(parsed["secrets"]) >= 1
        assert len(parsed["relationships"]) >= 1

    def test_demo_world_json_round_trip(self):
        """Test that demo world survives JSON round-trip and all references resolve"""
        world = create_demo_world()
        json_str = world.model_dump_json()
        world_restored = world.__class__.model_validate_json(json_str)

        assert world_restored.id == world.id
        assert len(world_restored.locations) == len(world.locations)
        assert len(world_restored.characters) == len(world.characters)
        assert len(world_restored.objects) == len(world.objects)
        assert len(world_restored.goals) == len(world.goals)
        assert len(world_restored.beliefs) == len(world.beliefs)
        assert len(world_restored.secrets) == len(world.secrets)
        assert len(world_restored.relationships) == len(world.relationships)

        # Verify character data integrity
        arjun_restored = world_restored.characters["char_arjun"]
        arjun_original = world.characters["char_arjun"]
        assert arjun_restored.name == arjun_original.name
        assert arjun_restored.personality_traits == arjun_original.personality_traits

        # Verify resolution on restored world
        assert world_restored.validate_references() == []
        goals = world_restored.get_character_goals("char_arjun")
        assert len(goals) == 1
        assert goals[0].description == "Recover and verify the confidential documents"

        secrets = world_restored.get_character_secrets("char_maya")
        assert len(secrets) == 1
        assert secrets[0].statement == "The documents contain evidence of corporate fraud that implicates the CEO"


class TestDemoWorldConsistency:
    """Tests for demo world internal consistency"""

    def test_demo_world_has_no_dangling_references(self):
        """Test that demo world has zero dangling references across all entities"""
        world = create_demo_world()
        dangling_errors = world.validate_references()
        assert dangling_errors == [], f"Dangling references found: {dangling_errors}"

    def test_character_locations_exist(self):
        """Test that all character locations exist in world"""
        world = create_demo_world()
        for char in world.characters.values():
            if char.current_location_id:
                assert (
                    char.current_location_id in world.locations
                ), f"Character {char.id} references non-existent location {char.current_location_id}"

    def test_character_goals_exist_in_world(self):
        """Test that all character goals exist in canonical world state"""
        world = create_demo_world()
        for char in world.characters.values():
            for gid in char.goals:
                assert gid in world.goals, f"Goal {gid} not in world.goals"

    def test_character_beliefs_exist_in_world(self):
        """Test that all character beliefs exist in canonical world state"""
        world = create_demo_world()
        for char in world.characters.values():
            for bid in char.beliefs:
                assert bid in world.beliefs, f"Belief {bid} not in world.beliefs"

    def test_character_secrets_exist_in_world(self):
        """Test that all character secrets exist in canonical world state"""
        world = create_demo_world()
        for char in world.characters.values():
            for sid in char.secrets:
                assert sid in world.secrets, f"Secret {sid} not in world.secrets"

    def test_character_relationships_exist_in_world(self):
        """Test that all character relationships exist in canonical world state"""
        world = create_demo_world()
        for char in world.characters.values():
            for rid in char.relationships:
                assert rid in world.relationships, f"Relationship {rid} not in world.relationships"

    def test_object_locations_exist(self):
        """Test that all object locations exist in world"""
        world = create_demo_world()
        for obj in world.objects.values():
            if obj.location_id:
                assert (
                    obj.location_id in world.locations
                ), f"Object {obj.id} references non-existent location {obj.location_id}"

    def test_mutual_relationships(self):
        """Test that relationships are properly set for both characters"""
        world = create_demo_world()
        arjun = world.characters["char_arjun"]
        maya = world.characters["char_maya"]

        # Both should have the same relationship ID
        assert len(arjun.relationships) > 0
        assert len(maya.relationships) > 0
