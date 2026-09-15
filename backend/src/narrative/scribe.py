"""Scribe agent for converting simulation events into Fountain screenplays with subtext and spatial awareness."""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Set
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
from src.narrative.subtext import SubtextAnalyzer, DeceptionClassification
from src.narrative.performance_cues import PerformanceCueGenerator, PerformanceCue
from src.narrative.spatial import SpatialReasoner, SpatialContext
from src.narrative.framer import NarrativeFramer, FramingMode
from src.narrative.scene_purpose import ScenePurposeAnalyzer
from src.narrative.scene_builder import SceneBuilder
from src.domain.story_structure import ScenePurposeType
from src.providers.base import LLMProvider


class Scribe:
    """Converts verified narrative beats into standard Fountain screenplays."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider
        self.subtext_analyzer = SubtextAnalyzer()
        self.cue_generator = PerformanceCueGenerator()
        self.spatial_reasoner = SpatialReasoner()
        self.framer = NarrativeFramer()
        self.purpose_analyzer = ScenePurposeAnalyzer()
        self.scene_builder = SceneBuilder()

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
        return char_id.replace("char_", "").replace("_", " ").upper()

    def _extract_dialogue_text(self, event: Event) -> tuple[str, Optional[str]]:
        """Extract spoken dialogue and optional parenthetical from event."""
        if "dialogue" in event.metadata and event.metadata["dialogue"]:
            text = str(event.metadata["dialogue"])
            emotion = event.metadata.get("emotion", None)
            return text, emotion

        desc = event.description
        quotes = re.findall(r"['\"](.*?)['\"]", desc)
        if quotes:
            return quotes[0], None

        if ":" in desc:
            return desc.split(":", 1)[1].strip(), None

        return desc, None

    def compose_screenplay(
        self,
        selection: NarrativeEventSelection,
        world: WorldState,
        title: str = "EMERGENT NARRATIVE",
        framing_mode: FramingMode = FramingMode.CHRONOLOGICAL,
    ) -> ScreenplayDocument:
        """Transform narrative beats into a verified ScreenplayDocument with subtext and spatial awareness."""
        events: List[Event] = []
        seen_event_ids = set()
        for beat in selection.filtered_beats:
            for eid in beat.source_event_ids:
                if eid not in seen_event_ids and eid in world.events:
                    seen_event_ids.add(eid)
                    events.append(world.events[eid])

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
        surfaced_spatial_notes: Set[str] = set()
        scene_counter = 0

        def finalize_scene():
            nonlocal scene_counter, current_scene_blocks, current_scene_events, current_location_id, surfaced_spatial_notes
            if current_scene_blocks:
                scene_counter += 1
                heading = self._format_scene_heading(current_location_id or "UNKNOWN", world)
                temp_scene = ScreenplayScene(
                    scene_number=scene_counter,
                    location_id=current_location_id or "unknown",
                    heading=heading,
                    blocks=list(current_scene_blocks),
                    source_event_ids=list(dict.fromkeys(current_scene_events)),
                )

                # Derive scene purpose, goal, and turning points
                analysis = self.purpose_analyzer.analyze_scene(temp_scene, world)
                sc_events = [world.events[eid] for eid in current_scene_events if eid in world.events]
                focal_id = self.scene_builder._determine_focal_character(sc_events, world) or "char_protagonist"
                purpose_type = ScenePurposeType(analysis.purpose.value) if analysis.purpose.value in ScenePurposeType._value2member_map_ else ScenePurposeType.SETUP
                ceo = self.scene_builder._derive_core_emotional_objective(
                    focal_char_id=focal_id,
                    events=sc_events,
                    world=world,
                    scene_purpose=purpose_type,
                )

                meta = {
                    "scene_purpose": analysis.purpose.value,
                    "core_emotional_objective": ceo.model_dump(mode="json"),
                    "dramatic_question": analysis.dramatic_question,
                    "scene_goal": ceo.immediate_desire,
                    "scene_obstacle": ceo.immediate_obstacle,
                    "turning_point": analysis.turning_point,
                    "scene_outcome": analysis.scene_outcome,
                }
                scenes.append(
                    ScreenplayScene(
                        scene_number=scene_counter,
                        location_id=current_location_id or "unknown",
                        heading=heading,
                        blocks=list(current_scene_blocks),
                        source_event_ids=list(dict.fromkeys(current_scene_events)),
                        metadata=meta,
                    )
                )
                current_scene_blocks = []
                current_scene_events = []
                surfaced_spatial_notes = set()

        recent_dialogues: List[dict] = []
        dialogue_since_last_paren = 999

        i = 0
        while i < len(events):
            event = events[i]
            event_loc = event.location_id or "unknown"

            # Check transient pass-through
            is_transient_pass_through = False
            if current_location_id is not None and event_loc != current_location_id:
                if i + 1 < len(events) and events[i + 1].location_id == current_location_id:
                    if event.event_type != EventType.CHARACTER_SPOKE:
                        is_transient_pass_through = True

            target_scene_loc = current_location_id if is_transient_pass_through else event_loc

            if current_location_id is None:
                current_location_id = target_scene_loc
            elif target_scene_loc != current_location_id:
                finalize_scene()
                current_location_id = target_scene_loc

            # Spatial awareness check: surface dramatic spatial facts if newly relevant
            if current_location_id and current_location_id in world.locations:
                spatial_ctx = self.spatial_reasoner.compute_spatial_context(current_location_id, world)
                for note in spatial_ctx.narrative_spatial_notes:
                    if note not in surfaced_spatial_notes:
                        surfaced_spatial_notes.add(note)
                        # Surface spatial tension when multiple actors present or tactical obstacle exists
                        if len(spatial_ctx.actor_states) >= 2 or spatial_ctx.geometry.blocked_exits:
                            current_scene_blocks.append(
                                ScreenplayBlock(
                                    block_type=ScreenplayBlockType.ACTION,
                                    text=note,
                                    source_event_ids=[event.id],
                                    character_id=event.actor_ids[0] if event.actor_ids else None,
                                    metadata={"spatial_tension": True},
                                )
                            )
                            break  # Surface one tactical note at a time to preserve rhythm

            # --- 1. Movement Merging & Pacing ---
            if event.event_type == EventType.CHARACTER_MOVED:
                next_ev = events[i + 1] if i + 1 < len(events) else None
                if next_ev and next_ev.event_type == EventType.CHARACTER_MOVED and abs(next_ev.tick - event.tick) <= 1:
                    actor1 = world.characters.get(event.actor_ids[0]) if event.actor_ids else None
                    actor2 = world.characters.get(next_ev.actor_ids[0]) if next_ev.actor_ids else None
                    name1 = actor1.name if actor1 else "Figure"
                    name2 = actor2.name if actor2 else "Figure"

                    dest1 = event.metadata.get("to_location_name") or (world.locations[event.location_id].name if event.location_id in world.locations else "the adjacent area")
                    dest2 = next_ev.metadata.get("to_location_name") or (world.locations[next_ev.location_id].name if next_ev.location_id in world.locations else "the adjacent area")

                    if actor1 and actor2 and actor1.id != actor2.id and (dest1 == dest2 or event.location_id == next_ev.location_id):
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
                        orig_loc = event.metadata.get("from_location_name") or "the suite"
                        merged_text = f"{name1} glances into {dest1}, then retreats to {orig_loc}."
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

            # --- 2. Dialogue Processing with Subtext and Performance Cues ---
            elif event.event_type == EventType.CHARACTER_SPOKE:
                speaker_id = event.actor_ids[0] if event.actor_ids else "SPEAKER"
                speaker_name = self._resolve_character_name(speaker_id, world)
                dialogue_text, raw_emotion = self._extract_dialogue_text(event)
                speech_act = event.metadata.get("speech_act", "").lower()
                topic = event.metadata.get("topic", "").lower()

                # Clean dialogue for deduplication check
                def clean_dialogue(text: str) -> str:
                    t = text.lower()
                    for c in world.characters.values():
                        t = t.replace(c.name.lower(), "")
                    return re.sub(r"[^a-z0-9\s]", "", t).strip()

                clean_curr = clean_dialogue(dialogue_text)
                words_curr = set(clean_curr.split())

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
                    # Collapse duplicate into reaction cue
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
                    recent_dialogues.append({
                        "speaker_id": speaker_id,
                        "clean_text": clean_curr,
                        "words": words_curr,
                        "speech_act": speech_act,
                        "topic": topic,
                    })

                    # Perform Subtext & Deception Analysis
                    speaker_char = world.characters.get(speaker_id)
                    perf_cue: Optional[PerformanceCue] = None

                    if speaker_char:
                        # Identify interlocutor (another character in same room)
                        listener_id = None
                        loc_id = getattr(speaker_char, "current_location_id", None) or getattr(speaker_char, "location_id", None)
                        for other_id, other_char in world.characters.items():
                            other_loc = getattr(other_char, "current_location_id", None) or getattr(other_char, "location_id", None)
                            if other_id != speaker_id and other_loc == loc_id:
                                listener_id = other_id
                                break

                        subtext_res = self.subtext_analyzer.analyze(
                            speaker=speaker_char,
                            dialogue=dialogue_text,
                            world=world,
                            listener_id=listener_id,
                            event_metadata=event.metadata,
                        )

                        # Prefer action cue to avoid parenthetical stacking
                        prefer_action = (dialogue_since_last_paren < 3)
                        perf_cue = self.cue_generator.generate_cue(
                            analysis=subtext_res,
                            character=speaker_char,
                            world=world,
                            source_event_id=event.id,
                            prefer_action=prefer_action,
                        )

                    # Character heading
                    current_scene_blocks.append(
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.CHARACTER,
                            text=speaker_name,
                            source_event_ids=[event.id],
                            character_id=speaker_id,
                        )
                    )

                    # Optional Parenthetical (Enforce strict spacing cooldown to avoid overuse)
                    dialogue_since_last_paren += 1
                    paren_text = (perf_cue.parenthetical_text if perf_cue else None) or (str(raw_emotion).lower() if raw_emotion else None)
                    if paren_text and dialogue_since_last_paren >= 3:
                        dialogue_since_last_paren = 0
                        current_scene_blocks.append(
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.PARENTHETICAL,
                                text=paren_text,
                                source_event_ids=[event.id],
                                character_id=speaker_id,
                            )
                        )

                    # Spoken dialogue
                    current_scene_blocks.append(
                        ScreenplayBlock(
                            block_type=ScreenplayBlockType.DIALOGUE,
                            text=dialogue_text,
                            source_event_ids=[event.id],
                            character_id=speaker_id,
                        )
                    )

                    # Observable physical performance cue as action beat (SHOW, DON'T TELL)
                    if perf_cue and perf_cue.action_text:
                        current_scene_blocks.append(
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.ACTION,
                                text=perf_cue.action_text,
                                source_event_ids=[event.id],
                                character_id=speaker_id,
                                derived_from_event_id=event.id,
                                derived_from_actor_state_ids=perf_cue.derived_from_actor_state_ids,
                                cue_type=perf_cue.cue_type.value,
                                is_performance_cue=True,
                            )
                        )

                i += 1
                continue

            # --- 3. Object & Physical Incident Events ---
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

        # Apply Narrative Framing (Chronological or Non-Linear In-Media-Res / Flashback)
        framed_scenes = self.framer.reorder_presentation(scenes, mode=framing_mode)

        return ScreenplayDocument(
            title=title,
            author="D3 Story Lab Simulation",
            scenes=framed_scenes,
        )
