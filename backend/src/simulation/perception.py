"""Perception and knowledge boundary system (Milestone 3)"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from ..domain import WorldState, Event, EventType


class VisibleCharacter(BaseModel):
    """Observable outward details of a character in the same location"""

    id: str
    name: str
    role: str
    description: Optional[str] = None
    inventory: List[str] = Field(default_factory=list)
    # Notice: NO secrets, NO private beliefs, NO memories, NO private goals

    model_config = ConfigDict(frozen=True)


class VisibleObject(BaseModel):
    """Observable object details in the character's vicinity"""

    id: str
    name: str
    description: Optional[str] = None
    holder_id: Optional[str] = None
    portable: bool = True
    properties: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ObservedEvent(BaseModel):
    """An event observed from the actor's perspective"""

    id: str
    tick: int
    event_type: EventType
    description: str
    location_id: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class Observation(BaseModel):
    """Complete, strictly bounded perception available to a character at a specific tick"""

    character_id: str
    tick: int
    current_location_id: Optional[str] = None
    current_location_name: Optional[str] = None
    current_location_description: Optional[str] = None
    connected_locations: List[str] = Field(default_factory=list)
    visible_characters: List[VisibleCharacter] = Field(default_factory=list)
    visible_objects: List[VisibleObject] = Field(default_factory=list)
    recent_events: List[ObservedEvent] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class KnowledgeFilter:
    """Constructs character-specific observations respecting strict knowledge privacy"""

    @staticmethod
    def build_observation(
        world: WorldState, character_id: str, event_horizon: int = 5
    ) -> Observation:
        """Create an Observation strictly containing only what the character can perceive"""
        char = world.characters.get(character_id)
        if not char:
            return Observation(character_id=character_id, tick=world.current_tick)

        loc_id = char.current_location_id
        loc = world.locations.get(loc_id) if loc_id else None

        # 1. Co-located characters (excluding the character themselves, and stripping all private state)
        visible_chars: List[VisibleCharacter] = []
        if loc_id:
            for other_id, other_char in world.characters.items():
                if other_id != character_id and other_char.current_location_id == loc_id:
                    visible_chars.append(
                        VisibleCharacter(
                            id=other_char.id,
                            name=other_char.name,
                            role=other_char.role,
                            description=other_char.description,
                            inventory=list(other_char.inventory),
                        )
                    )

        # 2. Visible objects (located in the room or held by co-located characters)
        visible_objs: List[VisibleObject] = []
        if loc_id:
            co_located_char_ids = {other.id for other in visible_chars} | {character_id}
            for obj in world.objects.values():
                if obj.location_id == loc_id or (obj.holder_id and obj.holder_id in co_located_char_ids):
                    visible_objs.append(
                        VisibleObject(
                            id=obj.id,
                            name=obj.name,
                            description=obj.description,
                            holder_id=obj.holder_id,
                            portable=obj.portable,
                            properties=dict(obj.properties),
                        )
                    )

        # 3. Perceivable events (within horizon, occurring in the same location or involving character)
        min_tick = max(0, world.current_tick - event_horizon)
        perceivable_events: List[ObservedEvent] = []
        for evt in world.events.values():
            if evt.tick >= min_tick:
                # Perceived if co-located or if character is an actor
                can_perceive = False
                if loc_id and evt.location_id == loc_id:
                    can_perceive = True
                elif character_id in evt.actor_ids:
                    can_perceive = True

                if can_perceive:
                    perceivable_events.append(
                        ObservedEvent(
                            id=evt.id,
                            tick=evt.tick,
                            event_type=evt.event_type,
                            description=evt.description,
                            location_id=evt.location_id,
                        )
                    )

        perceivable_events.sort(key=lambda e: (e.tick, e.id))

        return Observation(
            character_id=character_id,
            tick=world.current_tick,
            current_location_id=loc.id if loc else None,
            current_location_name=loc.name if loc else None,
            current_location_description=loc.description if loc else None,
            connected_locations=list(loc.connected_locations) if loc else [],
            visible_characters=visible_chars,
            visible_objects=visible_objs,
            recent_events=perceivable_events,
        )
