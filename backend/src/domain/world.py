"""World state and location models"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from .character import Character
from .goal import Goal
from .belief import Belief
from .secret import Secret
from .relationship import Relationship
from .memory import Memory
from .event import Event
from .fact import DiscoveredFact
from .continuity import LocationVisualProfile, ObjectVisualProfile
from .proposition import Proposition, KnowledgeItem


class Location(BaseModel):
    """A location in the world"""

    id: str = Field(..., description="Unique location ID")
    name: str = Field(..., description="Name of the location")
    description: Optional[str] = Field(None, description="Description of the location")
    connected_locations: List[str] = Field(
        default_factory=list, description="IDs of adjacent locations"
    )
    capacity: Optional[int] = Field(
        None, description="Maximum number of characters allowed (None = unlimited)"
    )
    visual_profile: Optional[LocationVisualProfile] = Field(
        default=None, description="Visual environment profile for panel continuity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "loc_room307",
                "name": "Hotel Room 307",
                "description": "A modest hotel room on the third floor",
                "connected_locations": ["loc_hallway"],
                "capacity": 5,
            }
        }
    )


class WorldObject(BaseModel):
    """An object in the world"""

    id: str = Field(..., description="Unique object ID")
    name: str = Field(..., description="Name of the object")
    description: Optional[str] = Field(None, description="Description")
    location_id: Optional[str] = Field(
        None, description="Location where object currently is"
    )
    holder_id: Optional[str] = Field(
        None, description="Character ID if held by someone"
    )
    portable: bool = Field(default=True, description="Can this object be moved?")
    properties: Dict[str, str] = Field(
        default_factory=dict, description="Custom properties"
    )
    inspected_by: List[str] = Field(
        default_factory=list, description="IDs of characters who have inspected this object"
    )
    last_changed_tick: int = Field(
        default=0, description="Simulation tick of last modification or movement"
    )
    discovered_properties: Dict[str, Any] = Field(
        default_factory=dict, description="Revealed properties discovered by investigation"
    )
    visual_profile: Optional[ObjectVisualProfile] = Field(
        default=None, description="Visual identity profile for panel continuity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "obj_documents",
                "name": "Documents",
                "description": "Confidential project files",
                "location_id": "loc_room307",
                "holder_id": None,
                "portable": True,
                "properties": {"sensitive": "true"},
            }
        }
    )


class WorldState(BaseModel):
    """Complete canonical state of the world"""

    id: str = Field(..., description="World ID")
    name: str = Field(..., description="World name")
    description: Optional[str] = Field(None, description="World description")
    current_tick: int = Field(default=0, ge=0, description="Current simulation tick")
    locations: Dict[str, Location] = Field(
        default_factory=dict, description="All locations indexed by ID"
    )
    characters: Dict[str, Character] = Field(
        default_factory=dict, description="All characters indexed by ID"
    )
    objects: Dict[str, WorldObject] = Field(
        default_factory=dict, description="All objects indexed by ID"
    )
    goals: Dict[str, Goal] = Field(
        default_factory=dict, description="All goals indexed by ID"
    )
    beliefs: Dict[str, Belief] = Field(
        default_factory=dict, description="All beliefs indexed by ID"
    )
    secrets: Dict[str, Secret] = Field(
        default_factory=dict, description="All secrets indexed by ID"
    )
    relationships: Dict[str, Relationship] = Field(
        default_factory=dict, description="All relationships indexed by ID"
    )
    memories: Dict[str, Memory] = Field(
        default_factory=dict, description="All memories indexed by ID"
    )
    events: Dict[str, Event] = Field(
        default_factory=dict, description="All events indexed by ID"
    )
    facts: Dict[str, DiscoveredFact] = Field(
        default_factory=dict, description="All discovered facts indexed by ID"
    )
    propositions: Dict[str, Proposition] = Field(
        default_factory=dict, description="All canonical propositions indexed by ID"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "world_001",
                "name": "Hotel Intrigue",
                "description": "A story of secrets and deception in a luxury hotel",
                "current_tick": 0,
                "locations": {},
                "characters": {},
                "objects": {},
                "goals": {},
                "beliefs": {},
                "secrets": {},
                "relationships": {},
                "memories": {},
                "events": {},
            }
        }
    )

    def get_character_goals(self, character_id: str) -> List[Goal]:
        """Resolve all goals for a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.goals[gid] for gid in char.goals if gid in self.goals]

    def get_character_beliefs(self, character_id: str) -> List[Belief]:
        """Resolve all beliefs for a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.beliefs[bid] for bid in char.beliefs if bid in self.beliefs]

    def get_character_secrets(self, character_id: str) -> List[Secret]:
        """Resolve all secrets known by a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.secrets[sid] for sid in char.secrets if sid in self.secrets]

    def get_character_memories(self, character_id: str) -> List[Memory]:
        """Resolve all memories for a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.memories[mid] for mid in char.memories if mid in self.memories]

    def get_character_relationships(self, character_id: str) -> List[Relationship]:
        """Resolve all relationships involving a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.relationships[rid] for rid in char.relationships if rid in self.relationships]

    def get_relationship(self, char_a_id: str, char_b_id: str) -> Optional[Relationship]:
        """Find relationship between two characters regardless of direction"""
        for rel in self.relationships.values():
            if (rel.character_a_id == char_a_id and rel.character_b_id == char_b_id) or (
                rel.character_a_id == char_b_id and rel.character_b_id == char_a_id
            ):
                return rel
        return None

    def get_character_facts(self, character_id: str) -> List[DiscoveredFact]:
        """Resolve all discovered facts known to a character"""
        char = self.characters.get(character_id)
        if not char:
            return []
        return [self.facts[fid] for fid in getattr(char, "known_facts", []) if fid in self.facts]

    def register_proposition(self, proposition: Proposition) -> Proposition:
        """Register a canonical proposition into the world state."""
        self.propositions[proposition.id] = proposition
        return proposition

    def get_character_knowledge(self, character_id: str) -> List[KnowledgeItem]:
        """Resolve all private knowledge items held by a character."""
        char = self.characters.get(character_id)
        if not char:
            return []
        return list(char.knowledge.values())

    def validate_references(self) -> List[str]:
        """Check for dangling references across the canonical state.
        Returns a list of error descriptions (empty list if valid).
        """
        errors = []
        for char_id, char in self.characters.items():
            if char.current_location_id and char.current_location_id not in self.locations:
                errors.append(
                    f"Character '{char_id}' references missing location '{char.current_location_id}'"
                )
            for gid in char.goals:
                if gid not in self.goals:
                    errors.append(f"Character '{char_id}' references missing goal '{gid}'")
            for bid in char.beliefs:
                if bid not in self.beliefs:
                    errors.append(f"Character '{char_id}' references missing belief '{bid}'")
            for sid in char.secrets:
                if sid not in self.secrets:
                    errors.append(f"Character '{char_id}' references missing secret '{sid}'")
            for mid in char.memories:
                if mid not in self.memories:
                    errors.append(f"Character '{char_id}' references missing memory '{mid}'")
            for rid in char.relationships:
                if rid not in self.relationships:
                    errors.append(f"Character '{char_id}' references missing relationship '{rid}'")
            for fid in getattr(char, "known_facts", []):
                if fid not in self.facts:
                    errors.append(f"Character '{char_id}' references missing fact '{fid}'")
            for oid in char.inventory:
                if oid not in self.objects:
                    errors.append(f"Character '{char_id}' references missing object '{oid}'")

        for obj_id, obj in self.objects.items():
            if obj.location_id and obj.location_id not in self.locations:
                errors.append(f"Object '{obj_id}' references missing location '{obj.location_id}'")
            if obj.holder_id and obj.holder_id not in self.characters:
                errors.append(f"Object '{obj_id}' references missing holder '{obj.holder_id}'")

        for loc_id, loc in self.locations.items():
            for conn_id in loc.connected_locations:
                if conn_id not in self.locations:
                    errors.append(f"Location '{loc_id}' connects to missing location '{conn_id}'")

        for rel_id, rel in self.relationships.items():
            if rel.character_a_id not in self.characters:
                errors.append(f"Relationship '{rel_id}' references missing character_a '{rel.character_a_id}'")
            if rel.character_b_id not in self.characters:
                errors.append(f"Relationship '{rel_id}' references missing character_b '{rel.character_b_id}'")

        return errors
