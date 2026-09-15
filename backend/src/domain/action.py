"""Action proposal and result models"""
from enum import Enum
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class Motivation(BaseModel):
    """The causal and psychological reason driving a proposed action."""
    kind: Literal["PURSUE_GOAL", "REACT_TO_EVENT", "ACT_ON_KNOWLEDGE", "AVOID_THREAT"]
    knowledge_item_id: Optional[str] = None
    prior_event_id: Optional[str] = None
    goal_id: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ActionType(str, Enum):
    """Types of actions characters can propose"""

    WAIT = "wait"
    MOVE = "move"
    SPEAK = "speak"
    TAKE_OBJECT = "take_object"
    DROP_OBJECT = "drop_object"
    GIVE_OBJECT = "give_object"
    INSPECT_OBJECT = "inspect_object"
    OPEN_OBJECT = "open_object"
    CLOSE_OBJECT = "close_object"
    INTERACT = "interact"
    OBSERVE = "observe"
    # Legacy / alias types for backwards compatibility
    PICKUP = "pickup"
    DROP = "drop"
    GIVE = "give"
    OPEN_DOOR = "open_door"
    CLOSE_DOOR = "close_door"
    OTHER = "other"


class ActionProposal(BaseModel):
    """A proposed action by an actor (does NOT mutate world state)"""

    id: str = Field(..., description="Unique proposal ID")
    actor_id: str = Field(..., description="Character proposing the action")
    action_type: ActionType
    target_id: Optional[str] = Field(None, description="Object or character ID targeted")
    location_id: Optional[str] = Field(None, description="Location involved")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters"
    )
    tick_proposed: int = Field(..., ge=0, description="Simulation tick when proposed")
    motivation: Motivation = Field(..., description="Mandatory motivation driving this proposal")
    expected_outcome: str = Field(default="", description="Expected outcome of the action")
    reason: Optional[str] = Field(
        None, description="Why the actor proposes this action"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "act_prop_001",
                "actor_id": "char_arjun",
                "action_type": "move",
                "target_id": None,
                "location_id": "loc_hallway",
                "parameters": {"from": "loc_room307", "to": "loc_hallway"},
                "tick_proposed": 1,
                "motivation": {"kind": "PURSUE_GOAL", "goal_id": "goal_search"},
                "expected_outcome": "Reach the hallway",
                "reason": "Search for Maya",
            }
        }
    )


class ActionRejection(BaseModel):
    """Immutable record of an action proposal rejected by a validator gate."""
    tick: int = Field(..., ge=0, description="Simulation tick when rejected")
    actor_id: str = Field(..., description="Actor who proposed the rejected action")
    proposal: ActionProposal = Field(..., description="The rejected ActionProposal")
    gate: str = Field(..., description="Name of the gate that rejected the action")
    reason: str = Field(..., description="Human-readable reason for rejection")

    model_config = ConfigDict(frozen=True)


class ActionResultStatus(str, Enum):
    """Status of an action result"""

    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    INVALID = "invalid"


class ActionResult(BaseModel):
    """Result of processing an action proposal"""

    proposal_id: str = Field(..., description="ID of the proposal this results from")
    status: ActionResultStatus
    tick_resolved: int = Field(..., ge=0, description="Tick when action was resolved")
    events_created: List[str] = Field(
        default_factory=list,
        description="Event IDs that resulted from this action",
    )
    error_message: Optional[str] = Field(
        None, description="If failed/invalid, why did it fail"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional result data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "proposal_id": "act_prop_001",
                "status": "success",
                "tick_resolved": 1,
                "events_created": ["evt_001"],
                "error_message": None,
                "metadata": {},
            }
        }
    )
