"""Object affordance resolution system for D3 Story Lab.

Exposes semantic affordances for visible and interactable objects based on
object properties, naming, portability, and situational context.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character
from src.domain.action import ActionType


class ObjectAffordance:
    """A semantic affordance representing an available interaction with an object."""

    def __init__(
        self,
        action_type: ActionType,
        target_id: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        utility_hint: float = 0.5,
    ):
        self.action_type = action_type
        self.target_id = target_id
        self.description = description
        self.parameters = parameters or {}
        self.utility_hint = utility_hint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "target_id": self.target_id,
            "description": self.description,
            "parameters": self.parameters,
            "utility_hint": self.utility_hint,
        }


class ObjectAffordanceResolver:
    """Determines valid semantic affordances for objects accessible to a character."""

    @staticmethod
    def resolve_affordances(
        obj: WorldObject,
        actor: Character,
        location: Optional[Location] = None,
    ) -> List[ObjectAffordance]:
        affordances: List[ObjectAffordance] = []
        name_lower = obj.name.lower()
        desc_lower = obj.description.lower()
        props = obj.properties or {}
        is_held_by_actor = (obj.holder_id == actor.id)
        is_unheld = (obj.holder_id is None)

        # 1. Inspection (examine object / read contents)
        affordances.append(
            ObjectAffordance(
                action_type=ActionType.INSPECT_OBJECT,
                target_id=obj.id,
                description=f"Inspect and examine {obj.name}",
                utility_hint=0.6,
            )
        )

        # 2. Documents / Ledgers / Evidence / Confidential Records
        if any(w in name_lower or w in desc_lower for w in ["document", "ledger", "file", "letter", "dossier", "paper", "card", "evidence"]):
            if is_unheld and obj.portable:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.TAKE_OBJECT,
                        target_id=obj.id,
                        description=f"Take and secure {obj.name}",
                        utility_hint=0.85,
                    )
                )
            elif is_held_by_actor:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.DROP_OBJECT,
                        target_id=obj.id,
                        description=f"Stash or conceal {obj.name}",
                        utility_hint=0.5,
                    )
                )

        # 3. Communication / Electronic Devices (Phone, Terminal, Radio, Computer)
        elif any(w in name_lower or w in desc_lower for w in ["phone", "terminal", "radio", "intercom", "computer", "recorder"]):
            affordances.append(
                ObjectAffordance(
                    action_type=ActionType.INTERACT,
                    target_id=obj.id,
                    description=f"Use/activate {obj.name}",
                    parameters={"mode": "use"},
                    utility_hint=0.75,
                )
            )
            if is_unheld and obj.portable:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.TAKE_OBJECT,
                        target_id=obj.id,
                        description=f"Pick up {obj.name}",
                        utility_hint=0.7,
                    )
                )

        # 4. Containers / Storage (Safe, Suitcase, Briefcase, Cabinet, Drawer, Box, Desk)
        elif any(w in name_lower or w in desc_lower for w in ["safe", "suitcase", "briefcase", "cabinet", "drawer", "box", "desk", "vault"]):
            is_open = props.get("open") == "true"
            is_locked = props.get("locked") == "true"

            if not is_open and not is_locked:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.OPEN_OBJECT,
                        target_id=obj.id,
                        description=f"Open {obj.name}",
                        utility_hint=0.8,
                    )
                )
            elif is_open:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.CLOSE_OBJECT,
                        target_id=obj.id,
                        description=f"Close {obj.name}",
                        utility_hint=0.5,
                    )
                )

            if is_unheld and obj.portable:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.TAKE_OBJECT,
                        target_id=obj.id,
                        description=f"Take {obj.name}",
                        utility_hint=0.65,
                    )
                )

        # 5. Doors / Portals
        elif any(w in name_lower or w in desc_lower for w in ["door", "gate", "portal", "exit"]):
            is_open = props.get("open") == "true"
            is_locked = props.get("locked") == "true"
            if not is_open and not is_locked:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.OPEN_OBJECT,
                        target_id=obj.id,
                        description=f"Open {obj.name}",
                        utility_hint=0.7,
                    )
                )
            elif is_open:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.CLOSE_OBJECT,
                        target_id=obj.id,
                        description=f"Close {obj.name}",
                        utility_hint=0.6,
                    )
                )

        # 6. Generic Portable Objects
        else:
            if is_unheld and obj.portable:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.TAKE_OBJECT,
                        target_id=obj.id,
                        description=f"Pick up {obj.name}",
                        utility_hint=0.5,
                    )
                )
            elif is_held_by_actor:
                affordances.append(
                    ObjectAffordance(
                        action_type=ActionType.DROP_OBJECT,
                        target_id=obj.id,
                        description=f"Drop {obj.name}",
                        utility_hint=0.3,
                    )
                )

        return affordances
