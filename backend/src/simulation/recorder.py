"""Event recorder for logging immutable simulation events into canonical world state"""
import uuid
from typing import List, Dict, Any, Optional
from ..domain import Event, EventType, WorldState


class EventRecorder:
    """Creates immutable events and registers them canonically in WorldState"""

    def __init__(self, world: WorldState):
        self.world = world
        self._counter = 0

    def record_event(
        self,
        event_type: EventType,
        description: str,
        actor_ids: Optional[List[str]] = None,
        location_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Create and canonically register an immutable Event"""
        self._counter += 1
        event_id = f"evt_{self.world.current_tick}_{self._counter}_{uuid.uuid4().hex[:6]}"
        event = Event(
            id=event_id,
            tick=self.world.current_tick,
            event_type=event_type,
            actor_ids=actor_ids or [],
            location_id=location_id,
            description=description,
            metadata=metadata or {},
        )
        self.world.events[event.id] = event
        return event

    def get_events_for_tick(self, tick: int) -> List[Event]:
        """Retrieve all events recorded at a specific tick"""
        return [evt for evt in self.world.events.values() if evt.tick == tick]

    def get_all_events(self) -> List[Event]:
        """Retrieve all events in chronological order"""
        return sorted(self.world.events.values(), key=lambda e: (e.tick, e.id))
