"""Deterministic rule-based policies for simulation agents"""
import uuid
import hashlib
from typing import Dict, Any, Optional
from ..domain import WorldState, ActionProposal, ActionType


def _det_id(prefix: str, char_id: str, tick: int, tag: str) -> str:
    slug = hashlib.sha256(f"{char_id}:{tick}:{tag}".encode()).hexdigest()[:6]
    return f"{prefix}_{char_id}_{tick}_{slug}"


class RuleBasedPolicy:
    """Provides deterministic action proposals based on character state and world context"""

    @staticmethod
    def decide_action(
        world: WorldState,
        character_id: str,
        recent_events: Optional[list] = None,
    ) -> ActionProposal:
        """Deterministically choose an action proposal for a character"""
        char = world.characters.get(character_id)
        if not char:
            slug = hashlib.sha256(f"{character_id}:{world.current_tick}:not_found".encode()).hexdigest()[:8]
            return ActionProposal(
                id=f"prop_{slug}",
                actor_id=character_id,
                action_type=ActionType.WAIT,
                tick_proposed=world.current_tick,
                reason="Character not found",
            )

        # Specialized rules for Hotel Intrigue demo
        if character_id == "char_maya":
            return RuleBasedPolicy._decide_maya(world, char)
        elif character_id == "char_arjun":
            return RuleBasedPolicy._decide_arjun(world, char)

        # Generic default policy
        return RuleBasedPolicy._decide_generic(world, char)

    @staticmethod
    def _decide_maya(world: WorldState, maya) -> ActionProposal:
        """Maya's deterministic policy: protect secrets, secure documents, deflect Arjun"""
        docs = world.objects.get("obj_documents")

        # 1. If documents are sitting in the room unheld, take them to protect the secret
        if docs and docs.location_id == maya.current_location_id and docs.holder_id is None:
            return ActionProposal(
                id=_det_id("prop_maya", maya.id, world.current_tick, "take_docs"),
                actor_id=maya.id,
                action_type=ActionType.TAKE_OBJECT,
                target_id=docs.id,
                location_id=maya.current_location_id,
                tick_proposed=world.current_tick,
                reason="Protect the documents from investigation",
            )

        # 2. If Maya is holding the documents, inspect the suitcase as a hiding place
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
                    reason="Assess suitcase for securing confidential records",
                )

        # 3. If Arjun is in the same room, deflect conversation
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
                reason="Maintain control over the discussion",
            )

        # Fallback: wait
        return ActionProposal(
            id=_det_id("prop_maya", maya.id, world.current_tick, "wait"),
            actor_id=maya.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            reason="Wait and assess the environment",
        )

    @staticmethod
    def _decide_arjun(world: WorldState, arjun) -> ActionProposal:
        """Arjun's deterministic policy: investigate fraud, examine documents, question Maya"""
        docs = world.objects.get("obj_documents")

        # 1. If documents are in the room, inspect them
        if docs and docs.location_id == arjun.current_location_id and docs.holder_id is None:
            return ActionProposal(
                id=_det_id("prop_arjun", arjun.id, world.current_tick, "inspect_docs"),
                actor_id=arjun.id,
                action_type=ActionType.INSPECT_OBJECT,
                target_id=docs.id,
                location_id=arjun.current_location_id,
                tick_proposed=world.current_tick,
                reason="Examine project files for evidence of fraud",
            )

        # 2. If Maya is present and holds the documents or documents are absent, question her
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
                reason="Recover truth regarding missing documents",
            )

        # Fallback: observe room
        return ActionProposal(
            id=_det_id("prop_arjun", arjun.id, world.current_tick, "wait"),
            actor_id=arjun.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            reason="Monitor room for clues",
        )

    @staticmethod
    def _decide_generic(world: WorldState, char) -> ActionProposal:
        """Generic fallback for unspecialized characters"""
        return ActionProposal(
            id=_det_id("prop", char.id, world.current_tick, "generic_wait"),
            actor_id=char.id,
            action_type=ActionType.WAIT,
            tick_proposed=world.current_tick,
            reason="Passive observation",
        )
