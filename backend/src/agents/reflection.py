"""Reflection system for characters to synthesize episodic memories into higher-level beliefs (Milestone 11)"""
import uuid
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

from ..domain import WorldState, Memory, Belief
from ..memory.service import MemoryService
from ..evolution.belief import BeliefUpdater
from ..evolution.emotion import EmotionUpdater
from ..providers import LLMProvider, MockLLMProvider


class ReflectionResult(BaseModel):
    """Higher level cognitive insight distilled from episodic memories"""

    insight: str = Field(..., description="High-level understanding or synthesis")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    subject: Optional[str] = Field(None, description="Other character or entity this insight concerns")
    emotional_shift: Dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ReflectionSystem:
    """Bounded, periodic cognitive synthesis for characters"""

    def __init__(self, cadence_ticks: int = 5, provider: Optional[LLMProvider] = None):
        self.cadence_ticks = cadence_ticks
        self.provider = provider or MockLLMProvider()

    def should_reflect(self, current_tick: int, unreflected_memory_count: int) -> bool:
        """Check if reflection conditions are satisfied (cadence reached and memories available)"""
        if unreflected_memory_count < 2:
            return False
        return (current_tick > 0) and (current_tick % self.cadence_ticks == 0)

    def reflect_for_character(
        self,
        world: WorldState,
        character_id: str,
        memory_service: MemoryService,
    ) -> Optional[ReflectionResult]:
        """Synthesize recent memories into a belief without altering objective history"""
        char = world.characters.get(character_id)
        if not char:
            return None

        recent_memories = memory_service.get_working_memory(character_id, limit=5)
        if len(recent_memories) < 2:
            return None

        memory_summaries = [f"- {m.summary}" for m in recent_memories]
        prompt = (
            f"You are the internal subconscious reflection of character '{char.name}' ({char.role}).\n"
            f"Given these recent memories:\n"
            + "\n".join(memory_summaries)
            + "\n\nSynthesize a single overarching strategic insight or belief about your situation or companions."
        )
        system_prompt = "Synthesize episodic memories into an overarching character belief."

        # Generate reflection
        if isinstance(self.provider, MockLLMProvider) and ReflectionResult not in self.provider._structured_handlers:
            result = self._build_deterministic_mock_reflection(char, recent_memories)
        else:
            result = self.provider.generate_structured(ReflectionResult, prompt, system_prompt=system_prompt)

        # 1. Register newly synthesized belief in WorldState
        BeliefUpdater.form_or_reinforce_belief(
            world,
            character_id=character_id,
            statement=result.insight,
            initial_confidence=result.confidence,
            source="reflection",
        )

        # 2. Register reflection memory
        memory_service.form_memory(
            character_id=character_id,
            summary=f"Reflected upon recent events: {result.insight}",
            importance=0.8,
            emotional_weight=result.emotional_shift.get("fear", 0.0) - result.emotional_shift.get("trust", 0.0),
            tags=["reflection"],
        )

        # 3. Apply emotional shifts if specified
        if result.emotional_shift:
            EmotionUpdater.adjust_emotion(
                char,
                delta_fear=result.emotional_shift.get("fear", 0.0),
                delta_anger=result.emotional_shift.get("anger", 0.0),
                delta_trust=result.emotional_shift.get("trust", 0.0),
                delta_curiosity=result.emotional_shift.get("curiosity", 0.0),
            )

        return result

    def _build_deterministic_mock_reflection(self, char, recent_mems: List[Memory]) -> ReflectionResult:
        """Deterministic mock reflection based on character identity"""
        combined = " ".join([m.summary.lower() for m in recent_mems])
        if char.id == "char_arjun":
            if "maya" in combined:
                return ReflectionResult(
                    insight="Maya is deliberately withholding information about corporate misconduct.",
                    confidence=0.85,
                    subject="char_maya",
                    emotional_shift={"trust": -0.2, "curiosity": 0.3},
                )
            return ReflectionResult(
                insight="The environment has unresolved security risks.",
                confidence=0.75,
                emotional_shift={"fear": 0.1},
            )
        elif char.id == "char_maya":
            if "arjun" in combined:
                return ReflectionResult(
                    insight="Arjun's investigation threatens my legal immunity; maximum discretion required.",
                    confidence=0.9,
                    subject="char_arjun",
                    emotional_shift={"fear": 0.2, "trust": -0.3},
                )
            return ReflectionResult(
                insight="I must secure all physical records before departing.",
                confidence=0.8,
                emotional_shift={"curiosity": 0.1},
            )

        return ReflectionResult(
            insight="I need to remain alert and proceed cautiously.",
            confidence=0.7,
        )
