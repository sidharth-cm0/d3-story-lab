"""Tests for WorldState and JSON serialization"""
import json
import pytest
from src.domain import WorldState, Location, Character, EmotionalState, WorldObject


def test_world_state_creation():
    """Test basic WorldState creation"""
    world = WorldState(
        id="world_001",
        name="Test World",
        description="A test world",
    )
    assert world.id == "world_001"
    assert world.name == "Test World"
    assert world.current_tick == 0
    assert len(world.locations) == 0
    assert len(world.characters) == 0


def test_world_state_json_serialization():
    """Test that WorldState can be serialized to JSON and back"""
    world = WorldState(
        id="world_001",
        name="Test World",
    )

    # Add a location
    location = Location(
        id="loc_001",
        name="Test Location",
    )
    world.locations["loc_001"] = location

    # Add a character
    character = Character(
        id="char_001",
        name="Test Character",
        role="Tester",
    )
    world.characters["char_001"] = character

    # Serialize to JSON
    json_str = world.model_dump_json()
    assert isinstance(json_str, str)

    # Parse back from JSON
    parsed_json = json.loads(json_str)
    assert parsed_json["id"] == "world_001"
    assert parsed_json["name"] == "Test World"

    # Deserialize back to object
    world_restored = WorldState.model_validate_json(json_str)
    assert world_restored.id == world.id
    assert world_restored.name == world.name
    assert len(world_restored.locations) == 1
    assert len(world_restored.characters) == 1


def test_world_state_empty_serialization():
    """Test serialization of empty WorldState"""
    world = WorldState(id="empty_world", name="Empty")
    json_str = world.model_dump_json()
    world_restored = WorldState.model_validate_json(json_str)
    assert world_restored.id == "empty_world"
    assert world_restored.name == "Empty"
    assert world_restored.current_tick == 0


def test_world_state_complex_serialization():
    """Test serialization with nested objects"""
    world = WorldState(id="complex_world", name="Complex World", current_tick=5)

    location = Location(
        id="loc_001", name="Room", connected_locations=["loc_002"]
    )
    world.locations["loc_001"] = location

    world_object = WorldObject(
        id="obj_001",
        name="Sword",
        location_id="loc_001",
        portable=True,
        properties={"material": "steel", "damage": "10"},
    )
    world.objects["obj_001"] = world_object

    # Serialize and deserialize
    json_str = world.model_dump_json()
    world_restored = WorldState.model_validate_json(json_str)

    assert world_restored.current_tick == 5
    assert "loc_001" in world_restored.locations
    assert "obj_001" in world_restored.objects
    assert world_restored.objects["obj_001"].properties["material"] == "steel"


def test_world_state_all_registries_initialized():
    """Test that all canonical registries are initialized as empty dicts"""
    world = WorldState(id="world_reg", name="Registry Test")
    assert isinstance(world.locations, dict)
    assert isinstance(world.characters, dict)
    assert isinstance(world.objects, dict)
    assert isinstance(world.goals, dict)
    assert isinstance(world.beliefs, dict)
    assert isinstance(world.secrets, dict)
    assert isinstance(world.relationships, dict)
    assert isinstance(world.memories, dict)
    assert isinstance(world.events, dict)


def test_world_state_reference_validation_clean():
    """Test validate_references passes on a fully consistent world"""
    world = WorldState(id="world_valid", name="Valid World")
    loc = Location(id="loc_1", name="Room 1", connected_locations=["loc_2"])
    loc2 = Location(id="loc_2", name="Room 2", connected_locations=["loc_1"])
    world.locations["loc_1"] = loc
    world.locations["loc_2"] = loc2

    from src.domain import Goal, Belief, Secret, Relationship, Memory
    char = Character(
        id="char_1",
        name="Alice",
        role="Agent",
        current_location_id="loc_1",
        goals=["goal_1"],
        beliefs=["bel_1"],
        secrets=["sec_1"],
        memories=["mem_1"],
        relationships=["rel_1"],
        inventory=["obj_1"],
    )
    char2 = Character(id="char_2", name="Bob", role="Target", current_location_id="loc_2")
    world.characters["char_1"] = char
    world.characters["char_2"] = char2

    obj = WorldObject(id="obj_1", name="Key", location_id="loc_1", holder_id="char_1")
    world.objects["obj_1"] = obj

    world.goals["goal_1"] = Goal(id="goal_1", character_id="char_1", description="Find Bob")
    world.beliefs["bel_1"] = Belief(id="bel_1", character_id="char_1", statement="Bob is in Room 2", confidence=0.9)
    world.secrets["sec_1"] = Secret(id="sec_1", character_id="char_1", statement="Classified")
    world.memories["mem_1"] = Memory(id="mem_1", character_id="char_1", summary="Saw Bob", importance=0.8, emotional_weight=0.1, tick=0)
    world.relationships["rel_1"] = Relationship(id="rel_1", character_a_id="char_1", character_b_id="char_2")

    assert world.validate_references() == []

    # Test resolution helpers
    assert len(world.get_character_goals("char_1")) == 1
    assert world.get_character_goals("char_1")[0].description == "Find Bob"
    assert len(world.get_character_beliefs("char_1")) == 1
    assert len(world.get_character_secrets("char_1")) == 1
    assert len(world.get_character_memories("char_1")) == 1
    assert len(world.get_character_relationships("char_1")) == 1
    assert world.get_character_goals("nonexistent") == []


def test_world_state_reference_validation_detects_dangling():
    """Test validate_references detects dangling IDs"""
    world = WorldState(id="world_broken", name="Broken World")
    # Character with dangling references
    char = Character(
        id="char_bad",
        name="Ghost",
        role="Specter",
        current_location_id="loc_missing",
        goals=["goal_missing"],
        beliefs=["bel_missing"],
        secrets=["sec_missing"],
        memories=["mem_missing"],
        relationships=["rel_missing"],
        inventory=["obj_missing"],
    )
    world.characters["char_bad"] = char

    errors = world.validate_references()
    assert len(errors) == 7
    assert any("location 'loc_missing'" in e for e in errors)
    assert any("goal 'goal_missing'" in e for e in errors)
    assert any("belief 'bel_missing'" in e for e in errors)
    assert any("secret 'sec_missing'" in e for e in errors)
    assert any("memory 'mem_missing'" in e for e in errors)
    assert any("relationship 'rel_missing'" in e for e in errors)
    assert any("object 'obj_missing'" in e for e in errors)
