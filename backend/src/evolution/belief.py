"""Belief updater for belief formation, reinforcement, and contradiction handling"""
import uuid
from typing import Optional, List
from ..domain import WorldState, Belief


class BeliefUpdater:
    """Updates and maintains character beliefs with bounded confidence levels [0.0, 1.0]"""

    @staticmethod
    def form_or_reinforce_belief(
        world: WorldState,
        character_id: str,
        statement: str,
        confidence_delta: float = 0.2,
        initial_confidence: float = 0.6,
        source: Optional[str] = "observation",
    ) -> Belief:
        """Form a new belief or reinforce an existing similar belief held by the character"""
        char = world.characters.get(character_id)
        if not char:
            raise ValueError(f"Character '{character_id}' does not exist")

        # Check if character already has an identical or matching statement belief
        existing_beliefs = world.get_character_beliefs(character_id)
        for bel in existing_beliefs:
            if bel.statement.strip().lower() == statement.strip().lower():
                # Reinforce confidence
                new_conf = round(max(0.0, min(1.0, bel.confidence + confidence_delta)), 2)
                updated_bel = bel.model_copy(update={"confidence": new_conf, "source": source})
                world.beliefs[updated_bel.id] = updated_bel
                return updated_bel

        # Form new belief
        new_id = f"bel_{world.current_tick}_{character_id}_{uuid.uuid4().hex[:6]}"
        initial_conf = round(max(0.0, min(1.0, initial_confidence)), 2)
        new_bel = Belief(
            id=new_id,
            character_id=character_id,
            statement=statement,
            confidence=initial_conf,
            source=source,
        )
        world.beliefs[new_bel.id] = new_bel
        if new_bel.id not in char.beliefs:
            char.beliefs.append(new_bel.id)
        return new_bel

    @staticmethod
    def weaken_belief(
        world: WorldState,
        belief_id: str,
        penalty: float = 0.3,
    ) -> Optional[Belief]:
        """Weaken confidence in a belief when encountering contradictory evidence"""
        bel = world.beliefs.get(belief_id)
        if not bel:
            return None

        new_conf = round(max(0.0, min(1.0, bel.confidence - penalty)), 2)
        updated_bel = bel.model_copy(update={"confidence": new_conf})
        world.beliefs[updated_bel.id] = updated_bel
        return updated_bel
