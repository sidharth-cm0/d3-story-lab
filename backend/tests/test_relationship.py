"""Tests for Relationship domain model"""
import pytest
from pydantic import ValidationError
from src.domain import Relationship


class TestRelationship:
    """Tests for Relationship domain model"""

    def test_basic_relationship_creation(self):
        """Test creating a default relationship"""
        rel = Relationship(
            id="rel_001",
            character_a_id="char_001",
            character_b_id="char_002",
        )
        assert rel.id == "rel_001"
        assert rel.character_a_id == "char_001"
        assert rel.character_b_id == "char_002"
        assert rel.affinity == 0.0
        assert rel.trust == 0.0
        assert rel.history == ""

    def test_relationship_with_values(self):
        """Test creating a relationship with custom affinity, trust, and history"""
        rel = Relationship(
            id="rel_002",
            character_a_id="char_001",
            character_b_id="char_002",
            affinity=0.8,
            trust=0.6,
            history="Childhood friends",
        )
        assert rel.affinity == 0.8
        assert rel.trust == 0.6
        assert rel.history == "Childhood friends"

    def test_affinity_validation(self):
        """Test affinity range validation [-1.0, 1.0]"""
        # Valid boundaries
        Relationship(id="r1", character_a_id="a", character_b_id="b", affinity=-1.0)
        Relationship(id="r2", character_a_id="a", character_b_id="b", affinity=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            Relationship(id="r_bad", character_a_id="a", character_b_id="b", affinity=-1.1)

        with pytest.raises(ValidationError):
            Relationship(id="r_bad", character_a_id="a", character_b_id="b", affinity=1.1)

    def test_trust_validation(self):
        """Test trust range validation [-1.0, 1.0]"""
        # Valid boundaries
        Relationship(id="r1", character_a_id="a", character_b_id="b", trust=-1.0)
        Relationship(id="r2", character_a_id="a", character_b_id="b", trust=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            Relationship(id="r_bad", character_a_id="a", character_b_id="b", trust=-1.1)

        with pytest.raises(ValidationError):
            Relationship(id="r_bad", character_a_id="a", character_b_id="b", trust=1.1)

    def test_relationship_json_serialization(self):
        """Test JSON serialization and deserialization"""
        rel = Relationship(
            id="rel_json",
            character_a_id="char_a",
            character_b_id="char_b",
            affinity=-0.5,
            trust=0.2,
            history="Business rivals",
        )
        json_str = rel.model_dump_json()
        restored = Relationship.model_validate_json(json_str)
        assert restored.id == rel.id
        assert restored.affinity == -0.5
        assert restored.trust == 0.2
        assert restored.history == "Business rivals"
