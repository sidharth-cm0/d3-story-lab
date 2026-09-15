"""Tests for Shot Planner psychological rationale integration and keyframe budgeting (Phase 9)."""

import pytest
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character, EmotionalState
from src.domain.event import Event, EventType
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storyboard.models import ShotType, CameraAngle, ShotPurpose
from src.storyboard.planner import StoryboardPlanner
from src.storyboard.open_model_provider import select_keyframe_indices


@pytest.fixture
def sample_world_and_screenplay():
    world = WorldState(id="world_spy", name="Cold War Dossier World")

    loc = Location(id="loc_office", name="Director's Office", description="Shadowed office with mahogany desk")
    world.locations[loc.id] = loc

    evelyn = Character(
        id="char_evelyn",
        name="Evelyn Cross",
        role="undercover agent",
        location_id="loc_office",
        emotional_state=EmotionalState(fear=0.7, anger=0.2, trust=-0.5),
        secrets=["Carries stolen microfilm in hidden coat lining"],
    )
    world.characters[evelyn.id] = evelyn

    kane = Character(
        id="char_kane",
        name="Director Kane",
        role="intelligence boss",
        location_id="loc_office",
        emotional_state=EmotionalState(fear=0.1, anger=0.8, trust=-0.8),
    )
    world.characters[kane.id] = kane

    dossier = WorldObject(
        id="obj_dossier",
        name="Classified Dossier",
        description="Red file stamped TOP SECRET",
        location_id="loc_office",
    )
    world.objects[dossier.id] = dossier

    # Events
    ev1 = Event(
        id="ev_001",
        tick=1,
        event_type=EventType.OBJECT_PICKED_UP,
        actor_ids=["char_evelyn"],
        location_id="loc_office",
        description="Evelyn inspects the classified dossier on the desk.",
    )
    ev2 = Event(
        id="ev_002",
        tick=2,
        event_type=EventType.CHARACTER_SPOKE,
        actor_ids=["char_kane", "char_evelyn"],
        location_id="loc_office",
        description="Kane confronts Evelyn about the unauthorized clearance.",
    )
    world.events[ev1.id] = ev1
    world.events[ev2.id] = ev2

    # Screenplay with CEO in scene metadata
    scene_meta = {
        "scene_purpose": "confrontation",
        "core_emotional_objective": {
            "focal_character_id": "char_evelyn",
            "focal_character_name": "Evelyn Cross",
            "immediate_desire": "Secure the cipher key and deflect suspicion",
            "immediate_obstacle": "Kane blocking the exit corridor",
            "internal_need": "Protect undercover identity",
            "subconscious_fear": "Exposure and immediate capture",
            "emotional_vulnerability": "Trembling fingers while handling documents",
            "scene_turn_expected": "Kane demands surrender",
        },
    }

    blocks = [
        ScreenplayBlock(
            id="blk_01",
            block_type=ScreenplayBlockType.ACTION,
            text="Evelyn Cross slides the dossier into her trenchcoat.",
            character_id="char_evelyn",
            source_event_ids=["ev_001"],
        ),
        ScreenplayBlock(
            id="blk_02",
            block_type=ScreenplayBlockType.CHARACTER,
            text="DIRECTOR KANE",
            character_id="char_kane",
            source_event_ids=["ev_002"],
        ),
        ScreenplayBlock(
            id="blk_03",
            block_type=ScreenplayBlockType.DIALOGUE,
            text="Step away from the files, Cross. The building is surrounded.",
            character_id="char_kane",
            source_event_ids=["ev_002"],
        ),
        ScreenplayBlock(
            id="blk_04",
            block_type=ScreenplayBlockType.CHARACTER,
            text="EVELYN CROSS",
            character_id="char_evelyn",
            source_event_ids=["ev_002"],
        ),
        ScreenplayBlock(
            id="blk_05",
            block_type=ScreenplayBlockType.DIALOGUE,
            text="You have no jurisdiction here, Director.",
            character_id="char_evelyn",
            source_event_ids=["ev_002"],
        ),
    ]

    scene = ScreenplayScene(
        scene_number=1,
        location_id="loc_office",
        heading="INT. DIRECTOR'S OFFICE - NIGHT",
        blocks=blocks,
        source_event_ids=["ev_001", "ev_002"],
        metadata=scene_meta,
    )

    doc = ScreenplayDocument(
        title="The Missing Dossier",
        scenes=[scene],
    )

    return world, doc


def test_shot_planner_integrates_ceo_into_focal_character_rationale(sample_world_and_screenplay):
    world, doc = sample_world_and_screenplay
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")

    shot_plan = planner.plan_shots(doc, world=world, project_id="proj_spy")

    # Find panels featuring Evelyn (focal character)
    evelyn_panels = [
        p for p in shot_plan.panels
        if "Evelyn" in p.character_names or p.characters_present == ["char_evelyn"]
    ]
    assert len(evelyn_panels) >= 1

    # Check that focal character panels incorporate the Core Emotional Objective
    for p in evelyn_panels:
        rationale = p.psychological_rationale or p.metadata.get("psychological_rationale", "")
        assert "focal objective" in rationale.lower()
        # Verify specific objective fragments are present
        assert ("secure the cipher key" in rationale.lower() or
                "kane blocking the exit" in rationale.lower() or
                "protect undercover identity" in rationale.lower())
        assert p.metadata.get("is_focal_character") is True
        assert "core_emotional_objective" in p.metadata

    # Check establishing shot rationale
    est_panel = shot_plan.panels[0]
    assert est_panel.narrative_purpose == ShotPurpose.ESTABLISH
    assert "Secure the cipher key" in est_panel.psychological_rationale


def test_shot_planner_non_focal_character_does_not_usurp_ceo(sample_world_and_screenplay):
    world, doc = sample_world_and_screenplay
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")

    shot_plan = planner.plan_shots(doc, world=world, project_id="proj_spy")

    # Find Kane dialogue panel
    kane_panels = [
        p for p in shot_plan.panels
        if "Director Kane" in p.character_names or "DIRECTOR KANE" in p.caption
    ]
    assert len(kane_panels) >= 1
    kane_panel = kane_panels[0]

    # Kane is NOT focal character
    assert kane_panel.metadata.get("is_focal_character") is False
    rationale = kane_panel.psychological_rationale or kane_panel.metadata.get("psychological_rationale", "")
    assert "authority" in rationale.lower() or "dominance" in rationale.lower() or "intimacy" in rationale.lower()


def test_keyframe_budget_enforcement(sample_world_and_screenplay):
    world, doc = sample_world_and_screenplay
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")

    # Test budget = 4
    plan_4 = planner.plan_shots(doc, world=world, keyframe_budget=4)
    keyframes_4 = [p for p in plan_4.panels if p.is_keyframe]
    assert len(keyframes_4) <= 4

    # Test budget = 8
    plan_8 = planner.plan_shots(doc, world=world, keyframe_budget=8)
    keyframes_8 = [p for p in plan_8.panels if p.is_keyframe]
    assert len(keyframes_8) <= min(8, len(plan_8.panels))

    # Test hard cap at 12 even if larger budget requested
    plan_12 = planner.plan_shots(doc, world=world, keyframe_budget=20)
    keyframes_12 = [p for p in plan_12.panels if p.is_keyframe]
    assert len(keyframes_12) <= 12


def test_procedural_svg_never_masquerades_as_final_artwork(sample_world_and_screenplay):
    world, doc = sample_world_and_screenplay
    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")
    shot_plan = planner.plan_shots(doc, world=world, keyframe_budget=4)

    # In planned state, rendered_svg and image_url must never contain raw svg artwork as final
    for p in shot_plan.panels:
        assert p.rendered_svg is None or p.rendered_svg == ""
        # SVG is only allowed as a previs guide reference, not as final artwork url
        if p.image_url:
            assert not p.image_url.endswith(".svg")
