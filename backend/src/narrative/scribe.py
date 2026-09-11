"""Scribe agent for converting simulation events into Fountain screenplays."""

from __future__ import annotations
from typing import List, Optional
import re

from src.domain.world import WorldState
from src.domain.event import Event, EventType
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat
from src.narrative.fountain import (
    ScreenplayDocument,
    ScreenplayScene,
    ScreenplayBlock,
    ScreenplayBlockType,
)
from src.providers.base import LLMProvider


class Scribe:
    """Converts verified narrative beats into standard Fountain screenplays."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    def _format_scene_heading(self, location_id: str, world: WorldState) -> str:
        loc = world.locations.get(location_id)
        loc_name = loc.name.upper() if loc else location_id.upper()
        # Clean slugline prefix
        if not loc_name.startswith("INT.") and not loc_name.startswith("EXT."):
            heading = f"INT. {loc_name} - CONTINUOUS"
        else:
            heading = f"{loc_name} - CONTINUOUS"
        return heading

    def _resolve_character_name(self, char_id: str, world: WorldState) -> str:
        char = world.characters.get(char_id)
        if char:
            return char.name.upper()
        # Fallback to readable format if ID is char_maya -> MAYA
        return char_id.replace("char_", "").replace("_", " ").upper()

    def _extract_dialogue_text(self, event: Event) -> tuple[str, Optional[str]]:
        """Extract spoken dialogue and optional parenthetical from event."""
        # 1. Check metadata
        if "dialogue" in event.metadata and event.metadata["dialogue"]:
            text = str(event.metadata["dialogue"])
            emotion = event.metadata.get("emotion", None)
            return text, emotion

        # 2. Check description: e.g. "Maya says: 'Where is the ledger?'"
        desc = event.description
        quotes = re.findall(r"['\"](.*?)['\"]", desc)
        if quotes:
            return quotes[0], None

        # Fallback if no quote marks
        if ":" in desc:
            return desc.split(":", 1)[1].strip(), None

        return desc, None

    def compose_screenplay(
        self,
        selection: NarrativeEventSelection,
        world: WorldState,
        title: str = "EMERGENT NARRATIVE",
    ) -> ScreenplayDocument:
        """Transform narrative beats into a verified ScreenplayDocument with repetition control."""
        # 1. Flatten ordered events from beats while maintaining provenance
        events: List[Event] = []
        seen_event_ids = set()
        for beat in selection.filtered_beats:
            for eid in beat.source_event_ids:
                if eid not in seen_event_ids and eid in world.events:
                    seen_event_ids.add(eid)
                    events.append(world.events[eid])

        # If no events from beats, fallback to all world events
        if not events and world.events:
            events = sorted(world.events.values(), key=lambda e: (e.tick, e.id))

        if not events:
            heading = "INT. VOID - DAY"
            return ScreenplayDocument(
                title=title,
                author="D3 Story Lab Simulation",
                scenes=[
                    ScreenplayScene(
                        scene_number=1,
                        location_id="none",
                        heading=heading,
                        blocks=[
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.ACTION,
                                text="Silence. The world awaits action.",
                                source_event_ids=[],
                            )
                        ],
                        source_event_ids=[],
                    )
                ],
            )

        scenes: List[ScreenplayScene] = []
        current_location_id: Optional[str] = None
        current_scene_blocks: List[ScreenplayBlock] = []
        current_scene_events: List[str] = []
        scene_counter = 0

        def finalize_scene():
            nonlocal scene_counter, current_scene_blocks, current_scene_events, current_location_id
            if current_scene_blocks:
                scene_counter += 1
                heading = self._format_scene_heading(current_location_id or "UNKNOWN", world)
                scenes.append(
                    ScreenplayScene(
                        scene_number=scene_counter,
                        location_id=current_location_id or "unknown",
                        heading=heading,
                        blocks=list(current_scene_blocks),
                        source_event_ids=list(dict.fromkeys(current_scene_events)),
                    )
                )
                current_scene_blocks = []
                current_scene_events = []

        # Tracking for dialogue deduplication
        recent_dialogues: List[dict] = []

        i = 0
        while i < len(events):
            event = events[i]
            event_loc = event.location_id or "unknown"

            # Check if this event represents a genuine scene transition
            # Avoid creating a new scene for a transient 1-event pass-through if the next event returns to the current location
            is_transient_pass_through = False
            if current_location_id is not None and event_loc != current_location_id:
                if i + 1 < len(events) and events[i + 1].location_id == current_location_id:
                    # Current event is in a different location, but next event returns immediately
                    # If current event has no dialogue, absorb it into the current scene action
                    if event.event_type != EventType.CHARACTER_SPOKE:
                        is_transient_pass_through = True

            target_scene_loc = current_location_id if is_transient_pass_through else event_loc

            if current_location_id is None:
                current_location_id = target_scene_loc
            elif target_scene_loc != current_location_id:
                finalize_scene()
                current_location_id = target_scene_loc

            # --- 1. Movement Merging ---
            if event.event_type == EventType.CHARACTER_MOVED:
                next_ev = events[i + 1] if i + 1 < len(events) else None
                # Check if next event is also a movement around the same time
                if next_ev and next_ev.event_type == EventType.CHARACTER_MOVED and abs(next_ev.tick - event.tick) <= 1:
                    actor1 = world.characters.get(event.actor_ids[0]) if event.actor_ids else None
                    actor2 = world.characters.get(next_ev.actor_ids[0]) if next_ev.actor_ids else None
                    name1 = actor1.name if actor1 else "Figure"
                    name2 = actor2.name if actor2 else "Figure"

                    dest1 = event.metadata.get("to_location_name") or (world.locations[event.location_id].name if event.location_id in world.locations else "the adjacent area")
                    dest2 = next_ev.metadata.get("to_location_name") or (world.locations[next_ev.location_id].name if next_ev.location_id in world.locations else "the adjacent area")

                    if actor1 and actor2 and actor1.id != actor2.id and (dest1 == dest2 or event.location_id == next_ev.location_id):
                        # Both characters moving to the same destination
                        merged_text = f"{name1} steps into {dest1}. {name2} follows."
                        current_scene_events.extend([event.id, next_ev.id])
                        current_scene_blocks.append(
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.ACTION,
                                text=merged_text,
                                source_event_ids=[event.id, next_ev.id],
                                character_id=actor1.id,
                            )
                        )
                        i += 2
                        continue
                    elif actor1 and actor2 and actor1.id == actor2.id and event.metadata.get("from_location") == next_ev.metadata.get("to_location"):
                        # Same character briefly steps out and immediately returns
                        orig_loc = event.metadata.get("from_location_name") or "the suite"
                        merged_text = f"{name1} glances into {dest1}, then returns to {orig_loc}."
                        current_scene_events.extend([event.id, next_ev.id])
                        current_scene_blocks.append(
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.ACTION,
                                text=merged_text,
                                source_event_ids=[event.id, next_ev.id],
                                character_id=actor1.id,
                            )
                        )
                        i += 2
                        continue

                # Single movement
                actor = world.characters.get(event.actor_ids[0]) if event.actor_ids else None
                name = actor.name if actor else "Figure"
                from_name = event.metadata.get("from_location_name")
                to_name = event.metadata.get("to_location_name") or (world.locations[event.location_id].name if event.location_id in world.locations else "another room")

                action_text = f"{name} enters {to_name}." if from_name is None else f"{name} moves from {from_name} into {to_name}."
                current_scene_events.append(event.id)
                current_scene_blocks.append(
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text=action_text,
                        source_event_ids=[event.id],
                        character_id=event.actor_ids[0] if event.actor_ids else None,
                    )
                )
                i += 1
                continue

            # --- 2. Dialogue Processing & Deduplication ---
            elif event.event_type == EventType.CHARACTER_SPOKE:
                speaker_id = event.actor_ids[0] if event.actor_ids else "SPEAKER"
                speaker_name = self._resolve_character_name(speaker_id, world)
                dialogue_text, emotion = self._extract_dialogue_text(event)
                speech_act = event.metadata.get("speech_act", "").lower()
                topic = event.metadata.get("topic", "").lower()

                # Normalize text for similarity check
                def clean_dialogue(text: str) -> str:
                    t = text.lower()
                    for c in world.characters.values():
                        t = t.replace(c.name.lower(), "")
                    return re.sub(r"[^a-z0-9\s]", "", t).strip()

                clean_curr = clean_dialogue(dialogue_text)
                words_curr = set(clean_curr.split())

                # Check if duplicate of recent dialogue (within last 3 speeches)
                is_duplicate = False
                for prev in recent_dialogues[-3:]:
                    prev_clean = prev["clean_text"]
                    if clean_curr == prev_clean and clean_curr != "":
                        is_duplicate = True
                        break
                    prev_words = prev["words"]
                    if words_curr and prev_words:
                        overlap = len(words_curr & prev_words) / max(len(words_curr), len(prev_words))
                        if overlap >= 0.65 and prev["speech_act"] == speech_act and speech_act != "":
                            is_duplicate = True
                            break

                current_scene_events.append(event.id)

                if is_duplicate:
                    # Collapse identical duplicate into a narrative action / reaction cue
                    if "warn" in speech_act or "running out" in dialogue_text.lower():
                        reaction_text = f"{speaker_name} glances back, echoing the urgency."
                    elif "deny" in speech_act or "clean" in dialogue_text.lower():
                        reaction_text = f"{speaker_name} holds firm in denial."
                    elif "accuse" in speech_act:
                        reaction_text = f"{speaker_name} presses the accusation further."
                    elif "question" in speech_act:
                        reaction_text = f"{speaker_name} repeats the demand."
                    else:
                        reaction_text = f"{speaker_name} nods in tense concurrence."

                    current_scene_blocks.append(
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.ACTION,
                            text=reaction_text,
                            source_event_ids=[event.id],
                            character_id=speaker_id,
                        )
                    )
                else:
                    # Fresh dialogue: standard Fountain format
                    recent_dialogues.append({
                        "speaker_id": speaker_id,
                        "clean_text": clean_curr,
                        "words": words_curr,
                        "speech_act": speech_act,
                        "topic": topic,
                    })

                    current_scene_blocks.append(
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.CHARACTER,
                            text=speaker_name,
                            source_event_ids=[event.id],
                            character_id=speaker_id,
                        )
                    )

                    if emotion:
                        current_scene_blocks.append(
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.PARENTHETICAL,
                                text=str(emotion).lower(),
                                source_event_ids=[event.id],
                                character_id=speaker_id,
                            )
                        )

                    current_scene_blocks.append(
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.DIALOGUE,
                            text=dialogue_text,
                            source_event_ids=[event.id],
                            character_id=speaker_id,
                        )
                    )

                i += 1
                continue

            # --- 3. Other Events (Objects, Incidents, etc.) ---
            else:
                current_scene_events.append(event.id)
                current_scene_blocks.append(
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text=event.description,
                        source_event_ids=[event.id],
                        character_id=event.actor_ids[0] if event.actor_ids else None,
                    )
                )
                i += 1
                continue

        finalize_scene()

        return ScreenplayDocument(
            title=title,
            author="D3 Story Lab Simulation",
            scenes=scenes,
        )

