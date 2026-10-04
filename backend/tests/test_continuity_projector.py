"""Tests for ContinuityProjector and Storyboard continuity prompt integration.

Phase G4, G5, G6 verification:
- Derivation of story-caused temporary visual states (wetness, injuries, damage, carried objects).
- Provenance tracking with real source event IDs.
- Read-only invariant: world state and events remain unmutated.
- Integration with StoryboardPromptBuilder and GroundedStoryboardRenderer.
"""

import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character
from src.domain.character_reference import CharacterReferenceProfile
from src.domain.event import Event, EventType
from src.storyboard.continuity_projector import (
    CharacterContinuityState,
    ContinuityProjector,
)
from src.storyboard.keyframe_rendering import (
    ContinuityPack,
    StoryboardPromptBuilder,
    LocationVisualRef,
    CharacterVisualRef,
)
from src.storyboard.shot_planner import ShotPlan, ShotType, CameraAngle, CompositionPlan


def test_continuity_projector_derives_injuries_and_damage_with_provenance():
    """Verify projector inspects canonical events and outputs temporary visual effects with event IDs."""
    events = [
        Event(
            id="evt_001",
            tick=1,
            event_type=EventType.CHARACTER_MOVED,
            actor_ids=["char_elena"],
            location_id="loc_rainy_courtyard",
            description="Elena dashes through torrential rain across the flooded courtyard.",
        ),
        Event(
            id="evt_002",
            tick=2,
            event_type=EventType.OTHER,
            actor_ids=["char_guard", "char_elena"],
            location_id="loc_corridor",
            description="A brutal struggle ensues; Elena is shoved into broken glass and sustains a laceration.",
        ),
        Event(
            id="evt_003",
            tick=3,
            event_type=EventType.OBJECT_PICKED_UP,
            actor_ids=["char_elena"],
            location_id="loc_vault",
            description="Elena seizes the red dossier obj_dossier from the vault shelf.",
            metadata={"object_id": "obj_dossier"},
        ),
    ]

    state = ContinuityProjector.project_character_continuity(
        character_id="char_elena",
        events=events,
        tick=3,
    )

    assert state.character_id == "char_elena"
    assert state.tick == 3
    # Check wetness derived from rain event
    assert state.wetness is not None
    assert "wet" in state.wetness or "rain" in state.wetness
    assert "evt_001" in state.source_event_ids

    # Check injuries or damage derived from struggle event
    assert state.injuries or state.clothing_damage or state.dirt_or_blood
    assert "evt_002" in state.source_event_ids

    # Check carried object
    assert "obj_dossier" in state.carried_objects
    assert "evt_003" in state.source_event_ids

    # Check summary description
    summary = state.summary_description()
    assert summary != "normal baseline appearance"
    assert "holding obj_dossier" in summary


def test_continuity_projector_read_only_invariance():
    """Verify projection does not mutate events or world state."""
    world = WorldState(
        id="world_test",
        name="Test Laboratory",
        current_tick=2,
        locations={"loc_lab": Location(id="loc_lab", name="Research Lab")},
        characters={
            "char_marcus": Character(
                id="char_marcus",
                name="Marcus",
                role="Scientist",
                location_id="loc_lab",
                reference_profile=CharacterReferenceProfile(baseline_wardrobe="white lab coat"),
            )
        },
    )

    events = [
        Event(
            id="evt_fire_01",
            tick=1,
            event_type=EventType.OTHER,
            actor_ids=["char_marcus"],
            location_id="loc_lab",
            description="A chemical explosion scorches the workbench with soot and smoke.",
        )
    ]

    # Pre-state snapshots
    char_wardrobe_before = world.characters["char_marcus"].reference_profile.baseline_wardrobe
    event_dict_before = events[0].model_dump()

    continuity = ContinuityProjector.project_scene_continuity(
        world=world,
        events=events,
        scene_id="scene_lab",
    )

    # Post-state verification: world and events are unaltered
    assert world.characters["char_marcus"].reference_profile.baseline_wardrobe == char_wardrobe_before
    assert events[0].model_dump() == event_dict_before
    assert "char_marcus" in continuity


def test_prompt_builder_incorporates_temporary_continuity():
    """Verify StoryboardPromptBuilder appends temporary continuity and changes content hash."""
    prompt_builder = StoryboardPromptBuilder()

    shot = ShotPlan(
        shot_id="shot_101",
        scene_id="scene_corridor",
        screenplay_block_ids=["blk_1"],
        source_event_ids=["evt_001"],
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.EYE_LEVEL,
        lens_feel="50mm prime",
        subject_focus="char_elena",
        emotion="determined focus",
        rationale="Close-up highlighting intensity",
        composition_plan=CompositionPlan(focal_point="center"),
    )

    clean_continuity = ContinuityPack(
        shot_id="shot_101",
        character_refs=[
            CharacterVisualRef(
                character_id="char_elena",
                face="angular features",
                hair="short dark crop",
                age_descriptor="mid 30s",
                build="lean",
                wardrobe="tailored suit",
                palette="charcoal",
            )
        ],
        location_ref=LocationVisualRef(
            location_id="loc_corridor",
            architecture="concrete hallway",
            layout="long rectangular passage",
            doors="metal doors",
            windows="none",
            materials="bare concrete",
            lighting="fluorescent flicker",
            landmarks="water pipe",
        ),
    )

    prompt_clean, hash_clean = prompt_builder.build_prompt(shot, clean_continuity)
    assert "CONTINUITY" not in prompt_clean

    # Add temporary continuity state
    injured_continuity = clean_continuity.model_copy(deep=True)
    injured_continuity.character_continuity_states = {
        "char_elena": CharacterContinuityState(
            character_id="char_elena",
            injuries=["split lip", "bruised jaw"],
            wetness="soaking wet coat",
            source_event_ids=["evt_001"],
        )
    }

    prompt_injured, hash_injured = prompt_builder.build_prompt(shot, injured_continuity)
    assert "CONTINUITY:" in prompt_injured
    assert "split lip" in prompt_injured or "soaking wet" in prompt_injured
    # Invariant: prompt hash must differ when visual continuity changes
    assert hash_clean != hash_injured
