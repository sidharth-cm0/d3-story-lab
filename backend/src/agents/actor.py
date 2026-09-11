"""Autonomous actor agent reasoning, decision-making, and action proposal layer."""

from __future__ import annotations
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState
from src.domain.action import ActionProposal, ActionType
from src.simulation.perception import KnowledgeFilter
from src.simulation.actions import ActionValidator
from src.simulation.affordances import ObjectAffordanceResolver
from src.memory.service import MemoryService
from src.providers.base import LLMProvider
from src.providers.mock import MockLLMProvider
from src.agents.social import SocialDialogueGenerator, SocialIntent
from src.agents.repetition import RepetitionTracker
from src.agents.goal_selector import CandidateAction, GoalActionSelector


class ActorDecision(BaseModel):
    """Structured decision output from an autonomous actor"""

    reasoning_summary: str = Field(..., description="Concise explanation of decision without hidden chain of thought")
    intent: str = Field(..., description="What the actor seeks to achieve")
    action_type: ActionType
    target_id: Optional[str] = None
    location_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_effect: str = Field(default="")

    model_config = ConfigDict(frozen=True)


class ActorAgent:
    """Autonomous character agent proposing actions through perception, memory, and reasoning"""

    def __init__(
        self,
        character_id: str,
        provider: Optional[LLMProvider] = None,
        memory_service: Optional[MemoryService] = None,
        repetition_tracker: Optional[RepetitionTracker] = None,
    ):
        self.character_id = character_id
        self.provider = provider or MockLLMProvider()
        self.memory_service = memory_service
        self.repetition_tracker = repetition_tracker or RepetitionTracker()

    def propose_action(self, world: WorldState) -> ActionProposal:
        """Execute the cognitive loop:
        Observe -> Retrieve Memory -> Reason -> Propose Action -> Validate -> (Optional single retry)
        """
        char = world.characters.get(self.character_id)
        if not char:
            return ActionProposal(
                id=f"act_err_{uuid.uuid4().hex[:6]}",
                actor_id=self.character_id,
                action_type=ActionType.WAIT,
                tick_proposed=world.current_tick,
                reason="Character not found in world state",
            )

        # 1. Perception
        obs = KnowledgeFilter.build_observation(world, self.character_id)

        # 2. Memory Retrieval
        retrieved_memories: List[str] = []
        if self.memory_service:
            mems = self.memory_service.retrieve_relevant_memories(
                self.character_id, query=obs.current_location_name or "current room", limit=4
            )
            retrieved_memories = [f"[{m.tick}] {m.summary}" for m in mems]

        # 3. Inner State
        goals = world.get_character_goals(self.character_id)
        beliefs = [f"{b.statement} (confidence: {b.confidence})" for b in world.get_character_beliefs(self.character_id)]
        secrets = [s.statement for s in world.get_character_secrets(self.character_id)]

        # 4. Generate decision
        prompt = self._build_prompt(char, obs, [g.description for g in goals], beliefs, secrets, retrieved_memories)
        system_prompt = (
            f"You are the autonomous actor agent for '{char.name}' ({char.role}). "
            "You make proactive, dramatic, and goal-oriented decisions based on what you observe and know. "
            "Do NOT wait passively unless there are no other viable actions. Engage with other characters, "
            "interact with objects, or explore connected locations."
        )

        if isinstance(self.provider, MockLLMProvider) and ActorDecision not in self.provider._structured_handlers:
            decision = self._build_deterministic_mock_decision(world)
        else:
            decision = self.provider.generate_structured(ActorDecision, prompt, system_prompt=system_prompt)

        proposal = self._decision_to_proposal(decision, world.current_tick)

        # 5. Deterministic validation with single-retry fallback
        is_valid, err_msg = ActionValidator.validate(world, proposal)
        if not is_valid:
            if not isinstance(self.provider, MockLLMProvider) or ActorDecision in self.provider._structured_handlers:
                retry_prompt = (
                    f"{prompt}\n\nATTENTION: Your previous proposed action '{proposal.action_type.value}' was rejected "
                    f"because: {err_msg}. Please choose a valid alternative action."
                )
                retry_decision = self.provider.generate_structured(ActorDecision, retry_prompt, system_prompt=system_prompt)
                retry_proposal = self._decision_to_proposal(retry_decision, world.current_tick)
                is_valid_retry, _ = ActionValidator.validate(world, retry_proposal)
                if is_valid_retry:
                    proposal = retry_proposal
                else:
                    proposal = self._build_fallback_action(world)
            else:
                proposal = self._build_fallback_action(world)

        # Record action in repetition tracker
        self.repetition_tracker.record_action(
            actor_id=self.character_id,
            action_type=proposal.action_type,
            target_id=proposal.target_id,
            location_id=proposal.location_id,
            intent=decision.intent,
        )

        return proposal

    def _build_prompt(
        self,
        char,
        obs,
        goals: List[str],
        beliefs: List[str],
        secrets: List[str],
        memories: List[str],
    ) -> str:
        """Compile strictly private character prompt"""
        vis_chars = [f"{c.name} ({c.role}, holding: {c.inventory or 'none'})" for c in obs.visible_characters]
        vis_objs = [f"{o.name} (id: {o.id}, portable: {o.portable})" for o in obs.visible_objects]
        recent_evts = [f"Tick {e.tick}: {e.description}" for e in obs.recent_events[-4:]]

        lines = [
            f"CHARACTER: {char.name} ({char.role})",
            f"LOCATION: {obs.current_location_name or 'Unknown'} (ID: {obs.current_location_id})",
            f"CONNECTED LOCATIONS: {', '.join(obs.connected_locations) or 'None'}",
            f"VISIBLE CHARACTERS: {', '.join(vis_chars) or 'None'}",
            f"VISIBLE OBJECTS: {', '.join(vis_objs) or 'None'}",
            f"EMOTIONAL STATE: {char.emotional_state.model_dump()}",
            f"ACTIVE GOALS: {goals or 'None'}",
            f"CURRENT BELIEFS: {beliefs or 'None'}",
            f"KNOWN SECRETS: {secrets or 'None'}",
            f"RELEVANT MEMORIES: {memories or 'None'}",
            f"RECENT PERCEIVED EVENTS: {recent_evts or 'None'}",
            "\nDecide your next action to advance your goals and engage with the environment or other characters.",
        ]
        return "\n".join(lines)

    def _build_deterministic_mock_decision(self, world: WorldState) -> ActorDecision:
        """Goal-driven, affordance-based deterministic decision for ANY character."""
        char = world.characters[self.character_id]
        goals = world.get_character_goals(self.character_id)
        loc = world.locations.get(char.current_location_id) if char.current_location_id else None

        candidates: List[CandidateAction] = []

        # 1. Social dialogue with co-located characters
        co_located_chars = [
            c for c in world.characters.values()
            if c.id != char.id and c.current_location_id == char.current_location_id
        ]
        for other in co_located_chars:
            social_candidates = SocialDialogueGenerator.generate_candidates(char, other, goals, world)
            for sc in social_candidates:
                candidates.append(
                    CandidateAction(
                        action_type=ActionType.SPEAK,
                        target_id=other.id,
                        parameters={
                            "dialogue": sc["dialogue"],
                            "target_id": other.id,
                            "social_intent": sc["social_intent"],
                            "speech_act": sc["social_intent"],
                            "topic": sc.get("topic", "the situation"),
                            "claim": sc.get("claim", sc["dialogue"]),
                            "truth_status": sc.get("truth_status", "uncertain"),
                        },
                        intent=f"{sc['social_intent'].capitalize()} {other.name}",
                        reasoning=f"Social interaction to advance goals: {sc['dialogue'][:35]}",
                        base_utility=sc["base_utility"],
                    )
                )

        # 2. Object affordances
        accessible_objs = [
            o for o in world.objects.values()
            if o.location_id == char.current_location_id or o.holder_id == char.id
        ]
        for obj in accessible_objs:
            affordances = ObjectAffordanceResolver.resolve_affordances(obj, char, loc)
            for aff in affordances:
                candidates.append(
                    CandidateAction(
                        action_type=aff.action_type,
                        target_id=aff.target_id,
                        parameters=aff.parameters,
                        intent=aff.description,
                        reasoning=f"Interact with {obj.name} regarding current situation",
                        base_utility=aff.utility_hint,
                    )
                )

        # 3. Locomotion / Movement to connected rooms
        if loc and loc.connected_locations:
            for conn_id in loc.connected_locations:
                conn_loc = world.locations.get(conn_id)
                loc_name = conn_loc.name if conn_loc else conn_id
                candidates.append(
                    CandidateAction(
                        action_type=ActionType.MOVE,
                        location_id=conn_id,
                        parameters={"destination_id": conn_id},
                        intent=f"Move to {loc_name}",
                        reasoning=f"Explore or change position to {loc_name}",
                        base_utility=0.55,
                    )
                )

        # 4. Wait as last-resort fallback
        candidates.append(
            CandidateAction(
                action_type=ActionType.WAIT,
                intent="Wait",
                reasoning="Observe situation quietly",
                base_utility=0.05,
            )
        )

        # Score all candidates against goals, emotional state, and repetition penalties
        for cand in candidates:
            GoalActionSelector.score_candidate(
                cand, char, goals, world, self.repetition_tracker
            )

        # Sort descending by final score
        candidates.sort(key=lambda c: c.final_score, reverse=True)

        # Pick the highest-scoring candidate that passes deterministic validation
        for cand in candidates:
            temp_proposal = self._candidate_to_proposal(cand, world.current_tick)
            is_valid, _ = ActionValidator.validate(world, temp_proposal)
            if is_valid:
                return ActorDecision(
                    reasoning_summary=cand.reasoning,
                    intent=cand.intent,
                    action_type=cand.action_type,
                    target_id=cand.target_id,
                    location_id=cand.location_id,
                    parameters=cand.parameters,
                    confidence=0.85,
                )

        # If somehow none are valid, fallback to WAIT
        return ActorDecision(
            reasoning_summary="No valid active action available",
            intent="Wait",
            action_type=ActionType.WAIT,
        )

    def _build_fallback_action(self, world: WorldState) -> ActionProposal:
        """Safe fallback proposal when primary proposal is rejected"""
        char = world.characters.get(self.character_id)
        if char and char.current_location_id:
            loc = world.locations.get(char.current_location_id)
            if loc and loc.connected_locations:
                dest = loc.connected_locations[0]
                return ActionProposal(
                    id=f"prop_fallback_move_{self.character_id}_{world.current_tick}_{uuid.uuid4().hex[:6]}",
                    actor_id=self.character_id,
                    action_type=ActionType.MOVE,
                    location_id=dest,
                    parameters={"destination_id": dest},
                    tick_proposed=world.current_tick,
                    reason="Moving to adjacent room after previous action rejected",
                )

        return ActionProposal(
            id=f"prop_fallback_wait_{self.character_id}_{world.current_tick}_{uuid.uuid4().hex[:6]}",
            actor_id=self.character_id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            reason="Waiting after validation failure",
        )

    def _candidate_to_proposal(self, candidate: CandidateAction, current_tick: int) -> ActionProposal:
        return ActionProposal(
            id=f"prop_{self.character_id}_{current_tick}_{uuid.uuid4().hex[:6]}",
            actor_id=self.character_id,
            action_type=candidate.action_type,
            target_id=candidate.target_id,
            location_id=candidate.location_id,
            parameters=dict(candidate.parameters),
            tick_proposed=current_tick,
            reason=f"{candidate.intent}: {candidate.reasoning}",
        )

    def _decision_to_proposal(self, decision: ActorDecision, current_tick: int) -> ActionProposal:
        """Convert an ActorDecision to an ActionProposal"""
        return ActionProposal(
            id=f"prop_{self.character_id}_{current_tick}_{uuid.uuid4().hex[:6]}",
            actor_id=self.character_id,
            action_type=decision.action_type,
            target_id=decision.target_id,
            location_id=decision.location_id,
            parameters=dict(decision.parameters),
            tick_proposed=current_tick,
            reason=f"{decision.intent}: {decision.reasoning_summary}",
        )
