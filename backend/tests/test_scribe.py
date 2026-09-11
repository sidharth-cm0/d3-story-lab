"""Tests for Scribe and Fountain screenplay exporter."""

import pytest
from src.domain.event import Event, EventType
from src.domain.character import Character
from src.domain.world import WorldState, Location
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.fountain import ScreenplayBlockType


class TestScribeAndFountain:
    @pytest.fixture
    def populated_world_and_events(self) -> tuple[WorldState, list[Event]]:
        world = WorldState(id="world_1", name="Hotel World")
        # Locations
        penthouse = Location(id="loc_penthouse", name="Hotel Penthouse", description="Luxurious suite overlooking the bay.")
        lobby = Location(id="loc_lobby", name="Hotel Lobby", description="Grand lobby with marble columns.")
        world.locations[penthouse.id] = penthouse
        world.locations[lobby.id] = lobby

        # Characters
        maya = Character(id="char_maya", name="Maya Lin", role="Journalist", location_id="loc_penthouse")
        arjun = Character(id="char_arjun", name="Arjun Mehta", role="Diplomat", location_id="loc_penthouse")
        world.characters[maya.id] = maya
        world.characters[arjun.id] = arjun

        # Events
        events = [
            Event(
                id="evt_101",
                tick=1,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_maya"],
                location_id="loc_penthouse",
                description="Maya quietly enters the Hotel Penthouse.",
            ),
            Event(
                id="evt_102",
                tick=2,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_maya", "char_arjun"],
                location_id="loc_penthouse",
                description="Maya says: 'I know about the offshore accounts, Arjun.'",
                metadata={"dialogue": "I know about the offshore accounts, Arjun.", "emotion": "tense"},
            ),
            Event(
                id="evt_103",
                tick=3,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_arjun", "char_maya"],
                location_id="loc_penthouse",
                description="Arjun says: 'You shouldn't have come here.'",
                metadata={"dialogue": "You shouldn't have come here."},
            ),
            Event(
                id="evt_104",
                tick=5,
                event_type=EventType.OTHER,
                actor_ids=[],
                location_id="loc_penthouse",
                description="A heavy fist knocks three times against the locked suite door.",
                metadata={"incident_type": "KNOCK_ON_DOOR"},
            ),
            Event(
                id="evt_105",
                tick=6,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_arjun"],
                location_id="loc_lobby",
                description="Arjun retreats hastily into the Hotel Lobby.",
            ),
        ]

        for e in events:
            world.events[e.id] = e

        return world, events

    def test_scribe_composes_screenplay_with_scenes(self, populated_world_and_events):
        world, events = populated_world_and_events
        observer = Observer()
        selection = observer.observe_events(events, world)

        scribe = Scribe()
        doc = scribe.compose_screenplay(selection, world, title="THE HOTEL CONFRONTATION")

        assert doc.title == "THE HOTEL CONFRONTATION"
        assert len(doc.scenes) == 2  # Penthouse scene, then Lobby scene
        assert doc.scenes[0].heading == "INT. HOTEL PENTHOUSE - CONTINUOUS"
        assert doc.scenes[1].heading == "INT. HOTEL LOBBY - CONTINUOUS"

    def test_dialogue_formatting_and_speaker_cue(self, populated_world_and_events):
        world, events = populated_world_and_events
        observer = Observer()
        selection = observer.observe_events(events, world)

        scribe = Scribe()
        doc = scribe.compose_screenplay(selection, world)

        scene = doc.scenes[0]
        char_blocks = [b for b in scene.blocks if b.block_type == ScreenplayBlockType.CHARACTER]
        dial_blocks = [b for b in scene.blocks if b.block_type == ScreenplayBlockType.DIALOGUE]

        assert any(b.text == "MAYA LIN" for b in char_blocks)
        assert any(b.text == "ARJUN MEHTA" for b in char_blocks)
        assert any("offshore accounts" in b.text for b in dial_blocks)
        assert any("You shouldn't have come here" in b.text for b in dial_blocks)

    def test_strict_provenance_to_source_events(self, populated_world_and_events):
        world, events = populated_world_and_events
        observer = Observer()
        selection = observer.observe_events(events, world)

        scribe = Scribe()
        doc = scribe.compose_screenplay(selection, world)
        prov_map = doc.get_provenance_map()

        assert len(prov_map) > 0
        raw_event_ids = {e.id for e in events}

        for block_id, source_ids in prov_map.items():
            assert len(source_ids) > 0
            for sid in source_ids:
                assert sid in raw_event_ids

    def test_to_fountain_text_output(self, populated_world_and_events):
        world, events = populated_world_and_events
        observer = Observer()
        selection = observer.observe_events(events, world)

        scribe = Scribe()
        doc = scribe.compose_screenplay(selection, world, title="SHADOW IN SUITE 4B")
        fountain_txt = doc.to_fountain()

        assert "Title: SHADOW IN SUITE 4B" in fountain_txt
        assert "INT. HOTEL PENTHOUSE - CONTINUOUS" in fountain_txt
        assert "MAYA LIN" in fountain_txt
        assert "(tense)" in fountain_txt
        assert "I know about the offshore accounts, Arjun." in fountain_txt
        assert "A heavy fist knocks three times" in fountain_txt
        assert "INT. HOTEL LOBBY - CONTINUOUS" in fountain_txt

    def test_dialogue_deduplication_and_movement_merging(self):
        """Verify Scribe merges consecutive movements and collapses repeated identical lines."""
        world = WorldState(id="w_dup", name="Deduplication World")
        suite = Location(id="loc_suite", name="Private Suite", description="Locked room")
        hall = Location(id="loc_corridor", name="Service Corridor", description="Dim hallway")
        world.locations[suite.id] = suite
        world.locations[hall.id] = hall

        jordan = Character(id="char_jordan", name="Jordan", role="Journalist", location_id="loc_suite")
        morgan = Character(id="char_morgan", name="Morgan", role="Investigator", location_id="loc_suite")
        world.characters[jordan.id] = jordan
        world.characters[morgan.id] = morgan

        # 1. Consecutive movements to same destination
        # 2. Repeated identical dialogue lines ("Time is running out...")
        # 3. Movement back to suite
        events = [
            Event(
                id="e1",
                tick=1,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_jordan"],
                location_id="loc_corridor",
                description="Jordan moved from Private Suite to Service Corridor.",
                metadata={"to_location_name": "Service Corridor", "from_location_name": "Private Suite"},
            ),
            Event(
                id="e2",
                tick=1,
                event_type=EventType.CHARACTER_MOVED,
                actor_ids=["char_morgan"],
                location_id="loc_corridor",
                description="Morgan moved from Private Suite to Service Corridor.",
                metadata={"to_location_name": "Service Corridor", "from_location_name": "Private Suite"},
            ),
            Event(
                id="e3",
                tick=2,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_jordan", "char_morgan"],
                location_id="loc_corridor",
                description="Jordan said to Morgan: \"Time is running out, Morgan. Whoever orchestrates this isn't leaving loose ends.\"",
                metadata={"speech_act": "warn", "dialogue": "Time is running out, Morgan. Whoever orchestrates this isn't leaving loose ends."},
            ),
            Event(
                id="e4",
                tick=2,
                event_type=EventType.CHARACTER_SPOKE,
                actor_ids=["char_morgan", "char_jordan"],
                location_id="loc_corridor",
                description="Morgan said to Jordan: \"Time is running out, Jordan. Whoever orchestrates this isn't leaving loose ends.\"",
                metadata={"speech_act": "warn", "dialogue": "Time is running out, Jordan. Whoever orchestrates this isn't leaving loose ends."},
            ),
        ]
        for e in events:
            world.events[e.id] = e

        observer = Observer()
        selection = observer.observe_events(events, world)

        scribe = Scribe()
        doc = scribe.compose_screenplay(selection, world, title="CORRIDOR TENSION")

        # 1. Merged movement block
        action_blocks = [b for s in doc.scenes for b in s.blocks if b.block_type == ScreenplayBlockType.ACTION]
        assert any("Jordan steps into Service Corridor. Morgan follows." in b.text for b in action_blocks)

        # 2. Dialogue deduplicated: Only one spoken DIALOGUE block for the warning
        dial_blocks = [b for s in doc.scenes for b in s.blocks if b.block_type == ScreenplayBlockType.DIALOGUE]
        assert len(dial_blocks) == 1, f"Expected 1 dialogue block, got {len(dial_blocks)}"
        assert "Time is running out" in dial_blocks[0].text

        # 3. Second speaker collapsed into reaction action line
        assert any("glances back, echoing the urgency" in b.text for b in action_blocks)

        # 4. Strict provenance: all 4 event IDs are preserved in blocks
        all_source_ids = {sid for s in doc.scenes for b in s.blocks for sid in b.source_event_ids}
        assert all_source_ids == {"e1", "e2", "e3", "e4"}

