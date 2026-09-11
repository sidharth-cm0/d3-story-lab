"""Tests for Milestone 8: Autonomous Actor Agents"""
import pytest
from src.demo_world import create_demo_world
from src.domain import ActionType, ActionProposal
from src.agents.actor import ActorAgent, ActorDecision
from src.memory import MemoryService
from src.providers import MockLLMProvider


class TestActorAgent:
    """Tests verifying ActorAgent reasoning, privacy boundaries, and validation retry"""

    def test_actor_agent_proposes_valid_action(self):
        """Test ActorAgent produces a valid ActionProposal"""
        world = create_demo_world()
        agent = ActorAgent("char_maya")

        proposal = agent.propose_action(world)
        assert isinstance(proposal, ActionProposal)
        assert proposal.actor_id == "char_maya"
        assert proposal.action_type in (ActionType.TAKE_OBJECT, ActionType.SPEAK, ActionType.WAIT)
        # Verify world state was NOT mutated directly
        assert world.current_tick == 0

    def test_actor_agent_cannot_mutate_world_state(self):
        """Test that calling propose_action leaves WorldState completely unmutated"""
        world = create_demo_world()
        initial_json = world.model_dump_json()

        agent = ActorAgent("char_arjun")
        agent.propose_action(world)

        # World JSON must be 100% identical
        assert world.model_dump_json() == initial_json

    def test_actor_agent_validation_retry_recovery(self):
        """Test that an invalid decision triggers retry with validation error feedback"""
        world = create_demo_world()
        provider = MockLLMProvider()

        # Step 1: Force provider to return an invalid move first, then a valid WAIT on retry
        attempts = []

        def custom_handler(prompt: str) -> ActorDecision:
            attempts.append(prompt)
            if len(attempts) == 1:
                # Propose illegal move to non-existent room
                return ActorDecision(
                    reasoning_summary="Attempting escape",
                    intent="Escape",
                    action_type=ActionType.MOVE,
                    location_id="loc_non_existent_99",
                )
            else:
                # Propose legal WAIT on retry
                return ActorDecision(
                    reasoning_summary="Waiting calmly",
                    intent="Wait",
                    action_type=ActionType.WAIT,
                )

        provider.register_structured_handler(ActorDecision, custom_handler)
        agent = ActorAgent("char_arjun", provider=provider)

        proposal = agent.propose_action(world)
        assert len(attempts) == 2
        assert "ATTENTION: Your previous proposed action" in attempts[1]
        assert proposal.action_type == ActionType.WAIT

    def test_actor_with_memory_service(self):
        """Test that actor utilizes memory service for prompt compilation"""
        world = create_demo_world()
        memory_service = MemoryService(world)
        memory_service.form_memory(
            character_id="char_arjun",
            summary="Recalled secret wiretap recording of room 307.",
            importance=0.9,
            emotional_weight=0.5,
            tags=["wiretap", "hotel room 307"],
        )

        agent = ActorAgent("char_arjun", memory_service=memory_service)
        obs = agent.propose_action(world)
        assert obs is not None
