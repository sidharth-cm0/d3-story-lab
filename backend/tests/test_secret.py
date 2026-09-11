"""Tests for Secret domain model"""
import pytest
from pydantic import ValidationError
from src.domain import Secret


class TestSecret:
    """Tests for Secret domain model"""

    def test_basic_secret_creation(self):
        """Test creating a basic secret"""
        secret = Secret(
            id="sec_001",
            character_id="char_001",
            statement="There is a hidden safe behind the painting",
        )
        assert secret.id == "sec_001"
        assert secret.character_id == "char_001"
        assert secret.statement == "There is a hidden safe behind the painting"
        assert secret.known_by == []
        assert secret.importance == 0.5

    def test_secret_with_known_by(self):
        """Test secret with other characters who know it"""
        secret = Secret(
            id="sec_002",
            character_id="char_001",
            statement="Shared secret",
            known_by=["char_002", "char_003"],
            importance=0.9,
        )
        assert len(secret.known_by) == 2
        assert "char_002" in secret.known_by
        assert secret.importance == 0.9

    def test_secret_importance_validation(self):
        """Test importance range validation [0.0, 1.0]"""
        # Valid boundaries
        Secret(id="s1", character_id="c1", statement="t", importance=0.0)
        Secret(id="s2", character_id="c1", statement="t", importance=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            Secret(id="s_bad", character_id="c1", statement="t", importance=-0.1)

        with pytest.raises(ValidationError):
            Secret(id="s_bad", character_id="c1", statement="t", importance=1.1)

    def test_secret_json_serialization(self):
        """Test JSON serialization and deserialization"""
        secret = Secret(
            id="sec_json",
            character_id="char_001",
            statement="Test secret",
            known_by=["char_002"],
            importance=0.75,
        )
        json_str = secret.model_dump_json()
        restored = Secret.model_validate_json(json_str)
        assert restored.id == secret.id
        assert restored.statement == secret.statement
        assert restored.known_by == ["char_002"]
        assert restored.importance == 0.75
