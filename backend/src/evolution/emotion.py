"""Emotion updater for character emotional states"""
from ..domain import Character, EmotionalState


class EmotionUpdater:
    """Deterministically evolves a character's emotional state within [-1.0, 1.0] bounds"""

    @staticmethod
    def adjust_emotion(
        character: Character,
        delta_happiness: float = 0.0,
        delta_fear: float = 0.0,
        delta_anger: float = 0.0,
        delta_trust: float = 0.0,
        delta_curiosity: float = 0.0,
    ) -> EmotionalState:
        """Apply bounded deltas to the character's emotional attributes"""
        curr = character.emotional_state

        new_happiness = round(max(-1.0, min(1.0, curr.happiness + delta_happiness)), 2)
        new_fear = round(max(-1.0, min(1.0, curr.fear + delta_fear)), 2)
        new_anger = round(max(-1.0, min(1.0, curr.anger + delta_anger)), 2)
        new_trust = round(max(-1.0, min(1.0, curr.trust + delta_trust)), 2)
        new_curiosity = round(max(-1.0, min(1.0, curr.curiosity + delta_curiosity)), 2)

        new_state = EmotionalState(
            happiness=new_happiness,
            fear=new_fear,
            anger=new_anger,
            trust=new_trust,
            curiosity=new_curiosity,
        )
        character.emotional_state = new_state
        return new_state
