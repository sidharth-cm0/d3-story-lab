"""Goal-driven action evaluation and candidate scoring for D3 Story Lab."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from src.domain.world import WorldState
from src.domain.character import Character
from src.domain.action import ActionType, ActionProposal, Motivation
from src.domain.goal import Goal
from src.domain.world_view import CharacterWorldView
from src.agents.repetition import RepetitionTracker


class CandidateAction:
    """An actionable choice available to a character with computed utility."""

    def __init__(
        self,
        action_type: ActionType,
        target_id: Optional[str] = None,
        location_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        intent: str = "",
        reasoning: str = "",
        base_utility: float = 0.5,
        motivation: Optional[Motivation] = None,
    ):
        self.action_type = action_type
        self.target_id = target_id
        self.location_id = location_id
        self.parameters = parameters or {}
        self.intent = intent
        self.reasoning = reasoning
        self.base_utility = base_utility
        self.motivation = motivation
        self.final_score: float = base_utility


class GoalActionSelector:
    """Scores candidate actions against character goals, emotional drive, novelty, and repetition penalties."""

    @staticmethod
    def score_candidate(
        candidate: CandidateAction,
        actor: Character,
        goals: List[Goal],
        world: WorldState | CharacterWorldView,
        repetition_tracker: Optional[RepetitionTracker] = None,
    ) -> float:
        score = candidate.base_utility

        # Extract views/state flexibly
        if isinstance(world, CharacterWorldView):
            objs = world.perceivable_objects
            events = world.recent_events
            chars = world.perceivable_characters
            trust_map = world.relationship_trust
        else:
            objs = world.objects
            events = list(world.events.values())
            chars = world.characters
            trust_map = {}
            for r in getattr(world, "relationships", {}).values():
                if r.character_a_id == actor.id:
                    trust_map[r.character_b_id] = r.trust
                elif r.character_b_id == actor.id:
                    trust_map[r.character_a_id] = r.trust

        # 1. Inspecting already-inspected objects has negligible novelty
        if candidate.action_type == ActionType.INSPECT_OBJECT and candidate.target_id:
            target_obj = objs.get(candidate.target_id)
            if target_obj and actor.id in getattr(target_obj, "inspected_by", []):
                score = 0.05
            elif target_obj and not actor.knows(candidate.target_id):
                # Knowledge-gap bonus: reward inspecting unknown/unheld clue
                score += 0.25

        # 2. Conversational response priority: if co-located partner just spoke, answer them
        last_speech = None
        for ev in reversed(events):
            if ev.event_type.value == "character_spoke" and ev.location_id == actor.current_location_id:
                last_speech = ev
                break

        if last_speech and last_speech.metadata.get("speaker_id") != actor.id:
            speaker_id = last_speech.metadata.get("speaker_id")
            if candidate.action_type == ActionType.SPEAK and candidate.target_id == speaker_id:
                score += 0.35  # Strong boost to engage in responsive conversation

        # 3. Movement preference: don't wander away if engaged in active dialogue or uninspected clues exist
        if candidate.action_type == ActionType.MOVE:
            co_located = [c for c in chars.values() if c.id != actor.id and getattr(c, "current_location_id", None) == actor.current_location_id]
            uninspected_here = [
                o for o in objs.values()
                if (o.location_id == actor.current_location_id or getattr(o, "holder_id", None) == actor.id)
                and actor.id not in getattr(o, "inspected_by", [])
            ]
            if co_located or uninspected_here:
                score -= 0.25

        # 4. Inventory constraint: already holding an object discourages picking up another
        if candidate.action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP) and len(actor.inventory) >= 1:
            score -= 0.40

        # 5. Goal alignment
        goal_boost = 0.0
        for g in goals:
            g_desc = g.description.lower()
            p = g.priority

            # Investigation goals
            if any(w in g_desc for w in ["discover", "find", "uncover", "investigate", "prove", "learn", "who", "what", "truth"]):
                if candidate.action_type == ActionType.SPEAK and candidate.parameters.get("social_intent") in ("question", "accuse"):
                    goal_boost += 0.35 * p
                elif candidate.action_type == ActionType.INSPECT_OBJECT:
                    goal_boost += 0.30 * p
                elif candidate.action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
                    goal_boost += 0.25 * p
                elif candidate.action_type in (ActionType.DROP_OBJECT, ActionType.DROP):
                    goal_boost -= 0.50
                elif candidate.action_type == ActionType.MOVE:
                    goal_boost += 0.20 * p

            # Concealment goals
            elif any(w in g_desc for w in ["hide", "protect", "conceal", "secure", "survive", "escape", "prevent"]):
                if candidate.action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
                    goal_boost += 0.35 * p
                elif candidate.action_type in (ActionType.DROP_OBJECT, ActionType.DROP):
                    goal_boost -= 0.50  # Dropping items on the open floor compromises security
                elif candidate.action_type == ActionType.SPEAK and candidate.parameters.get("social_intent") in ("deny", "warn", "deflect"):
                    goal_boost += 0.30 * p
                elif candidate.action_type == ActionType.MOVE:
                    goal_boost += 0.25 * p

            # Negotiation / Resolution goals
            elif any(w in g_desc for w in ["negotiate", "persuade", "convince", "cooperate", "resolve", "settle"]):
                if candidate.action_type == ActionType.SPEAK:
                    goal_boost += 0.35 * p

        score += goal_boost

        # 6. Emotional state drive & Relationship scores
        emo = actor.emotional_state
        if candidate.action_type == ActionType.SPEAK:
            social_intent = candidate.parameters.get("social_intent") or candidate.parameters.get("speech_act") or ""
            target_trust = trust_map.get(candidate.target_id, 0.0) if candidate.target_id else 0.0

            if social_intent == "accuse":
                if emo.anger > 0.3:
                    score += 0.15
                if emo.fear > 0.4:
                    score -= 0.25  # Fear suppresses confrontation
                if target_trust < 0:
                    score += (-target_trust) * 0.15  # Hostility enables accusation
            elif social_intent == "question":
                if emo.curiosity > 0.5:
                    score += 0.15
            elif social_intent in ("cooperate", "reveal", "share"):
                if target_trust > 0:
                    score += target_trust * 0.15  # Trust enables disclosure

        elif candidate.action_type == ActionType.INSPECT_OBJECT and emo.curiosity > 0.5:
            score += 0.15
        elif candidate.action_type == ActionType.MOVE and emo.fear > 0.4:
            score += 0.25  # Fear encourages changing location / fleeing

        # 7. Severe penalty for WAIT when active alternatives exist
        if candidate.action_type == ActionType.WAIT:
            score = 0.05

        # 8. Deduct repetition penalty
        if repetition_tracker:
            topic = candidate.parameters.get("topic")
            speech_act = candidate.parameters.get("speech_act") or candidate.parameters.get("social_intent")
            penalty = repetition_tracker.get_penalty(
                actor_id=actor.id,
                action_type=candidate.action_type,
                target_id=candidate.target_id,
                location_id=candidate.location_id,
                topic=topic,
                speech_act=speech_act,
            )
            score -= penalty

        candidate.final_score = round(max(0.01, score), 3)
        return candidate.final_score
