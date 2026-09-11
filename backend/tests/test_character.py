"""Tests for Character domain model"""
import pytest
from pydantic import ValidationError
from src.domain import Character, EmotionalState


class TestCharacterCreation:
    """Tests for Character creation"""

    def test_basic_character_creation(self):
        """Test creating a basic character"""
        char = Character(
            id="char_001",
            name="Alice",
            role="Detective",
        )
        assert char.id == "char_001"
        assert char.name == "Alice"
        assert char.role == "Detective"
        assert len(char.goals) == 0
        assert len(char.beliefs) == 0

    def test_character_with_all_fields(self):
        """Test creating a character with all fields"""
        emotion = EmotionalState(
            happiness=0.5,
            fear=0.3,
            anger=0.2,
            trust=0.6,
            curiosity=0.8,
        )
        char = Character(
            id="char_001",
            name="Bob",
            role="Investigator",
            description="An experienced investigator",
            personality_traits={"ambitious": 0.8, "loyal": 0.7, "cautious": 0.6},
            emotional_state=emotion,
            current_location_id="loc_001",
            goals=["goal_001"],
            beliefs=["bel_001"],
            secrets=["sec_001"],
            memories=["mem_001"],
            relationships=["rel_001"],
            inventory=["obj_001"],
        )
        assert char.name == "Bob"
        assert len(char.personality_traits) == 3
        assert char.personality_traits["ambitious"] == 0.8
        assert char.current_location_id == "loc_001"
        assert len(char.goals) == 1
        assert len(char.inventory) == 1

    def test_character_default_emotional_state(self):
        """Test that character has default emotional state"""
        char = Character(id="char_001", name="Charlie", role="Actor")
        assert char.emotional_state is not None
        assert isinstance(char.emotional_state, EmotionalState)
        assert char.emotional_state.happiness == 0.0

    def test_character_empty_inventory(self):
        """Test character with empty inventory"""
        char = Character(id="char_001", name="Dave", role="Worker")
        assert len(char.inventory) == 0

    def test_character_personality_traits_range(self):
        """Test that personality traits can be any value"""
        char = Character(
            id="char_001",
            name="Eve",
            role="Thinker",
            personality_traits={
                "very_ambitious": 0.95,
                "not_ambitious": 0.05,
                "moderately_ambitious": 0.5,
            },
        )
        assert char.personality_traits["very_ambitious"] == 0.95
        assert char.personality_traits["not_ambitious"] == 0.05

    def test_character_json_serialization(self):
        """Test character JSON serialization"""
        char = Character(
            id="char_001",
            name="Frank",
            role="Engineer",
            personality_traits={"creative": 0.8},
        )
        json_str = char.model_dump_json()
        assert isinstance(json_str, str)
        restored = Character.model_validate_json(json_str)
        assert restored.id == "char_001"
        assert restored.name == "Frank"
        assert restored.personality_traits["creative"] == 0.8


class TestCharacterLocationTracking:
    """Tests for tracking character location"""

    def test_character_location_tracking(self):
        """Test that character location can be set and retrieved"""
        char = Character(
            id="char_001",
            name="Grace",
            role="Explorer",
            current_location_id="loc_start",
        )
        assert char.current_location_id == "loc_start"

        # Update location
        char.current_location_id = "loc_end"
        assert char.current_location_id == "loc_end"

    def test_character_no_location(self):
        """Test character with no location"""
        char = Character(id="char_001", name="Henry", role="Ghost")
        assert char.current_location_id is None


class TestCharacterRelationships:
    """Tests for character relationships"""

    def test_character_multiple_relationships(self):
        """Test character with multiple relationships"""
        char = Character(
            id="char_001",
            name="Iris",
            role="Connector",
            relationships=["rel_001", "rel_002", "rel_003"],
        )
        assert len(char.relationships) == 3
        assert "rel_002" in char.relationships
