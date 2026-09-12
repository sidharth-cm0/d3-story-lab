"""Deterministic Canonical Prop Resolver for Storyboard Planning and Continuity.

Resolves mentioned objects from event actions, screenplay actions, dialogue context,
narrative beats, and shot purposes to canonical WorldObject IDs using WorldState
as the single source of truth.
"""

from __future__ import annotations
import re
from typing import List, Dict, Set, Optional, Tuple
from ..domain.world import WorldState, WorldObject


# Deterministic alias mapping for common narrative props
COMMON_PROP_ALIASES: Dict[str, List[str]] = {
    "dossier": [
        "dossier",
        "sealed dossier",
        "evidence dossier",
        "confidential dossier",
        "file",
        "documents",
        "case file",
        "classified folder",
        "folder",
        "paperwork",
        "manila envelope",
        "portfolio",
    ],
    "transceiver": [
        "transceiver",
        "encrypted transceiver",
        "radio",
        "walkie",
        "transmitter",
        "comms",
        "receiver",
        "handheld transceiver",
        "military transceiver",
    ],
    "ledger": [
        "ledger",
        "black ledger",
        "account book",
        "notebook",
        "journal",
        "logbook",
        "financial ledger",
        "bribe ledger",
    ],
    "keycard": [
        "keycard",
        "hotel keycard",
        "card",
        "access card",
        "magnetic card",
        "passkey",
        "electronic key",
    ],
    "key": [
        "brass key",
        "locker key",
        "room key",
        "skeleton key",
        "vault key",
        "small key",
    ],
    "safe": [
        "safe",
        "steel safe",
        "wall safe",
        "locker",
        "evidence locker",
        "vault",
        "security box",
        "lockbox",
        "deposit box",
    ],
    "phone": [
        "phone",
        "cell phone",
        "burner phone",
        "telephone",
        "mobile",
        "smartphone",
        "receiver",
    ],
    "drive": [
        "cipher drive",
        "thumb drive",
        "usb drive",
        "flash drive",
        "hard drive",
        "data disc",
        "decrypted cipher drive",
        "usb",
    ],
    "gun": [
        "revolver",
        "service weapon",
        "pistol",
        "firearm",
        "service revolver",
        "handgun",
    ],
    "suitcase": [
        "suitcase",
        "locked suitcase",
        "briefcase",
        "sealed package",
        "package",
        "valise",
        "courier bag",
    ],
}


def _build_object_patterns(obj: WorldObject) -> List[Tuple[re.Pattern, int]]:
    """Build compiled regex patterns for a WorldObject including aliases and specific names.
    Returns list of (compiled_pattern, priority_weight).
    """
    patterns: List[Tuple[re.Pattern, int]] = []
    normalized_name = obj.name.strip().lower()
    normalized_id = obj.id.strip().lower()
    normalized_desc = (obj.description or "").lower()

    # Exact name match (highest priority)
    exact_escaped = re.escape(normalized_name)
    patterns.append((re.compile(rf"\b{exact_escaped}\b", re.IGNORECASE), 100))

    # Cleaned name tokens (length >= 4)
    tokens = [t for t in re.split(r"\W+", normalized_name) if len(t) >= 4]
    for token in tokens:
        patterns.append((re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE), 70))

    # Match against COMMON_PROP_ALIASES
    for prop_key, alias_list in COMMON_PROP_ALIASES.items():
        # If this WorldObject matches the prop key in its name, ID, or description
        if (
            prop_key in normalized_name
            or prop_key in normalized_id
            or prop_key in normalized_desc
        ):
            for alias in alias_list:
                alias_clean = alias.strip().lower()
                # Longer phrases get higher priority
                weight = 80 if " " in alias_clean else 60
                patterns.append((re.compile(rf"\b{re.escape(alias_clean)}\b", re.IGNORECASE), weight))

    return patterns


class PropResolver:
    """Resolves canonical WorldObjects mentioned in narrative texts."""

    @classmethod
    def resolve_mentioned_objects(
        cls,
        text_pool: str,
        world: Optional[WorldState],
        location_id: Optional[str] = None,
        characters_present: Optional[List[str]] = None,
        direct_object_ids: Optional[List[str]] = None,
    ) -> List[WorldObject]:
        """Resolve all canonical WorldObjects mentioned in text_pool with context weighting."""
        if not world or not world.objects:
            return []

        resolved: Dict[str, Tuple[WorldObject, int]] = {}
        text_clean = text_pool.lower()

        # 1. Directly referenced object IDs (from event fields)
        if direct_object_ids:
            for oid in direct_object_ids:
                if oid in world.objects:
                    resolved[oid] = (world.objects[oid], 150)

        # 2. Check each canonical object in the registry
        for obj_id, obj in world.objects.items():
            patterns = _build_object_patterns(obj)
            best_weight = 0

            for pattern, weight in patterns:
                if pattern.search(text_clean):
                    if weight > best_weight:
                        best_weight = weight

            if best_weight > 0:
                # Context validation & weighting
                context_bonus = 0
                # If object is at the scene location
                if location_id and obj.location_id == location_id:
                    context_bonus += 20
                # If object is held by someone present in the scene
                if characters_present and obj.holder_id and obj.holder_id in characters_present:
                    context_bonus += 25
                # If object is held by anyone
                elif obj.holder_id:
                    context_bonus += 10
                # If it's the only object of this kind in the world
                matching_in_world = sum(
                    1 for o in world.objects.values()
                    if o.name.lower() == obj.name.lower()
                )
                if matching_in_world == 1:
                    context_bonus += 15

                total_weight = best_weight + context_bonus
                if obj_id not in resolved or total_weight > resolved[obj_id][1]:
                    resolved[obj_id] = (obj, total_weight)

        # Sort by weight descending
        sorted_objects = sorted(resolved.values(), key=lambda item: item[1], reverse=True)
        return [item[0] for item in sorted_objects]

    @classmethod
    def resolve_canonical_object_ids(
        cls,
        text_pool: str,
        world: Optional[WorldState],
        location_id: Optional[str] = None,
        characters_present: Optional[List[str]] = None,
        direct_object_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Convenience method returning list of canonical object_ids."""
        objs = cls.resolve_mentioned_objects(
            text_pool=text_pool,
            world=world,
            location_id=location_id,
            characters_present=characters_present,
            direct_object_ids=direct_object_ids,
        )
        return [o.id for o in objs]
