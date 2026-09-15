"""Decision policy architecture and deterministic rule policy for D3 Story Lab."""

from __future__ import annotations
import random
import hashlib
import logging
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState
from src.domain.character import Character
from src.domain.action import ActionProposal, ActionType, Motivation
from src.domain.world_view import CharacterWorldView
from src.simulation.affordances import ObjectAffordance, ObjectAffordanceResolver
from src.agents.repetition import RepetitionTracker
from src.agents.goal_selector import CandidateAction, GoalActionSelector
from src.agents.social import SocialDialogueGenerator
from src.providers.base import LLMProvider
from src.providers.mock import MockLLMProvider

logger = logging.getLogger(__name__)

Affordance = ObjectAffordance


@runtime_checkable
class DecisionPolicy(Protocol):
    """Protocol for character decision policies (rule-based or LLM-based)."""

    def propose(
        self,
        character: Character,
        view: CharacterWorldView,
        affordances: List[ObjectAffordance],
        rng: random.Random,
    ) -> ActionProposal:
        """Propose an ActionProposal based exclusively on subjective CharacterWorldView and affordances."""
        ...


class RuleDecisionPolicy:
    """The canonical deterministic rule decision policy. Runs with ZERO AI calls."""

    def __init__(self, repetition_tracker: Optional[RepetitionTracker] = None):
        self.repetition_tracker = repetition_tracker or RepetitionTracker()

    def propose(
        self,
        character: Character,
        view: CharacterWorldView,
        affordances: List[ObjectAffordance],
        rng: random.Random,
    ) -> ActionProposal:
        """Deterministically evaluate and score all valid candidate actions for the character."""
        candidates: List[CandidateAction] = []
        active_goal = view.goals[0] if view.goals else None
        active_goal_id = active_goal.id if active_goal else None

        # 1. Social dialogue with co-present characters
        for other in view.perceivable_characters.values():
            social_candidates = SocialDialogueGenerator.generate_candidates(character, other, view.goals, view)
            for sc in social_candidates:
                intent = sc.get("social_intent") or ""
                prior_evt_id = None
                if view.recent_events:
                    for ev in reversed(view.recent_events):
                        if ev.event_type.value == "character_spoke" and other.id in ev.actor_ids:
                            prior_evt_id = ev.id
                            break
                if prior_evt_id:
                    cand_motivation = Motivation(kind="REACT_TO_EVENT", prior_event_id=prior_evt_id)
                elif intent == "reveal" and view.knowledge:
                    cand_motivation = Motivation(kind="ACT_ON_KNOWLEDGE", knowledge_item_id=next(iter(view.knowledge.keys())))
                else:
                    cand_motivation = Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id)

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
                        motivation=cand_motivation,
                    )
                )

        # 2. Object Affordances
        resolved_affordances = list(affordances)
        if not resolved_affordances:
            for obj in view.perceivable_objects.values():
                resolved_affordances.extend(ObjectAffordanceResolver.resolve_affordances(obj, character, view.current_location))

        for aff in resolved_affordances:
            target_obj = view.perceivable_objects.get(aff.target_id)
            if not target_obj:
                continue

            # Skip illegal affordances based on view
            if aff.action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP) and target_obj.holder_id is not None:
                continue
            if aff.action_type in (ActionType.DROP_OBJECT, ActionType.DROP) and target_obj.holder_id != character.id:
                continue
            if aff.action_type in (ActionType.OPEN_OBJECT, ActionType.OPEN_DOOR) and (target_obj.properties.get("locked") == "true" or target_obj.properties.get("locked") is True):
                continue

            obj_name = target_obj.name.lower()

            # Check if related to active goals
            matching_goal = None
            if active_goal and any(w in active_goal.description.lower() for w in obj_name.split()):
                matching_goal = active_goal
            elif view.goals:
                for g in view.goals:
                    if any(w in g.description.lower() for w in obj_name.split()):
                        matching_goal = g
                        break

            if matching_goal:
                aff_motivation = Motivation(kind="PURSUE_GOAL", goal_id=matching_goal.id)
            elif aff.target_id in view.knowledge:
                aff_motivation = Motivation(kind="ACT_ON_KNOWLEDGE", knowledge_item_id=aff.target_id)
            elif view.emotional_state.fear > 0.6:
                prior_evt_id = view.recent_events[-1].id if view.recent_events else None
                aff_motivation = Motivation(kind="AVOID_THREAT", prior_event_id=prior_evt_id)
            else:
                aff_motivation = Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id)

            candidates.append(
                CandidateAction(
                    action_type=aff.action_type,
                    target_id=aff.target_id,
                    parameters=aff.parameters,
                    intent=aff.description,
                    reasoning=f"Interact with {aff.target_id} ({aff.description})",
                    base_utility=aff.utility_hint,
                    motivation=aff_motivation,
                )
            )

        # 3. Locomotion / Movement
        for conn_id, conn_loc in view.reachable_locations.items():
            if view.emotional_state.fear > 0.6:
                prior_evt_id = view.recent_events[-1].id if view.recent_events else None
                move_motivation = Motivation(kind="AVOID_THREAT", prior_event_id=prior_evt_id)
            else:
                move_motivation = Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id)

            candidates.append(
                CandidateAction(
                    action_type=ActionType.MOVE,
                    location_id=conn_id,
                    parameters={"destination_id": conn_id},
                    intent=f"Move to {conn_loc.name}",
                    reasoning=f"Navigate to connected area {conn_loc.name}",
                    base_utility=0.55,
                    motivation=move_motivation,
                )
            )

        # 4. Fallback Wait
        candidates.append(
            CandidateAction(
                action_type=ActionType.WAIT,
                intent="Wait",
                reasoning="Observe situation quietly",
                base_utility=0.05,
                motivation=Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id),
            )
        )

        # Score all candidates
        for cand in candidates:
            GoalActionSelector.score_candidate(
                candidate=cand,
                actor=character,
                goals=view.goals,
                world=view,
                repetition_tracker=self.repetition_tracker,
            )

        # Sort descending with deterministic tie-breaking:
        # (final_score, intent, action_type, target_id, rng_jitter)
        jitter_map = {id(c): rng.random() * 1e-6 for c in candidates}
        candidates.sort(
            key=lambda c: (
                c.final_score,
                c.intent,
                c.action_type.value,
                c.target_id or "",
                jitter_map[id(c)],
            ),
            reverse=True,
        )

        winning = candidates[0]
        rand_suffix = rng.randint(1000, 9999)
        prop_id = f"prop_{character.id}_{view.current_tick}_{rand_suffix}"

        return ActionProposal(
            id=prop_id,
            actor_id=character.id,
            action_type=winning.action_type,
            target_id=winning.target_id,
            location_id=winning.location_id,
            parameters=dict(winning.parameters),
            tick_proposed=view.current_tick,
            motivation=winning.motivation or Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id),
            expected_outcome=winning.intent,
            reason=f"{winning.intent}: {winning.reasoning}",
        )


class PolicyDecisionOutput(BaseModel):
    """Structured decision output for LLM decision policy."""
    reasoning_summary: str = Field(..., description="Concise rationale for action")
    intent: str = Field(..., description="Action intent")
    action_type: ActionType
    target_id: Optional[str] = None
    location_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_effect: str = Field(default="")

    model_config = ConfigDict(frozen=True)


class LLMDecisionPolicy:
    """Swappable decision policy backed by an LLM provider with fallback to RuleDecisionPolicy."""

    def __init__(
        self,
        provider: LLMProvider,
        fallback_policy: Optional[RuleDecisionPolicy] = None,
    ):
        self.provider = provider
        self.fallback = fallback_policy or RuleDecisionPolicy()

    def propose(
        self,
        character: Character,
        view: CharacterWorldView,
        affordances: List[ObjectAffordance],
        rng: random.Random,
    ) -> ActionProposal:
        """Query LLM provider using firewalled view, falling back to rule policy on error or mock."""
        if isinstance(self.provider, MockLLMProvider) and PolicyDecisionOutput not in self.provider._structured_handlers:
            return self.fallback.propose(character, view, affordances, rng)

        try:
            prompt = self._build_prompt_from_view(character, view, affordances)
            system_prompt = (
                f"You are the autonomous actor agent for '{character.name}' ({character.role}). "
                "You make proactive, dramatic, and goal-oriented decisions based on what you observe and know. "
                "Engage with other characters, interact with objects, or explore connected locations."
            )
            decision = self.provider.generate_structured(PolicyDecisionOutput, prompt, system_prompt=system_prompt)
            if decision and hasattr(decision, "action_type") and decision.action_type:
                active_goal_id = view.goals[0].id if view.goals else None
                motivation = Motivation(kind="PURSUE_GOAL", goal_id=active_goal_id)
                rand_suffix = rng.randint(1000, 9999)
                return ActionProposal(
                    id=f"prop_llm_{character.id}_{view.current_tick}_{rand_suffix}",
                    actor_id=character.id,
                    action_type=decision.action_type,
                    target_id=decision.target_id,
                    location_id=decision.location_id,
                    parameters=dict(decision.parameters),
                    tick_proposed=view.current_tick,
                    motivation=motivation,
                    expected_outcome=decision.intent,
                    reason=f"{decision.intent}: {decision.reasoning_summary}",
                )
        except Exception as e:
            logger.warning(f"LLMDecisionPolicy invocation failed ({e}); falling back to RuleDecisionPolicy.")

        return self.fallback.propose(character, view, affordances, rng)

    def _build_prompt_from_view(
        self,
        character: Character,
        view: CharacterWorldView,
        affordances: List[ObjectAffordance],
    ) -> str:
        vis_chars = [f"{c.name} ({c.role})" for c in view.perceivable_characters.values()]
        vis_objs = [f"{o.name} ({o.id})" for o in view.perceivable_objects.values()]
        goals = [f"{g.description} (priority: {g.priority})" for g in view.goals]
        recent_evts = [f"Tick {e.tick}: {e.description}" for e in view.recent_events[-5:]]
        conns = [c.name for c in view.reachable_locations.values()]

        return "\n".join([
            f"CHARACTER: {character.name} ({character.role})",
            f"LOCATION: {view.current_location.name if view.current_location else 'Unknown'}",
            f"REACHABLE LOCATIONS: {', '.join(conns) or 'None'}",
            f"VISIBLE CHARACTERS: {', '.join(vis_chars) or 'None'}",
            f"VISIBLE OBJECTS: {', '.join(vis_objs) or 'None'}",
            f"ACTIVE GOALS: {goals or 'None'}",
            f"EMOTION: {view.emotional_state.model_dump()}",
            f"RECENT EVENTS: {recent_evts or 'None'}",
            "Decide your next action.",
        ])


def _det_id(prefix: str, char_id: str, tick: int, tag: str) -> str:
    slug = hashlib.sha256(f"{char_id}:{tick}:{tag}".encode()).hexdigest()[:6]
    return f"{prefix}_{char_id}_{tick}_{slug}"


class RuleBasedPolicy:
    """Provides backward-compatible deterministic action proposals for early Milestone 2 engine."""

    @staticmethod
    def decide_action(
        world: WorldState,
        character_id: str,
        recent_events: Optional[list] = None,
    ) -> ActionProposal:
        """Deterministically choose an action proposal for a character with valid Motivation."""
        char = world.characters.get(character_id)
        if not char:
            slug = hashlib.sha256(f"{character_id}:{world.current_tick}:not_found".encode()).hexdigest()[:8]
            return ActionProposal(
                id=f"prop_{slug}",
                actor_id=character_id,
                action_type=ActionType.WAIT,
                tick_proposed=world.current_tick,
                motivation=Motivation(kind="PURSUE_GOAL"),
                reason="Character not found",
            )

        if character_id == "char_maya":
            return RuleBasedPolicy._decide_maya(world, char)
        elif character_id == "char_arjun":
            return RuleBasedPolicy._decide_arjun(world, char)

        return RuleBasedPolicy._decide_generic(world, char)

    @staticmethod
    def _decide_maya(world: WorldState, maya) -> ActionProposal:
        docs = world.objects.get("obj_documents")
        if docs and docs.location_id == maya.current_location_id and docs.holder_id is None:
            return ActionProposal(
                id=_det_id("prop_maya", maya.id, world.current_tick, "take_docs"),
                actor_id=maya.id,
                action_type=ActionType.TAKE_OBJECT,
                target_id=docs.id,
                location_id=maya.current_location_id,
                tick_proposed=world.current_tick,
                motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_protect_secrets"),
                reason="Protect the documents from investigation",
            )

        if docs and docs.holder_id == maya.id:
            suitcase = world.objects.get("obj_suitcase")
            if suitcase and suitcase.location_id == maya.current_location_id:
                return ActionProposal(
                    id=_det_id("prop_maya", maya.id, world.current_tick, "inspect_suitcase"),
                    actor_id=maya.id,
                    action_type=ActionType.INSPECT_OBJECT,
                    target_id=suitcase.id,
                    location_id=maya.current_location_id,
                    tick_proposed=world.current_tick,
                    motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_protect_secrets"),
                    reason="Assess suitcase for securing confidential records",
                )

        arjun = world.characters.get("char_arjun")
        if arjun and arjun.current_location_id == maya.current_location_id:
            return ActionProposal(
                id=_det_id("prop_maya", maya.id, world.current_tick, "deflect_arjun"),
                actor_id=maya.id,
                action_type=ActionType.SPEAK,
                target_id=arjun.id,
                location_id=maya.current_location_id,
                parameters={"dialogue": "We should keep our conversation strictly professional, Arjun."},
                tick_proposed=world.current_tick,
                motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_deflect"),
                reason="Maintain control over the discussion",
            )

        return ActionProposal(
            id=_det_id("prop_maya", maya.id, world.current_tick, "wait"),
            actor_id=maya.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            motivation=Motivation(kind="PURSUE_GOAL"),
            reason="Wait and assess the environment",
        )

    @staticmethod
    def _decide_arjun(world: WorldState, arjun) -> ActionProposal:
        docs = world.objects.get("obj_documents")
        if docs and docs.location_id == arjun.current_location_id and docs.holder_id is None:
            return ActionProposal(
                id=_det_id("prop_arjun", arjun.id, world.current_tick, "inspect_docs"),
                actor_id=arjun.id,
                action_type=ActionType.INSPECT_OBJECT,
                target_id=docs.id,
                location_id=arjun.current_location_id,
                tick_proposed=world.current_tick,
                motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_investigate"),
                reason="Examine project files for evidence of fraud",
            )

        maya = world.characters.get("char_maya")
        if maya and maya.current_location_id == arjun.current_location_id:
            dialogue = (
                "Maya, what is inside those project files you just picked up?"
                if docs and docs.holder_id == maya.id
                else "Maya, I know the CEO was involved in something questionable."
            )
            return ActionProposal(
                id=_det_id("prop_arjun", arjun.id, world.current_tick, "question_maya"),
                actor_id=arjun.id,
                action_type=ActionType.SPEAK,
                target_id=maya.id,
                location_id=arjun.current_location_id,
                parameters={"dialogue": dialogue},
                tick_proposed=world.current_tick,
                motivation=Motivation(kind="PURSUE_GOAL", goal_id="goal_investigate"),
                reason="Recover truth regarding missing documents",
            )

        return ActionProposal(
            id=_det_id("prop_arjun", arjun.id, world.current_tick, "wait"),
            actor_id=arjun.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            motivation=Motivation(kind="PURSUE_GOAL"),
            reason="Monitor room for clues",
        )

    @staticmethod
    def _decide_generic(world: WorldState, char) -> ActionProposal:
        return ActionProposal(
            id=_det_id("prop", char.id, world.current_tick, "generic_wait"),
            actor_id=char.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            motivation=Motivation(kind="PURSUE_GOAL"),
            reason="Passive observation",
        )
