"""Tests for ActionProposal and ActionResult domain models"""
import pytest
from pydantic import ValidationError
from src.domain import (
    ActionProposal,
    ActionResult,
    ActionType,
    ActionResultStatus,
    Motivation,
)


class TestActionProposal:
    """Tests for ActionProposal domain model"""

    def test_basic_action_proposal(self):
        """Test creating a basic action proposal"""
        proposal = ActionProposal(
            id="act_001",
            actor_id="char_arjun",
            action_type=ActionType.MOVE,
            tick_proposed=1,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_1"),
        )
        assert proposal.id == "act_001"
        assert proposal.actor_id == "char_arjun"
        assert proposal.action_type == ActionType.MOVE
        assert proposal.tick_proposed == 1
        assert proposal.target_id is None
        assert proposal.location_id is None
        assert proposal.parameters == {}
        assert proposal.reason is None
        assert proposal.motivation.kind == "PURSUE_GOAL"

    def test_all_action_types(self):
        """Test that all ActionType enum values can be used"""
        for action_type in [
            ActionType.MOVE,
            ActionType.PICKUP,
            ActionType.DROP,
            ActionType.GIVE,
            ActionType.SPEAK,
            ActionType.OBSERVE,
            ActionType.OPEN_DOOR,
            ActionType.CLOSE_DOOR,
            ActionType.OTHER,
        ]:
            proposal = ActionProposal(
                id=f"act_{action_type.value}",
                actor_id="char_001",
                action_type=action_type,
                tick_proposed=0,
                motivation=Motivation(kind="PURSUE_GOAL"),
            )
            assert proposal.action_type == action_type

    def test_action_proposal_with_all_fields(self):
        """Test action proposal with target, location, parameters, reason"""
        proposal = ActionProposal(
            id="act_full",
            actor_id="char_001",
            action_type=ActionType.GIVE,
            target_id="char_002",
            location_id="loc_001",
            parameters={"item_id": "obj_001"},
            tick_proposed=3,
            motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_trust"),
            reason="Build trust",
        )
        assert proposal.target_id == "char_002"
        assert proposal.location_id == "loc_001"
        assert proposal.parameters["item_id"] == "obj_001"
        assert proposal.reason == "Build trust"

    def test_action_proposal_negative_tick(self):
        """Test that negative tick raises ValidationError"""
        with pytest.raises(ValidationError):
            ActionProposal(
                id="act_bad",
                actor_id="c1",
                action_type=ActionType.MOVE,
                tick_proposed=-1,
                motivation=Motivation(kind="PURSUE_GOAL"),
            )

    def test_action_proposal_requires_motivation(self):
        """Test that ActionProposal cannot be constructed without motivation"""
        with pytest.raises(ValidationError):
            ActionProposal(
                id="act_no_mot",
                actor_id="char_001",
                action_type=ActionType.MOVE,
                tick_proposed=1,
            )


class TestActionResult:
    """Tests for ActionResult domain model"""

    def test_successful_action_result(self):
        """Test creating a successful action result"""
        result = ActionResult(
            proposal_id="act_001",
            status=ActionResultStatus.SUCCESS,
            tick_resolved=1,
            events_created=["evt_001"],
        )
        assert result.proposal_id == "act_001"
        assert result.status == ActionResultStatus.SUCCESS
        assert result.tick_resolved == 1
        assert result.events_created == ["evt_001"]
        assert result.error_message is None

    def test_all_result_statuses(self):
        """Test that all ActionResultStatus enum values can be used"""
        for status in [
            ActionResultStatus.SUCCESS,
            ActionResultStatus.FAILED,
            ActionResultStatus.BLOCKED,
            ActionResultStatus.INVALID,
        ]:
            result = ActionResult(
                proposal_id="act_001",
                status=status,
                tick_resolved=0,
            )
            assert result.status == status

    def test_failed_action_result_with_error(self):
        """Test creating a failed action result with error message"""
        result = ActionResult(
            proposal_id="act_002",
            status=ActionResultStatus.FAILED,
            tick_resolved=2,
            error_message="Door is locked",
        )
        assert result.status == ActionResultStatus.FAILED
        assert result.error_message == "Door is locked"

    def test_action_result_json_serialization(self):
        """Test JSON round trip for ActionResult"""
        result = ActionResult(
            proposal_id="act_json",
            status=ActionResultStatus.SUCCESS,
            tick_resolved=5,
            events_created=["evt_1", "evt_2"],
            metadata={"detail": "speedy"},
        )
        json_str = result.model_dump_json()
        restored = ActionResult.model_validate_json(json_str)
        assert restored.proposal_id == result.proposal_id
        assert restored.status == ActionResultStatus.SUCCESS
        assert restored.events_created == ["evt_1", "evt_2"]
        assert restored.metadata["detail"] == "speedy"
