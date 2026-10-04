"""Continuity Projector for deriving temporary, story-caused visual state from canonical events.

Phase G4 & G6:
- Pure read-only projection: derives CharacterContinuityState from canonical WorldState and EventLog.
- Tracks temporary visual states: wetness, injuries, dirt/blood, clothing damage, temporary disguise,
  carried objects, missing signature objects, environmental effects.
- Strict provenance discipline: every derived state carries real source event IDs and explainable reasons.
- Invariant: NEVER mutates WorldState, EventLog, or CharacterReferenceProfile.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, ConfigDict, Field

from src.domain.world import WorldState
from src.domain.event import Event


class CharacterContinuityState(BaseModel):
    """Temporary, story-caused visual state for a character at a specific shot/scene/tick.

    Derived strictly as a read-only projection from canonical events and world state.
    Carries source event IDs and reasons; never mutates canonical state or reference profiles.
    """
    model_config = ConfigDict(extra="ignore")

    character_id: str
    scene_id: str = ""
    tick: int = 0
    wetness: Optional[str] = None                             # e.g. "soaking wet coat", "damp hair"
    injuries: List[str] = Field(default_factory=list)         # e.g. ["split lip", "bruised right temple"]
    dirt_or_blood: Optional[str] = None                       # e.g. "grease smudges across cheek"
    clothing_damage: Optional[str] = None                     # e.g. "torn left sleeve"
    temporary_disguise: Optional[str] = None                  # e.g. "wearing custodian coveralls"
    carried_objects: List[str] = Field(default_factory=list)  # e.g. ["obj_dossier"]
    missing_signature_objects: List[str] = Field(default_factory=list)
    environmental_effects: List[str] = Field(default_factory=list) # e.g. ["rain-streaked", "dust-covered"]
    source_event_ids: List[str] = Field(default_factory=list) # Real provenance event IDs
    reasons: List[str] = Field(default_factory=list)

    def summary_description(self) -> str:
        """Observable demeanor and temporary visual state for prompt generation."""
        parts = []
        if self.temporary_disguise:
            parts.append(f"disguised in {self.temporary_disguise}")
        if self.clothing_damage:
            parts.append(self.clothing_damage)
        if self.wetness:
            parts.append(self.wetness)
        if self.dirt_or_blood:
            parts.append(self.dirt_or_blood)
        if self.injuries:
            parts.append(f"visible injuries: {', '.join(self.injuries)}")
        if self.carried_objects:
            parts.append(f"holding {', '.join(self.carried_objects)}")
        if self.environmental_effects:
            parts.append(", ".join(self.environmental_effects))
        return "; ".join(parts) if parts else "normal baseline appearance"


class ContinuityProjector:
    """Derives temporary character visual continuity states deterministically from canonical history."""

    @classmethod
    def project_character_continuity(
        cls,
        character_id: str,
        events: List[Event],
        world: Optional[WorldState] = None,
        up_to_tick: Optional[int] = None,
        tick: Optional[int] = None,
        scene_id: str = "",
    ) -> CharacterContinuityState:
        """Derive temporary visual state for a single character from canonical events up to up_to_tick."""
        effective_limit = tick if tick is not None else up_to_tick
        # 1. Filter events up to tick
        relevant_events = [
            e for e in events
            if effective_limit is None or e.tick <= effective_limit
        ]
        # Sort chronologically by tick and id
        relevant_events.sort(key=lambda e: (e.tick, e.id))

        carried: Set[str] = set()
        injuries: List[str] = []
        dirt_or_blood: Optional[str] = None
        clothing_damage: Optional[str] = None
        wetness: Optional[str] = None
        temporary_disguise: Optional[str] = None
        missing_signature: Set[str] = set()
        env_effects: Set[str] = set()
        source_events: List[str] = []
        reasons: List[str] = []

        # Current tick reference
        effective_tick = effective_limit if effective_limit is not None else (
            relevant_events[-1].tick if relevant_events else 0
        )

        # Baseline inventory from world if present
        if world and character_id in world.characters:
            char = world.characters[character_id]
            for obj_id in char.inventory:
                carried.add(obj_id)

        # Replay event stream to accumulate temporary physical state
        for ev in relevant_events:
            desc_lower = ev.description.lower()
            ev_type_val = getattr(ev, "event_type", getattr(ev, "type", ""))
            ev_type_str = ev_type_val.value.lower() if hasattr(ev_type_val, "value") else str(ev_type_val).lower()
            actor_ids = ev.actor_ids if hasattr(ev, "actor_ids") else ([getattr(ev, "actor_id")] if hasattr(ev, "actor_id") else [])
            is_actor = character_id in actor_ids
            target_ids = []
            if hasattr(ev, "target_ids") and ev.target_ids:
                target_ids.extend(ev.target_ids)
            if hasattr(ev, "target_id") and ev.target_id:
                target_ids.append(ev.target_id)
            if hasattr(ev, "metadata") and isinstance(ev.metadata, dict):
                if "target_id" in ev.metadata:
                    target_ids.append(ev.metadata["target_id"])
                if "object_id" in ev.metadata:
                    target_ids.append(ev.metadata["object_id"])
            is_target = character_id in target_ids or (not is_actor and character_id in actor_ids)

            # A. Carried objects
            if is_actor:
                if any(k in desc_lower for k in ("picked up", "took", "retrieved", "grabbed", "acquired", "seized", "seizes", "seize")) or "picked_up" in ev_type_str or "pick_up" in ev_type_str:
                    # Identify target object
                    for tid in target_ids:
                        carried.add(tid)
                        if ev.id not in source_events:
                            source_events.append(ev.id)
                        reasons.append(f"Retrieved {tid} at tick {ev.tick}")

                elif any(k in desc_lower for k in ("dropped", "lost", "transferred", "handed over", "stashed")) or "drop" in ev_type_str:
                    for tid in target_ids:
                        carried.discard(tid)
                        if ev.id not in source_events:
                            source_events.append(ev.id)
                        reasons.append(f"Relinquished {tid} at tick {ev.tick}")

            # B. Physical combat, struggle, and injuries
            if is_target or (is_actor and any(k in desc_lower for k in ("struggle", "grapple", "brawl", "clash"))):
                if any(k in desc_lower for k in ("hit", "struck", "strike", "attack", "shot", "wounded", "bruised", "fell", "thrown", "cut", "laceration", "glass", "shoved", "injured", "bleed", "bleeding")):
                    if "split lip" not in injuries:
                        injuries.append("split lip and bruised right cheek")
                    clothing_damage = "creased and torn coat sleeve"
                    dirt_or_blood = "trace blood and dust across jawline"
                    if ev.id not in source_events:
                        source_events.append(ev.id)
                    reasons.append(f"Sustained physical trauma in event {ev.id} at tick {ev.tick}")

                elif any(k in desc_lower for k in ("forced entry", "breached", "scrambled", "crawled", "vent")):
                    clothing_damage = "dust-streaked outerwear"
                    dirt_or_blood = "grease and soot marks across knuckles"
                    if ev.id not in source_events:
                        source_events.append(ev.id)
                    reasons.append(f"Physical exertion in event {ev.id} at tick {ev.tick}")

            # C. Environmental effects & Wetness
            loc = world.locations.get(ev.location_id) if (world and ev.location_id) else None
            loc_desc = (loc.description.lower() if loc and loc.description else "") + (loc.name.lower() if loc else "")

            if any(k in desc_lower or k in loc_desc for k in ("rain", "storm", "wet", "drench", "sprinkler", "water", "dock", "sewer")):
                wetness = "rain-dampened coat and darkened fabric"
                env_effects.add("rain-streaked silhouette")
                if ev.id not in source_events:
                    source_events.append(ev.id)
                reasons.append(f"Exposed to rain/water at {ev.location_id or 'environment'} at tick {ev.tick}")

            # D. Temporary disguise
            if is_actor:
                if any(k in desc_lower for k in ("disguise", "coveralls", "jumpsuit", "uniform", "lab coat", "donned")):
                    m_disguise = re.search(r"\b(?:wearing|in|donned|as a)\s+([a-z\s]+(?:coveralls|jumpsuit|uniform|lab coat|disguise))\b", desc_lower)
                    temporary_disguise = m_disguise.group(1).strip() if m_disguise else "utilitarian service uniform"
                    if ev.id not in source_events:
                        source_events.append(ev.id)
                    reasons.append(f"Adopted disguise in event {ev.id} at tick {ev.tick}")

        return CharacterContinuityState(
            character_id=character_id,
            scene_id=scene_id,
            tick=effective_tick,
            wetness=wetness,
            injuries=injuries,
            dirt_or_blood=dirt_or_blood,
            clothing_damage=clothing_damage,
            temporary_disguise=temporary_disguise,
            carried_objects=sorted(list(carried)),
            missing_signature_objects=sorted(list(missing_signature)),
            environmental_effects=sorted(list(env_effects)),
            source_event_ids=source_events,
            reasons=reasons,
        )

    @classmethod
    def project_scene_continuity(
        cls,
        character_ids: Optional[Any] = None,
        events: Optional[List[Event]] = None,
        world: Optional[WorldState] = None,
        up_to_tick: Optional[int] = None,
        tick: Optional[int] = None,
        scene_id: str = "",
    ) -> Dict[str, CharacterContinuityState]:
        """Project temporary visual continuity for all characters in a scene."""
        # Handle polymorphic argument ordering: project_scene_continuity(world, events, ...)
        if isinstance(character_ids, WorldState):
            world = character_ids
            character_ids = None

        if world and character_ids is None:
            character_ids = list(world.characters.keys())
        elif character_ids is None:
            character_ids = []

        effective_limit = tick if tick is not None else up_to_tick
        actual_events = events if events is not None else []

        result: Dict[str, CharacterContinuityState] = {}
        for cid in character_ids:
            result[cid] = cls.project_character_continuity(
                character_id=cid,
                events=actual_events,
                world=world,
                up_to_tick=effective_limit,
                scene_id=scene_id,
            )
        return result
