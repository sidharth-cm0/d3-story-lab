"""Character model"""
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .continuity import ActorVisualProfile
from .proposition import KnowledgeItem


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
    knowledge: Dict[str, KnowledgeItem] = Field(
        default_factory=dict, description="Private subjective knowledge held by the character"
    )
    current_location_id: Optional[str] = Field(
        None, description="Current location ID"
    )
    inventory: List[str] = Field(default_factory=list, description="Object IDs held")
    visual_profile: Optional[ActorVisualProfile] = Field(
        default=None, description="Visual identity profile for continuity"
    )

    def knows(self, proposition_id: str) -> Optional[KnowledgeItem]:
        """Retrieve private subjective knowledge of a proposition. Returns None if character does not know it."""
        return self.knowledge.get(proposition_id)

    def acquire_knowledge(
        self,
        proposition_id: str,
        certainty: float = 1.0,
        acquired_at_event: str = "",
        source: Literal["observed", "inferred", "told"] = "observed",
        source_character_id: Optional[str] = None,
        believed_truth_value: bool = True,
    ) -> KnowledgeItem:
        """Acquire or update a subjective KnowledgeItem for this character."""
        existing = self.knowledge.get(proposition_id)
        item = KnowledgeItem(
            proposition_id=proposition_id,
            holder_id=self.id,
            certainty=certainty,
            acquired_at_event=acquired_at_event,
            source=source,
            source_character_id=source_character_id,
            believed_truth_value=believed_truth_value,
            shared_with=existing.shared_with if existing else [],
        )
        self.knowledge[proposition_id] = item
        return item

    def share_knowledge(
        self,
        proposition_id: str,
        recipient: "Character",
        acquired_at_event: str = "",
        believed_truth_value: Optional[bool] = None,
    ) -> Optional[KnowledgeItem]:
        """Share knowledge with another character, creating a new KnowledgeItem on recipient with source='told'."""
        my_knowledge = self.knows(proposition_id)
        if not my_knowledge:
            return None
        if recipient.id not in my_knowledge.shared_with:
            new_shared = list(my_knowledge.shared_with) + [recipient.id]
            self.knowledge[proposition_id] = my_knowledge.model_copy(update={"shared_with": new_shared})

        tv = believed_truth_value if believed_truth_value is not None else my_knowledge.believed_truth_value
        return recipient.acquire_knowledge(
            proposition_id=proposition_id,
            certainty=my_knowledge.certainty,
            acquired_at_event=acquired_at_event,
            source="told",
            source_character_id=self.id,
            believed_truth_value=tv,
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
