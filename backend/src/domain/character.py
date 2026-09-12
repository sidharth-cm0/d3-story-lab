"""Character model"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .continuity import ActorVisualProfile


class EmotionalState(BaseModel):
    """A character's emotional state"""

    happiness: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Happiness level: -1.0 to 1.0",
    )
    fear: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Fear level: -1.0 to 1.0"
    )
    anger: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Anger level: -1.0 to 1.0"
    )
    trust: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="General trust level: -1.0 to 1.0"
    )
    curiosity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Curiosity level: -1.0 to 1.0",
    )

    @field_validator("happiness", "fear", "anger", "trust", "curiosity")
    @classmethod
    def validate_emotion(cls, v):
        if not (-1.0 <= v <= 1.0):
            raise ValueError("Emotion value must be between -1.0 and 1.0")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "happiness": 0.2,
                "fear": 0.6,
                "anger": 0.3,
                "trust": 0.4,
                "curiosity": 0.8,
            }
        }
    )


class Character(BaseModel):
    """A character in the world"""

    id: str = Field(..., description="Unique character ID")
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Character role/profession")
    description: Optional[str] = Field(None, description="Character description")
    personality_traits: Dict[str, float] = Field(
        default_factory=dict,
        description="Personality traits with values 0-1 (e.g., ambitious, loyal, cautious)",
    )
    emotional_state: EmotionalState = Field(
        default_factory=EmotionalState, description="Current emotional state"
    )
    goals: List[str] = Field(default_factory=list, description="Goal IDs")
    beliefs: List[str] = Field(default_factory=list, description="Belief IDs")
    secrets: List[str] = Field(default_factory=list, description="Secret IDs")
    memories: List[str] = Field(default_factory=list, description="Memory IDs")
    relationships: List[str] = Field(default_factory=list, description="Relationship IDs")
    known_facts: List[str] = Field(default_factory=list, description="Known fact IDs")
    current_location_id: Optional[str] = Field(
        None, description="Current location ID"
    )
    inventory: List[str] = Field(default_factory=list, description="Object IDs held")
    visual_profile: Optional[ActorVisualProfile] = Field(
        default=None, description="Visual identity profile for continuity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "char_arjun",
                "name": "Arjun",
                "role": "Corporate Investigator",
                "description": "A determined investigator searching for truth",
                "personality_traits": {
                    "ambitious": 0.8,
                    "loyal": 0.7,
                    "cautious": 0.6,
                },
                "emotional_state": {
                    "happiness": 0.2,
                    "fear": 0.6,
                    "anger": 0.3,
                    "trust": 0.4,
                    "curiosity": 0.8,
                },
                "goals": ["goal_001"],
                "beliefs": ["bel_001"],
                "secrets": [],
                "memories": [],
                "relationships": ["rel_001"],
                "current_location_id": "loc_room307",
                "inventory": [],
            }
        }
    )
