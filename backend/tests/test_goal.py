"""Tests for Goal domain model"""
import pytest
from pydantic import ValidationError
from src.domain import Goal, GoalStatus


class TestGoal:
    """Tests for Goal domain model"""

    def test_basic_goal_creation(self):
        """Test creating a basic goal"""
        goal = Goal(
            id="goal_001",
            character_id="char_001",
            description="Find the lost documents",
        )
        assert goal.id == "goal_001"
        assert goal.character_id == "char_001"
        assert goal.description == "Find the lost documents"
        assert goal.priority == 0.5
        assert goal.status == GoalStatus.ACTIVE
        assert goal.reason is None

    def test_goal_with_all_fields(self):
        """Test creating a goal with all fields specified"""
        goal = Goal(
            id="goal_002",
            character_id="char_002",
            description="Expose the corruption",
            priority=0.95,
            status=GoalStatus.COMPLETED,
            reason="Justice must prevail",
        )
        assert goal.priority == 0.95
        assert goal.status == GoalStatus.COMPLETED
        assert goal.reason == "Justice must prevail"

    def test_goal_status_values(self):
        """Test that all GoalStatus enum values work"""
        for status in [
            GoalStatus.ACTIVE,
            GoalStatus.COMPLETED,
            GoalStatus.ABANDONED,
            GoalStatus.FAILED,
        ]:
            goal = Goal(
                id=f"goal_{status.value}",
                character_id="char_001",
                description="Status test",
                status=status,
            )
            assert goal.status == status

    def test_priority_validation(self):
        """Test priority range validation [0.0, 1.0]"""
        # Valid boundary values
        Goal(id="g1", character_id="c1", description="d", priority=0.0)
        Goal(id="g2", character_id="c1", description="d", priority=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            Goal(id="g_invalid", character_id="c1", description="d", priority=-0.1)

        with pytest.raises(ValidationError):
            Goal(id="g_invalid", character_id="c1", description="d", priority=1.1)

    def test_goal_json_serialization(self):
        """Test JSON serialization and deserialization"""
        goal = Goal(
            id="goal_json",
            character_id="char_json",
            description="Serialize me",
            priority=0.8,
            status=GoalStatus.ACTIVE,
            reason="Testing",
        )
        json_str = goal.model_dump_json()
        restored = Goal.model_validate_json(json_str)
        assert restored.id == goal.id
        assert restored.priority == 0.8
        assert restored.status == GoalStatus.ACTIVE
        assert restored.reason == "Testing"
