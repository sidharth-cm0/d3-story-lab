"""Tests for SceneBuilder, scene_purpose, and CoreEmotionalObjective derivation."""

import pytest
from src.domain.world import WorldState, Location, Character, Goal
from src.domain.event import Event, EventType
from src.domain.story_structure import ScenePurposeType, SceneData, CoreEmotionalObjective
from src.narrative.observer import NarrativeEventSelection, NarrativeBeat, NarrativeBeatType
from src.narrative.scene_builder import SceneBuilder
from src.narrative.scribe import Scribe
from src.narrative.framer import FramingMode


def test_scene_builder_constructs_scenes_with_purpose_and_objective():
    """Verify that SceneBuilder creates SceneData with explicit scene_purpose and CoreEmotionalObjective."""
    loc_main = Location(id="loc_warehouse", name="Abandoned Warehouse", connected_locations=["loc_office"])
    loc_office = Location(id="loc_office", name="Locked Office", connected_locations=["loc_warehouse"])

    char_det = Character(id="char_det", name="Detective Miller", role="Undercover Detective", current_location_id="loc_warehouse")
    char_courier = Character(id="char_courier", name="Leo Vance", role="Courier", current_location_id="loc_warehouse")

    goal_det = Goal(id="goal_1", character_id="char_det", description="Recover the stolen classified dossier before midnight")

    world = WorldState(
        id="test_world",
        name="Warehouse World",
        current_tick=5,
        locations={"loc_warehouse": loc_main, "loc_office": loc_office},
        characters={"char_det": char_det, "char_courier": char_courier},
        goals={"goal_1": goal_det},
    )

    # Synthetic events with strict IDs
    ev1 = Event(id="ev_01", tick=1, event_type=EventType.CHARACTER_MOVED, description="Detective Miller enters the abandoned warehouse.", actor_ids=["char_det"], location_id="loc_warehouse")
    ev2 = Event(id="ev_02", tick=2, event_type=EventType.CHARACTER_SPOKE, description="Leo Vance insists he knows nothing about any classified documents.", actor_ids=["char_courier"], location_id="loc_warehouse", metadata={"dialogue": "I just work here, man. I don't know nothing about no dossier."})
    ev3 = Event(id="ev_03", tick=3, event_type=EventType.CHARACTER_OBSERVED, description="Detective Miller notices a heavy padlock on the back office door.", actor_ids=["char_det"], location_id="loc_warehouse")
    ev4 = Event(id="ev_04", tick=4, event_type=EventType.CHARACTER_MOVED, description="Detective Miller steps into the locked office.", actor_ids=["char_det"], location_id="loc_office")
    ev5 = Event(id="ev_05", tick=5, event_type=EventType.CHARACTER_OBSERVED, description="Detective Miller discovers the classified dossier hidden inside a filing cabinet.", actor_ids=["char_det"], location_id="loc_office")

    for ev in [ev1, ev2, ev3, ev4, ev5]:
        world.events[ev.id] = ev

    # Observer selection
    beat_1 = NarrativeBeat(
        id="beat_wh",
        beat_type=NarrativeBeatType.ESTABLISHING,
        start_tick=1,
        end_tick=3,
        location_id="loc_warehouse",
        character_ids=["char_det", "char_courier"],
        dramatic_score=0.75,
        summary="Confrontation in warehouse",
        source_event_ids=["ev_01", "ev_02", "ev_03"],
    )
    beat_2 = NarrativeBeat(
        id="beat_off",
        beat_type=NarrativeBeatType.REVELATION,
        start_tick=4,
        end_tick=5,
        location_id="loc_office",
        character_ids=["char_det"],
        dramatic_score=0.90,
        summary="Dossier discovery in office",
        source_event_ids=["ev_04", "ev_05"],
    )

    selection = NarrativeEventSelection(
        total_events_observed=5,
        filtered_beats=[beat_1, beat_2],
        dramatic_arc_summary="Undercover search leads to locked office discovery",
        tension_progression=[0.6, 0.9],
    )

    builder = SceneBuilder()
    scenes = builder.build_scenes(selection, world)

    assert len(scenes) == 2

    # Verify Scene 1
    scene1 = scenes[0]
    assert scene1.scene_number == 1
    assert scene1.location_id == "loc_warehouse"
    assert scene1.location_name == "Abandoned Warehouse"
    assert scene1.scene_purpose in (ScenePurposeType.SETUP, ScenePurposeType.INVESTIGATION, ScenePurposeType.CONFRONTATION)
    assert scene1.core_emotional_objective is not None
    assert scene1.core_emotional_objective.focal_character_id == "char_det"
    assert scene1.core_emotional_objective.immediate_desire
    assert scene1.core_emotional_objective.immediate_obstacle
    assert "ev_01" in scene1.source_event_ids
    assert "ev_02" in scene1.source_event_ids

    # Verify Scene 2
    scene2 = scenes[1]
    assert scene2.scene_number == 2
    assert scene2.location_id == "loc_office"
    assert scene2.scene_purpose in (ScenePurposeType.DISCOVERY, ScenePurposeType.REVELATION)
    assert scene2.core_emotional_objective is not None
    assert "ev_04" in scene2.source_event_ids
    assert "ev_05" in scene2.source_event_ids

    # Verify Scribe integrates CoreEmotionalObjective into screenplay scene metadata
    scribe = Scribe()
    doc = scribe.compose_screenplay(selection, world, title="DOSSIER RECOVERY", framing_mode=FramingMode.CHRONOLOGICAL)
    assert len(doc.scenes) >= 2
    for sc in doc.scenes:
        assert "scene_purpose" in sc.metadata
        assert "core_emotional_objective" in sc.metadata
        assert sc.metadata["core_emotional_objective"]["immediate_desire"]
