"""CharacterWorldView and project_view: The Omniscience Firewall for D3 Story Lab."""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.goal import Goal
from src.domain.proposition import KnowledgeItem
from src.domain.event import Event


class ObservableCharacter(BaseModel):
    """Observable external state of a character perceivable by another character."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    role: str
    location_id: Optional[str] = None
    inventory: List[str] = Field(default_factory=list)


class ObservableObject(BaseModel):
    """Observable properties of an object perceivable in the local environment."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    description: str
    location_id: Optional[str] = None
    holder_id: Optional[str] = None
    portable: bool = True
    properties: Dict[str, Any] = Field(default_factory=dict)
    is_secret: bool = False


class ObservableLocation(BaseModel):
    """Observable properties of a reachable or current location."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    description: Optional[str] = None
    connected_locations: List[str] = Field(default_factory=list)


class CharacterWorldView(BaseModel):
    """Subjective, firewalled world projection for a specific character.

    INVARIANT: Contains ONLY what this character has observed, inferred, remembered,
    or been told. The canonical PropositionRegistry and other characters' private
    knowledge are strictly excluded.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    character_id: str
    character_name: str
    current_location_id: Optional[str] = None
    current_tick: int
    knowledge: Dict[str, KnowledgeItem] = Field(default_factory=dict)
    goals: List[Goal] = Field(default_factory=list)
    emotional_state: EmotionalState
    relationship_trust: Dict[str, float] = Field(default_factory=dict)
    perceivable_characters: Dict[str, ObservableCharacter] = Field(default_factory=dict)
    perceivable_objects: Dict[str, ObservableObject] = Field(default_factory=dict)
    current_location: Optional[ObservableLocation] = None
    reachable_locations: Dict[str, ObservableLocation] = Field(default_factory=dict)
    recent_events: List[Event] = Field(default_factory=list)

    def knows(self, proposition_id: str) -> Optional[KnowledgeItem]:
        """Retrieve held subjective KnowledgeItem for a proposition, or None."""
        return self.knowledge.get(proposition_id)

    def holds_secret(self, secret_id_or_prop_id: str) -> bool:
        """Check if character holds knowledge of this secret proposition."""
        return secret_id_or_prop_id in self.knowledge


def project_view(world: WorldState, character: Character) -> CharacterWorldView:
    """Pure projection function creating a firewalled CharacterWorldView from WorldState.

    Never exposes:
    1. The canonical WorldState.propositions registry.
    2. KnowledgeItem instances held by any other character.
    3. Entities or state in non-visible locations.
    4. Secrets that this character does not subjectively hold.
    """
    loc_id = character.current_location_id
    current_loc = world.locations.get(loc_id) if loc_id else None

    # 1. Observable co-present characters (observable state ONLY - no knowledge/secrets/beliefs)
    perceivable_characters: Dict[str, ObservableCharacter] = {}
    if loc_id:
        for other in world.characters.values():
            if other.id != character.id and other.current_location_id == loc_id:
                perceivable_characters[other.id] = ObservableCharacter(
                    id=other.id,
                    name=other.name,
                    role=other.role,
                    location_id=other.current_location_id,
                    inventory=list(other.inventory),
                )

    # 2. Observable objects in current location or held by self / co-present characters
    perceivable_objects: Dict[str, ObservableObject] = {}
    if loc_id:
        for obj in world.objects.values():
            in_same_loc = (obj.location_id == loc_id)
            held_by_self = (obj.holder_id == character.id)
            held_by_copresent = bool(obj.holder_id and obj.holder_id in perceivable_characters)

            if in_same_loc or held_by_self or held_by_copresent:
                # If an object is marked secret and not held by self, ensure actor holds knowledge of it
                is_obj_secret = bool(getattr(obj, "is_secret", False) or (obj.properties and obj.properties.get("is_secret")))
                if is_obj_secret and not held_by_self:
                    if not character.knows(obj.id) and not character.knows(f"prop_{obj.id}"):
                        continue

                perceivable_objects[obj.id] = ObservableObject(
                    id=obj.id,
                    name=obj.name,
                    description=obj.description,
                    location_id=obj.location_id,
                    holder_id=obj.holder_id,
                    portable=obj.portable,
                    properties=dict(obj.properties or {}),
                    is_secret=is_obj_secret,
                )

    # 3. Current and reachable locations
    obs_current_loc: Optional[ObservableLocation] = None
    reachable_locations: Dict[str, ObservableLocation] = {}
    if current_loc:
        obs_current_loc = ObservableLocation(
            id=current_loc.id,
            name=current_loc.name,
            description=current_loc.description,
            connected_locations=list(current_loc.connected_locations),
        )
        for conn_id in current_loc.connected_locations:
            conn_loc = world.locations.get(conn_id)
            if conn_loc:
                reachable_locations[conn_id] = ObservableLocation(
                    id=conn_loc.id,
                    name=conn_loc.name,
                    description=conn_loc.description,
                    connected_locations=list(conn_loc.connected_locations),
                )

    # 4. Goals and relationships
    char_goals = world.get_character_goals(character.id)
    trust_map: Dict[str, float] = {}
    for r in world.relationships.values():
        if r.character_a_id == character.id:
            trust_map[r.character_b_id] = r.trust
        elif r.character_b_id == character.id:
            trust_map[r.character_a_id] = r.trust

    # 5. Recent events perceivable by this character (in same location or involving self)
    perceived_events: List[Event] = []
    for ev in world.events.values():
        at_same_loc = (loc_id is not None and ev.location_id == loc_id)
        is_actor = (character.id in ev.actor_ids)
        if at_same_loc or is_actor:
            perceived_events.append(ev)

    # Sort events chronologically and take last 10
    perceived_events.sort(key=lambda e: (e.tick, e.id))
    recent_perceived = perceived_events[-10:]

    return CharacterWorldView(
        character_id=character.id,
        character_name=character.name,
        current_location_id=character.current_location_id,
        current_tick=world.current_tick,
        knowledge=dict(character.knowledge),
        goals=list(char_goals),
        emotional_state=character.emotional_state,
        relationship_trust=trust_map,
        perceivable_characters=perceivable_characters,
        perceivable_objects=perceivable_objects,
        current_location=obs_current_loc,
        reachable_locations=reachable_locations,
        recent_events=recent_perceived,
    )
