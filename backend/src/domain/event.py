"""Event model representing objective history"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class EventType(str, Enum):
    """Types of events that can occur in the simulation"""

    CHARACTER_MOVED = "character_moved"
    OBJECT_PICKED_UP = "object_picked_up"
    OBJECT_DROPPED = "object_dropped"
    CHARACTER_SPOKE = "character_spoke"
    OBJECT_GIVEN = "object_given"
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    CHARACTER_OBSERVED = "character_observed"
    EMOTION_CHANGED = "emotion_changed"
    BELIEF_FORMED = "belief_formed"
    MEMORY_CREATED = "memory_created"
    RELATIONSHIP_CHANGED = "relationship_changed"
    OTHER = "other"


class Event(BaseModel):
    """Immutable record of what actually happened"""

    id: str = Field(..., description="Unique event ID")
    tick: int = Field(..., ge=0, description="Simulation tick when event occurred")
    event_type: EventType
    actor_ids: List[str] = Field(
        default_factory=list, description="IDs of characters involved"
    )
    location_id: Optional[str] = Field(
        None, description="Location where event occurred"
    )
    description: str = Field(..., description="Human-readable description")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event data"
    )

    @property
    def from_location(self) -> Optional[str]:
        """Source location ID if movement event"""
        return self.metadata.get("from_location")

    @property
    def to_location(self) -> Optional[str]:
        """Destination location ID if movement event"""
        return self.metadata.get("to_location")

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "id": "evt_001",
                "tick": 1,
                "event_type": "character_moved",
                "actor_ids": ["char_arjun"],
                "location_id": "loc_room307",
                "description": "Arjun moved to Hotel Room 307",
                "metadata": {"from_location": "lobby", "to_location": "room_307"},
            }
        },
    )
