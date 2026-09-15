"""Event recorder for logging immutable simulation events into canonical world state"""
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from ..domain import Event, EventType, EventLog, WorldState


class EventRecorder:
    """Creates immutable events and registers them canonically in WorldState"""

    def __init__(self, world: WorldState, seed: Optional[int] = None):
        self.world = world
        self._counter = 0
        self.seed = seed

    def record_event(
        self,
        event_type: EventType,
        description: str,
        actor_ids: Optional[List[str]] = None,
        location_id: Optional[str] = None,
        caused_by: Optional[List[str]] = None,
        motivation: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Create and canonically register an immutable Event"""
        self._counter += 1
        if self.seed is not None:
            slug = hashlib.sha256(
                f"{self.seed}:{self.world.current_tick}:{self._counter}:{event_type}:{description}".encode()
            ).hexdigest()[:6]
        else:
            slug = uuid.uuid4().hex[:6]
        event_id = f"evt_{self.world.current_tick}_{self._counter}_{slug}"
        event = Event(
            id=event_id,
            tick=self.world.current_tick,
            event_type=event_type,
            actor_ids=actor_ids or [],
            location_id=location_id,
            description=description,
            caused_by=caused_by or [],
            motivation=motivation,
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

    def get_event_log(self) -> EventLog:
        """Retrieve all events as an immutable EventLog"""
        return EventLog(events=self.get_all_events())
