"""Action validation and execution engine with 4 deterministic gates."""

from __future__ import annotations
from typing import Tuple, Optional, List, Dict, Any
from ..domain import (
    WorldState,
    ActionProposal,
    ActionResult,
    ActionType,
    ActionResultStatus,
    EventType,
    DiscoveredFact,
    ActionRejection,
)
from .recorder import EventRecorder


class KnowledgeGate:
    """Validates that an actor acts only on knowledge they subjectively hold."""

    @staticmethod
    def validate(world: WorldState, proposal: ActionProposal) -> Tuple[bool, Optional[str]]:
        actor = world.characters.get(proposal.actor_id)
        if not actor:
            return False, f"Actor '{proposal.actor_id}' does not exist"

        # 1. Motivation knowledge item check
        if proposal.motivation and proposal.motivation.knowledge_item_id:
            k_id = proposal.motivation.knowledge_item_id
            if not actor.knows(k_id) and k_id not in actor.known_facts:
                return False, f"Actor does not hold knowledge '{k_id}'"

        # 2. Secret proposition / knowledge check in parameters
        prop_id = proposal.parameters.get("proposition_id") or proposal.parameters.get("secret_id")
        if prop_id:
            if not actor.knows(prop_id) and prop_id not in actor.secrets:
                return False, f"Actor does not hold secret/proposition '{prop_id}'"

        # 3. Secret object interaction check
        target_id = proposal.target_id or proposal.parameters.get("object_id")
        if target_id and target_id in world.objects:
            target_obj = world.objects[target_id]
            is_secret = (
                getattr(target_obj, "is_secret", False)
                or (target_obj.properties and (
                    target_obj.properties.get("is_secret") is True
                    or str(target_obj.properties.get("is_secret")).lower() == "true"
                ))
            )
            if is_secret and target_obj.holder_id != actor.id:
                has_knowledge = (
                    actor.knows(target_obj.id) is not None
                    or actor.knows(f"prop_{target_obj.id}") is not None
                    or any(target_obj.id in s.statement or target_obj.name.lower() in s.statement.lower() for s in world.get_character_secrets(actor.id))
                    or any(target_obj.id in k_id for k_id in actor.knowledge.keys())
                )
                if not has_knowledge:
                    return False, f"Actor does not hold knowledge of secret object '{target_obj.name}'"

        return True, None


class SpatialGate:
    """Validates spatial connectivity, co-location, and reachability."""

    @staticmethod
    def validate(world: WorldState, proposal: ActionProposal) -> Tuple[bool, Optional[str]]:
        actor = world.characters.get(proposal.actor_id)
        if not actor:
            return False, f"Actor '{proposal.actor_id}' does not exist"

        action_type = proposal.action_type

        if action_type == ActionType.MOVE:
            dest_id = proposal.location_id or proposal.parameters.get("destination_id") or proposal.parameters.get("to")
            if not dest_id:
                return False, "Move action requires a destination location_id"
            dest = world.locations.get(dest_id)
            if not dest:
                return False, f"Destination location '{dest_id}' does not exist"
            if actor.current_location_id == dest_id:
                return False, f"Actor is already at location '{dest_id}'"

            # Check adjacency/connectivity
            current_loc = world.locations.get(actor.current_location_id) if actor.current_location_id else None
            if current_loc and dest_id not in current_loc.connected_locations:
                return False, f"Location '{dest_id}' is not connected to current location '{actor.current_location_id}'"

            # Check capacity
            if dest.capacity is not None:
                occupants = [c for c in world.characters.values() if c.current_location_id == dest_id]
                if len(occupants) >= dest.capacity:
                    return False, f"Location '{dest_id}' has reached maximum capacity ({dest.capacity})"
            return True, None

        elif action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            if not obj_id:
                return False, "Take action requires a target object_id"
            obj = world.objects.get(obj_id)
            if not obj:
                return False, f"Object '{obj_id}' does not exist"
            obj_loc = obj.location_id
            if obj.holder_id:
                holder = world.characters.get(obj.holder_id)
                obj_loc = holder.current_location_id if holder else None
            if obj_loc != actor.current_location_id and obj.holder_id != actor.id:
                return False, f"Object '{obj_id}' is at '{obj_loc}', not at actor's location '{actor.current_location_id}'"
            return True, None

        elif action_type in (ActionType.DROP_OBJECT, ActionType.DROP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            if not obj_id:
                return False, "Drop action requires a target object_id"
            obj = world.objects.get(obj_id)
            if not obj:
                return False, f"Object '{obj_id}' does not exist"
            return True, None

        elif action_type in (ActionType.GIVE_OBJECT, ActionType.GIVE):
            obj_id = proposal.parameters.get("object_id") or proposal.target_id
            target_char_id = proposal.parameters.get("recipient_id") or proposal.target_id
            if proposal.target_id and proposal.parameters.get("object_id"):
                obj_id = proposal.parameters["object_id"]
                target_char_id = proposal.target_id

            if not obj_id or not target_char_id:
                return False, "Give action requires both an object and a recipient"
            recipient = world.characters.get(target_char_id)
            if not recipient:
                return False, f"Recipient character '{target_char_id}' does not exist"
            if recipient.current_location_id != actor.current_location_id:
                return False, f"Recipient '{recipient.name}' is not in the same location as actor"
            return True, None

        elif action_type == ActionType.SPEAK:
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            if target_id:
                target = world.characters.get(target_id)
                if not target:
                    return False, f"Target character '{target_id}' does not exist"
                channel = proposal.parameters.get("channel") or proposal.parameters.get("communication_mechanism")
                if target.current_location_id != actor.current_location_id and not channel:
                    return False, f"Target character '{target.name}' is not in the same location (actor is in '{actor.current_location_id}', target is in '{target.current_location_id}')"
            return True, None

        elif action_type in (ActionType.INSPECT_OBJECT, ActionType.OBSERVE):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            if target_id:
                obj = world.objects.get(target_id)
                char = world.characters.get(target_id)
                if not obj and not char:
                    return False, f"Target '{target_id}' does not exist"
                target_loc = obj.location_id if obj else char.current_location_id
                if obj and obj.holder_id:
                    holder = world.characters.get(obj.holder_id)
                    target_loc = holder.current_location_id if holder else None
                if target_loc != actor.current_location_id and (obj and obj.holder_id != actor.id):
                    return False, f"Target '{target_id}' is not in the same location as actor"
            return True, None

        elif action_type in (ActionType.OPEN_OBJECT, ActionType.OPEN_DOOR, ActionType.CLOSE_OBJECT, ActionType.CLOSE_DOOR):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            if not target_id:
                return False, "Action requires a target object"
            obj = world.objects.get(target_id)
            if not obj:
                return False, f"Target object '{target_id}' does not exist"
            if obj.location_id != actor.current_location_id and obj.holder_id != actor.id:
                return False, f"Object '{target_id}' is not in actor's location"
            return True, None

        elif action_type == ActionType.INTERACT:
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            if target_id:
                obj = world.objects.get(target_id)
                if not obj:
                    return False, f"Target object '{target_id}' does not exist"
                if obj.location_id != actor.current_location_id and obj.holder_id != actor.id:
                    return False, f"Target object '{target_id}' is not accessible to actor"
            return True, None

        return True, None


class CanonGate:
    """Validates that an action does not contradict established canon facts.
    TODO: Phase 4 - Implement full CanonFact validation when StoryBlueprint is integrated.
    """

    test_rejection_reason: Optional[str] = None

    @classmethod
    def validate(cls, world: WorldState, proposal: ActionProposal) -> Tuple[bool, Optional[str]]:
        if cls.test_rejection_reason is not None:
            return False, cls.test_rejection_reason
        return True, None


class AffordanceGate:
    """Validates physical and contextual affordances for actions."""

    @staticmethod
    def validate(world: WorldState, proposal: ActionProposal) -> Tuple[bool, Optional[str]]:
        actor = world.characters.get(proposal.actor_id)
        if not actor:
            return False, f"Actor '{proposal.actor_id}' does not exist"

        action_type = proposal.action_type

        if action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            if not obj_id:
                return False, "Take action requires a target object_id"
            obj = world.objects.get(obj_id)
            if not obj:
                return False, f"Object '{obj_id}' does not exist"
            if not obj.portable:
                return False, f"Object '{obj_id}' ({obj.name}) is not portable"
            if obj.holder_id == actor.id:
                return False, f"Actor already holds object '{obj_id}'"
            if obj.holder_id is not None:
                holder = world.characters.get(obj.holder_id)
                holder_name = holder.name if holder else obj.holder_id
                return False, f"Object '{obj_id}' is currently held by '{holder_name}'"
            return True, None

        elif action_type in (ActionType.DROP_OBJECT, ActionType.DROP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            if not obj_id:
                return False, "Drop action requires a target object_id"
            obj = world.objects.get(obj_id)
            if not obj:
                return False, f"Object '{obj_id}' does not exist"
            if obj.holder_id != actor.id and obj_id not in actor.inventory:
                return False, f"Actor does not possess object '{obj_id}'"
            return True, None

        elif action_type in (ActionType.GIVE_OBJECT, ActionType.GIVE):
            obj_id = proposal.parameters.get("object_id") or proposal.target_id
            target_char_id = proposal.parameters.get("recipient_id") or proposal.target_id
            if proposal.target_id and proposal.parameters.get("object_id"):
                obj_id = proposal.parameters["object_id"]
                target_char_id = proposal.target_id
            if not obj_id or not target_char_id:
                return False, "Give action requires both an object and a recipient"
            obj = world.objects.get(obj_id)
            if not obj:
                return False, f"Object '{obj_id}' does not exist"
            if obj.holder_id != actor.id and obj_id not in actor.inventory:
                return False, f"Actor does not possess object '{obj_id}'"
            if target_char_id == actor.id:
                return False, "Actor cannot give an object to themselves"
            return True, None

        elif action_type in (ActionType.OPEN_OBJECT, ActionType.OPEN_DOOR):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            if not target_id:
                return False, "Open action requires a target object"
            obj = world.objects.get(target_id)
            if not obj:
                return False, f"Target object '{target_id}' does not exist"
            if obj.properties.get("locked") == "true" or obj.properties.get("locked") is True:
                return False, f"Object '{obj.name}' is locked"
            return True, None

        return True, None


class ActionValidator:
    """Deterministic validator for proposed character actions running through 4 gates."""

    def __init__(self):
        self.rejections: List[ActionRejection] = []

    def validate_proposal(
        self, world: WorldState, proposal: ActionProposal
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate an action proposal through all four gates.
        Returns (is_valid, error_message, gate_name).
        """
        # Gate 1: Knowledge Gate
        valid, err = KnowledgeGate.validate(world, proposal)
        if not valid:
            rejection = ActionRejection(
                tick=world.current_tick,
                actor_id=proposal.actor_id,
                proposal=proposal,
                gate="KnowledgeGate",
                reason=err or "Knowledge validation failed",
            )
            self.rejections.append(rejection)
            return False, err, "KnowledgeGate"

        # Gate 2: Spatial Gate
        valid, err = SpatialGate.validate(world, proposal)
        if not valid:
            rejection = ActionRejection(
                tick=world.current_tick,
                actor_id=proposal.actor_id,
                proposal=proposal,
                gate="SpatialGate",
                reason=err or "Spatial validation failed",
            )
            self.rejections.append(rejection)
            return False, err, "SpatialGate"

        # Gate 3: Canon Gate
        valid, err = CanonGate.validate(world, proposal)
        if not valid:
            rejection = ActionRejection(
                tick=world.current_tick,
                actor_id=proposal.actor_id,
                proposal=proposal,
                gate="CanonGate",
                reason=err or "Canon validation failed",
            )
            self.rejections.append(rejection)
            return False, err, "CanonGate"

        # Gate 4: Affordance Gate
        valid, err = AffordanceGate.validate(world, proposal)
        if not valid:
            rejection = ActionRejection(
                tick=world.current_tick,
                actor_id=proposal.actor_id,
                proposal=proposal,
                gate="AffordanceGate",
                reason=err or "Affordance validation failed",
            )
            self.rejections.append(rejection)
            return False, err, "AffordanceGate"

        return True, None, None

    @classmethod
    def validate(cls, world: WorldState, proposal: ActionProposal) -> Tuple[bool, Optional[str]]:
        """Class method for backward compatibility and static checks."""
        validator = cls()
        valid, err, _ = validator.validate_proposal(world, proposal)
        return valid, err


class ActionExecutor:
    """Executes validated ActionProposals, mutates WorldState, and logs Events"""

    def __init__(self, validator: Optional[ActionValidator] = None):
        self.validator = validator or ActionValidator()

    def execute(
        self_or_world,
        world_or_proposal=None,
        proposal_or_recorder=None,
        recorder_or_validator=None,
        validator=None,
    ) -> ActionResult:
        """Execute a validated ActionProposal against WorldState.
        Supports both instance call `executor.execute(world, proposal, recorder)`
        and static/class call `ActionExecutor.execute(world, proposal, recorder)`.
        """
        if isinstance(self_or_world, ActionExecutor):
            self = self_or_world
            world = world_or_proposal
            proposal = proposal_or_recorder
            recorder = recorder_or_validator
            val = validator or self.validator
        else:
            self = None
            world = self_or_world
            proposal = world_or_proposal
            recorder = proposal_or_recorder
            val = recorder_or_validator or ActionValidator()

        is_valid, error_msg, gate_name = val.validate_proposal(world, proposal)
        if not is_valid:
            return ActionResult(
                proposal_id=proposal.id,
                status=ActionResultStatus.INVALID,
                tick_resolved=world.current_tick,
                events_created=[],
                error_message=error_msg,
                metadata={"actor_id": proposal.actor_id, "gate": gate_name},
            )

        actor = world.characters[proposal.actor_id]
        action_type = proposal.action_type
        events_created = []

        # Resolve causality:
        # 1. prior_event_id -> append directly
        # 2. knowledge_item_id -> resolve to KnowledgeItem.acquired_at_event (if any)
        # 3. goal_id -> resolve to goal establishing event (if any)
        caused_by: List[str] = []
        if proposal.motivation:
            if proposal.motivation.prior_event_id:
                if proposal.motivation.prior_event_id not in caused_by:
                    caused_by.append(proposal.motivation.prior_event_id)
            if proposal.motivation.knowledge_item_id:
                k_item = actor.knows(proposal.motivation.knowledge_item_id)
                if k_item and k_item.acquired_at_event:
                    if k_item.acquired_at_event not in caused_by:
                        caused_by.append(k_item.acquired_at_event)
            if proposal.motivation.goal_id:
                goal = world.goals.get(proposal.motivation.goal_id)
                if goal and getattr(goal, "created_at_event", None):
                    if goal.created_at_event not in caused_by:
                        caused_by.append(goal.created_at_event)

        motivation_snapshot = proposal.motivation.model_dump() if proposal.motivation else None

        if action_type == ActionType.WAIT:
            event = recorder.record_event(
                event_type=EventType.OTHER,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} waits and observes the surroundings.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"action": "wait", "reason": proposal.reason},
            )
            events_created.append(event.id)

        elif action_type == ActionType.MOVE:
            dest_id = proposal.location_id or proposal.parameters.get("destination_id") or proposal.parameters.get("to")
            from_loc_id = actor.current_location_id
            from_loc = world.locations.get(from_loc_id)
            from_name = from_loc.name if from_loc else (from_loc_id or "unknown")
            dest_loc = world.locations[dest_id]
            actor.current_location_id = dest_id
            event = recorder.record_event(
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=[actor.id],
                location_id=dest_id,
                description=f"{actor.name} moved from {from_name} to {dest_loc.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={
                    "from_location": from_loc_id,
                    "to_location": dest_id,
                    "from_location_name": from_name,
                    "to_location_name": dest_loc.name,
                },
            )
            events_created.append(event.id)

        elif action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            obj = world.objects[obj_id]
            obj.holder_id = actor.id
            obj.location_id = None
            obj.last_changed_tick = world.current_tick
            if obj.id not in actor.inventory:
                actor.inventory.append(obj.id)
            event = recorder.record_event(
                event_type=EventType.OBJECT_PICKED_UP,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} picked up the {obj.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"object_id": obj.id, "object_name": obj.name},
            )
            events_created.append(event.id)

        elif action_type in (ActionType.DROP_OBJECT, ActionType.DROP):
            obj_id = proposal.target_id or proposal.parameters.get("object_id")
            obj = world.objects[obj_id]
            obj.holder_id = None
            obj.location_id = actor.current_location_id
            obj.last_changed_tick = world.current_tick
            if obj.id in actor.inventory:
                actor.inventory.remove(obj.id)
            event = recorder.record_event(
                event_type=EventType.OBJECT_DROPPED,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} dropped the {obj.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"object_id": obj.id, "object_name": obj.name},
            )
            events_created.append(event.id)

        elif action_type in (ActionType.GIVE_OBJECT, ActionType.GIVE):
            obj_id = proposal.parameters.get("object_id") or proposal.target_id
            target_char_id = proposal.parameters.get("recipient_id") or proposal.target_id
            if proposal.target_id and proposal.parameters.get("object_id"):
                obj_id = proposal.parameters["object_id"]
                target_char_id = proposal.target_id
            obj = world.objects[obj_id]
            recipient = world.characters[target_char_id]

            obj.holder_id = recipient.id
            obj.last_changed_tick = world.current_tick
            if obj.id in actor.inventory:
                actor.inventory.remove(obj.id)
            if obj.id not in recipient.inventory:
                recipient.inventory.append(obj.id)

            event = recorder.record_event(
                event_type=EventType.OBJECT_GIVEN,
                actor_ids=[actor.id, recipient.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} gave the {obj.name} to {recipient.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={
                    "object_id": obj.id,
                    "giver_id": actor.id,
                    "recipient_id": recipient.id,
                },
            )
            events_created.append(event.id)

        elif action_type == ActionType.SPEAK:
            dialogue = proposal.parameters.get("dialogue") or proposal.parameters.get("message") or proposal.reason or "..."
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            speech_act = proposal.parameters.get("speech_act") or proposal.parameters.get("social_intent") or "speak"
            topic = proposal.parameters.get("topic", "the situation")
            claim = proposal.parameters.get("claim", dialogue)
            truth_status = proposal.parameters.get("truth_status", "uncertain")

            actor_ids = [actor.id]
            if target_id and target_id in world.characters:
                actor_ids.append(target_id)
                target_name = world.characters[target_id].name
                desc = f"{actor.name} said to {target_name}: \"{dialogue}\""
                target_char = world.characters[target_id]
                fact_id = f"fact_dlg_{world.current_tick}_{actor.id}_{target_id}"
                if fact_id not in world.facts:
                    fact = DiscoveredFact(
                        id=fact_id,
                        statement=f"{actor.name} stated: \"{dialogue}\" regarding {topic}",
                        source="dialogue",
                        confidence=0.75,
                        discovered_by=target_id,
                        tick=world.current_tick,
                        related_entities=[actor.id, target_id],
                        metadata={
                            "speaker_id": actor.id,
                            "speech_act": speech_act,
                            "topic": topic,
                            "truth_status": truth_status,
                        },
                    )
                    world.facts[fact_id] = fact
                    if fact_id not in target_char.known_facts:
                        target_char.known_facts.append(fact_id)
            else:
                desc = f"{actor.name} said: \"{dialogue}\""

            event = recorder.record_event(
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=actor_ids,
                location_id=actor.current_location_id,
                description=desc,
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={
                    "speaker_id": actor.id,
                    "target_id": target_id,
                    "dialogue": dialogue,
                    "speech_act": speech_act,
                    "topic": topic,
                    "claim": claim,
                    "truth_status": truth_status,
                },
            )
            events_created.append(event.id)

        elif action_type in (ActionType.INSPECT_OBJECT, ActionType.OBSERVE):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            target_name = target_id
            target_obj = world.objects.get(target_id)
            target_char = world.characters.get(target_id)
            fact_created = False
            fact_id = None

            if target_obj:
                target_name = target_obj.name
                if actor.id not in target_obj.inspected_by:
                    target_obj.inspected_by.append(actor.id)
                fact_id = f"fact_{world.current_tick}_{actor.id}_{target_obj.id}"
                if fact_id not in world.facts:
                    fact_stmt = f"{target_obj.name}: {target_obj.description or 'Observed in detail.'}"
                    if target_obj.properties:
                        props_str = ", ".join(f"{k}: {v}" for k, v in target_obj.properties.items())
                        fact_stmt += f" ({props_str})"
                    discovered_fact = DiscoveredFact(
                        id=fact_id,
                        statement=fact_stmt,
                        source="inspection",
                        confidence=1.0,
                        discovered_by=actor.id,
                        tick=world.current_tick,
                        related_entities=[target_obj.id, actor.id],
                        metadata={"object_id": target_obj.id},
                    )
                    world.facts[fact_id] = discovered_fact
                    if fact_id not in actor.known_facts:
                        actor.known_facts.append(fact_id)
                    fact_created = True
            elif target_char:
                target_name = target_char.name

            event = recorder.record_event(
                event_type=EventType.CHARACTER_OBSERVED,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} closely examined {target_name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={
                    "target_id": target_id,
                    "target_name": target_name,
                    "fact_discovered": fact_created,
                    "fact_id": fact_id,
                },
            )
            events_created.append(event.id)

        elif action_type in (ActionType.OPEN_OBJECT, ActionType.OPEN_DOOR):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            obj = world.objects[target_id]
            obj.properties["open"] = "true"
            event = recorder.record_event(
                event_type=EventType.DOOR_OPENED,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} opened the {obj.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"object_id": obj.id, "object_name": obj.name},
            )
            events_created.append(event.id)

        elif action_type in (ActionType.CLOSE_OBJECT, ActionType.CLOSE_DOOR):
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            obj = world.objects[target_id]
            obj.properties["open"] = "false"
            event = recorder.record_event(
                event_type=EventType.DOOR_CLOSED,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} closed the {obj.name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"object_id": obj.id, "object_name": obj.name},
            )
            events_created.append(event.id)

        elif action_type == ActionType.INTERACT:
            target_id = proposal.target_id or proposal.parameters.get("target_id")
            target_name = world.objects[target_id].name if target_id in world.objects else target_id
            event = recorder.record_event(
                event_type=EventType.OTHER,
                actor_ids=[actor.id],
                location_id=actor.current_location_id,
                description=f"{actor.name} interacted with {target_name}.",
                caused_by=caused_by,
                motivation=motivation_snapshot,
                metadata={"target_id": target_id, "interaction": proposal.parameters},
            )
            events_created.append(event.id)

        return ActionResult(
            proposal_id=proposal.id,
            status=ActionResultStatus.SUCCESS,
            tick_resolved=world.current_tick,
            events_created=events_created,
            metadata={"actor_id": actor.id, "action_type": action_type.value},
        )
