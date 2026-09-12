"""Schemas for World Initialization Plan with provenance tagging"""
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from ..domain.continuity import ActorVisualProfile, LocationVisualProfile, ObjectVisualProfile
from ..narrative.completion import StoryOutline


class FactType(str, Enum):
    """Classification of facts to distinguish truth origin"""

    SOURCE_FACT = "source_fact"
    DERIVED_PREMISE = "derived_premise"
    SIMULATION_INVENTION = "simulation_invention"


class TaggedFact(BaseModel):
    """Fact or premise detail explicitly tagged with provenance"""

    statement: str
    fact_type: FactType
    source_reference: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class CharacterPlan(BaseModel):
    """Blueprint for generating a Character in the simulation"""

    id: str
    name: str
    role: str
    description: str
    starting_location_id: str
    personality_traits: Dict[str, float] = Field(default_factory=dict)
    immediate_goals: List[str] = Field(default_factory=list)
    long_term_goals: List[str] = Field(default_factory=list)
    secrets: List[str] = Field(default_factory=list)
    initial_beliefs: List[str] = Field(default_factory=list)
    emotional_state: Dict[str, float] = Field(default_factory=dict)
    visual_profile: Optional[ActorVisualProfile] = None

    model_config = ConfigDict(frozen=True)


class LocationPlan(BaseModel):
    """Blueprint for a Location in the simulation"""

    id: str
    name: str
    description: str
    connected_location_ids: List[str] = Field(default_factory=list)
    capacity: Optional[int] = None
    visual_profile: Optional[LocationVisualProfile] = None

    model_config = ConfigDict(frozen=True)


class ObjectPlan(BaseModel):
    """Blueprint for a WorldObject in the simulation"""

    id: str
    name: str
    description: str
    starting_location_id: Optional[str] = None
    starting_holder_id: Optional[str] = None
    portable: bool = True
    properties: Dict[str, str] = Field(default_factory=dict)
    visual_profile: Optional[ObjectVisualProfile] = None

    model_config = ConfigDict(frozen=True)


class RelationshipPlan(BaseModel):
    """Blueprint for a Relationship between two characters"""

    id: str
    character_a_id: str
    character_b_id: str
    affinity: float = 0.0
    trust: float = 0.0
    history: str = ""

    model_config = ConfigDict(frozen=True)


class WorldInitializationPlan(BaseModel):
    """Complete structured initialization plan generated from unstructured seed text"""

    world_id: str
    world_name: str
    genre: str
    tone: str
    initial_situation: str
    facts: List[TaggedFact] = Field(default_factory=list)
    locations: List[LocationPlan] = Field(default_factory=list)
    characters: List[CharacterPlan] = Field(default_factory=list)
    objects: List[ObjectPlan] = Field(default_factory=list)
    relationships: List[RelationshipPlan] = Field(default_factory=list)
    possible_conflicts: List[str] = Field(default_factory=list)
    story_outline: Optional[StoryOutline] = None

    model_config = ConfigDict(frozen=True)
