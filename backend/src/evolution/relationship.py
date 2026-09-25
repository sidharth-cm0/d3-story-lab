"""Relationship updater for trust, affinity, and interaction history"""
import uuid
import hashlib
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
        slug = hashlib.sha256(f"{char_a_id}:{char_b_id}:{len(world.relationships)}".encode()).hexdigest()[:6]
        new_id = f"rel_{char_a_id}_{char_b_id}_{slug}"
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
        delta_affection: float = 0.0,
        delta_fear: float = 0.0,
        delta_dependency: float = 0.0,
        delta_respect: float = 0.0,
        delta_resentment: float = 0.0,
        delta_suspicion: float = 0.0,
        delta_power_imbalance: float = 0.0,
        note: str = "",
        event_id: Optional[str] = None,
    ) -> Relationship:
        """Apply deltas to relationship dimensions with bounding [-1.0, 1.0] and event provenance."""
        rel = cls.get_or_create_relationship(world, char_a_id, char_b_id)

        deltas = {
            "affinity": delta_affinity,
            "trust": delta_trust,
            "affection": delta_affection,
            "fear": delta_fear,
            "dependency": delta_dependency,
            "respect": delta_respect,
            "resentment": delta_resentment,
            "suspicion": delta_suspicion,
            "power_imbalance": delta_power_imbalance,
        }

        updated_values = {}
        prov = dict(rel.event_provenance) if rel.event_provenance else {}

        for dim, delta in deltas.items():
            curr = getattr(rel, dim, 0.0)
            if delta != 0.0:
                new_val = round(max(-1.0, min(1.0, curr + delta)), 2)
                updated_values[dim] = new_val
                if event_id:
                    existing_evs = list(prov.get(dim, []))
                    if event_id not in existing_evs:
                        existing_evs.append(event_id)
                    prov[dim] = existing_evs
            else:
                updated_values[dim] = curr

        new_history = rel.history
        if note:
            new_history = f"{rel.history}; {note}".strip("; ")

        updated_values["history"] = new_history
        updated_values["event_provenance"] = prov
        if event_id:
            updated_values["last_event_id"] = event_id

        updated_rel = rel.model_copy(update=updated_values)
        world.relationships[updated_rel.id] = updated_rel
        return updated_rel
