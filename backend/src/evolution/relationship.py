"""Relationship updater for trust, affinity, and interaction history"""
import uuid
from typing import Optional
from ..domain import WorldState, Relationship


class RelationshipUpdater:
    """Updates relationships between characters deterministically bounded within [-1.0, 1.0]"""

    @staticmethod
    def get_or_create_relationship(
        world: WorldState,
        char_a_id: str,
        char_b_id: str,
    ) -> Relationship:
        """Find an existing relationship between two characters or initialize a neutral one"""
        # Look for existing relationship in world
        for rel in world.relationships.values():
            if (rel.character_a_id == char_a_id and rel.character_b_id == char_b_id) or (
                rel.character_a_id == char_b_id and rel.character_b_id == char_a_id
            ):
                return rel

        # Create new neutral relationship
        new_id = f"rel_{char_a_id}_{char_b_id}_{uuid.uuid4().hex[:6]}"
        new_rel = Relationship(
            id=new_id,
            character_a_id=char_a_id,
            character_b_id=char_b_id,
            affinity=0.0,
            trust=0.0,
            history="Initial encounter",
        )
        world.relationships[new_rel.id] = new_rel

        # Attach to characters
        char_a = world.characters.get(char_a_id)
        if char_a and new_rel.id not in char_a.relationships:
            char_a.relationships.append(new_rel.id)

        char_b = world.characters.get(char_b_id)
        if char_b and new_rel.id not in char_b.relationships:
            char_b.relationships.append(new_rel.id)

        return new_rel

    @classmethod
    def apply_interaction(
        cls,
        world: WorldState,
        char_a_id: str,
        char_b_id: str,
        delta_affinity: float = 0.0,
        delta_trust: float = 0.0,
        note: str = "",
    ) -> Relationship:
        """Apply deltas to affinity and trust with bounding [-1.0, 1.0]"""
        rel = cls.get_or_create_relationship(world, char_a_id, char_b_id)

        new_affinity = round(max(-1.0, min(1.0, rel.affinity + delta_affinity)), 2)
        new_trust = round(max(-1.0, min(1.0, rel.trust + delta_trust)), 2)

        new_history = rel.history
        if note:
            new_history = f"{rel.history}; {note}".strip("; ")

        updated_rel = rel.model_copy(
            update={
                "affinity": new_affinity,
                "trust": new_trust,
                "history": new_history,
            }
        )
        world.relationships[updated_rel.id] = updated_rel
        return updated_rel
