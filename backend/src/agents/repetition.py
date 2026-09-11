"""Action repetition tracking and penalty calculation for D3 Story Lab."""

from __future__ import annotations
from typing import Dict, List, Optional
from src.domain.action import ActionType


class RepetitionTracker:
    """Tracks recent action history per actor to prevent repetitive and passive loops."""

    def __init__(self, history_limit: int = 10):
        self.history_limit = history_limit
        self.actor_history: Dict[str, List[Dict[str, Optional[str]]]] = {}

    def record_action(
        self,
        actor_id: str,
        action_type: ActionType,
        target_id: Optional[str] = None,
        location_id: Optional[str] = None,
        intent: Optional[str] = None,
        topic: Optional[str] = None,
        speech_act: Optional[str] = None,
        tick: int = 0,
    ):
        if actor_id not in self.actor_history:
            self.actor_history[actor_id] = []

        entry = {
            "action_type": action_type.value,
            "target_id": target_id,
            "location_id": location_id,
            "intent": intent,
            "topic": topic,
            "speech_act": speech_act,
            "tick": tick,
        }
        self.actor_history[actor_id].append(entry)
        if len(self.actor_history[actor_id]) > self.history_limit:
            self.actor_history[actor_id].pop(0)

    def get_penalty(
        self,
        actor_id: str,
        action_type: ActionType,
        target_id: Optional[str] = None,
        location_id: Optional[str] = None,
        topic: Optional[str] = None,
        speech_act: Optional[str] = None,
    ) -> float:
        history = self.actor_history.get(actor_id, [])
        penalty = 0.0

        # Severe penalty for repeated WAIT actions
        if action_type == ActionType.WAIT:
            penalty += 0.4
            consecutive_waits = 0
            for entry in reversed(history):
                if entry["action_type"] == ActionType.WAIT.value:
                    consecutive_waits += 1
                else:
                    break
            if consecutive_waits >= 1:
                penalty += 0.8 * consecutive_waits

        if not history:
            return round(penalty, 3)

        # 1. Object oscillation prevention (pickup/drop loop in same location)
        if action_type in (ActionType.DROP_OBJECT, ActionType.DROP) and target_id:
            # Check if actor recently picked up this object without moving
            recent_moves_since_pickup = 0
            found_pickup = False
            for entry in reversed(history[-4:]):
                if entry["action_type"] == ActionType.MOVE.value:
                    recent_moves_since_pickup += 1
                if entry["action_type"] in (ActionType.TAKE_OBJECT.value, ActionType.PICKUP.value) and entry["target_id"] == target_id:
                    found_pickup = True
                    break
            if found_pickup and recent_moves_since_pickup == 0:
                penalty += 1.8  # Severely penalize dropping an item immediately where it was just picked up

        if action_type in (ActionType.TAKE_OBJECT, ActionType.PICKUP) and target_id:
            # Check if actor recently dropped this object in this room
            found_drop = any(
                e["action_type"] in (ActionType.DROP_OBJECT.value, ActionType.DROP.value) and e["target_id"] == target_id
                for e in history[-3:]
            )
            if found_drop:
                penalty += 1.8  # Severely penalize picking up what was just dropped

        # 2. Repeated speech topic or speech act
        if action_type == ActionType.SPEAK and target_id:
            recent_matches = 0
            for entry in reversed(history[-4:]):
                if entry["action_type"] == ActionType.SPEAK.value and entry["target_id"] == target_id:
                    if topic and entry.get("topic") == topic:
                        recent_matches += 1
                    if speech_act and entry.get("speech_act") == speech_act:
                        recent_matches += 1
            if recent_matches > 0:
                penalty += 0.7 * recent_matches

        # 3. Repeated inspection of same object
        if action_type in (ActionType.INSPECT_OBJECT, ActionType.OBSERVE) and target_id:
            inspected_count = sum(
                1 for e in history
                if e["action_type"] in (ActionType.INSPECT_OBJECT.value, ActionType.OBSERVE.value) and e["target_id"] == target_id
            )
            if inspected_count >= 1:
                penalty += 1.2 * inspected_count

        # 4. Repeating the exact same non-wait action + target
        if action_type != ActionType.WAIT:
            last = history[-1]
            if last["action_type"] == action_type.value and last["target_id"] == target_id:
                penalty += 0.55

            if len(history) >= 2:
                second_last = history[-2]
                if second_last["action_type"] == action_type.value and second_last["target_id"] == target_id:
                    penalty += 0.35

        # 5. Room ping-pong penalty (A -> B -> A)
        if action_type == ActionType.MOVE and location_id:
            recent_moves = [
                e["location_id"] for e in history
                if e["action_type"] == ActionType.MOVE.value and e.get("location_id")
            ]
            if recent_moves:
                if len(recent_moves) >= 2 and recent_moves[-2] == location_id:
                    penalty += 1.2
                elif location_id in recent_moves[-3:]:
                    penalty += 0.7

        return round(penalty, 3)

    def get_consecutive_wait_count(self, actor_id: str) -> int:
        history = self.actor_history.get(actor_id, [])
        count = 0
        for entry in reversed(history):
            if entry["action_type"] == ActionType.WAIT.value:
                count += 1
            else:
                break
        return count
