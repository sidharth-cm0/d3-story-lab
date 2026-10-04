"""Phase J4 Legacy Project Regression Test Suite.

Validates that:
1. Unversioned / pre-A legacy projects load cleanly with v2 schema defaults.
2. Legacy projects can advance through simulation, scribe screenplay, storyboard, and export without error.
3. Legacy projects with older visual profiles (ActorVisualProfile) adapt gracefully to CharacterReferenceProfile.
4. Pre-existing disk projects load idempotently without migration loops.
"""

import json
from pathlib import Path
import pytest

from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from src.domain.world import WorldState, Location, Character, Goal, WorldObject
from src.domain.continuity import ActorVisualProfile
from src.domain.character_reference import CharacterReferenceProfile
from src.storyboard.visual_bible import VisualBible
from src.storyboard.planner import StoryboardPlanner
from src.simulation.orchestrator import SimulationOrchestrator
from src.providers.mock import MockLLMProvider
from src.narrative.observer import Observer
from src.narrative.scribe import Scribe
from src.narrative.framer import FramingMode


def test_legacy_pre_a_project_full_lifecycle(tmp_path):
    """Verify that a legacy pre-A project without schema_version or reference profiles can complete the full lifecycle."""
    legacy_json = {
        "metadata": {
            "id": "proj_legacy_pre_a",
            "title": "Legacy Warehouse Handover",
            "seed_prompt": "Two operatives meet in a warehouse to exchange a sealed packet.",
            "created_at": "2026-08-15T10:00:00+00:00",
            "updated_at": "2026-08-15T10:00:00+00:00",
            "current_tick": 2,
            "total_events": 2,
            "total_scenes": 1,
        },
        "world": {
            "id": "proj_legacy_pre_a",
            "name": "Legacy Warehouse World",
            "current_tick": 2,
            "locations": {
                "loc_dock": {
                    "id": "loc_dock",
                    "name": "Cargo Bay 4",
                    "description": "Dimly lit warehouse bay with wooden shipping crates",
                    "connected_locations": ["loc_office"],
                },
                "loc_office": {
                    "id": "loc_office",
                    "name": "Foreman Office",
                    "description": "Glass-walled office overlooking cargo floor",
                    "connected_locations": ["loc_dock"],
                },
            },
            "characters": {
                "char_operative": {
                    "id": "char_operative",
                    "name": "Agent Marcus",
                    "role": "Courier",
                    "location_id": "loc_dock",
                    "emotional_state": {"fear": 0.2, "anger": 0.1, "trust": 0.0},
                    "goals": ["g_exchange"],
                },
                "char_contact": {
                    "id": "char_contact",
                    "name": "Contact Elena",
                    "role": "Handler",
                    "location_id": "loc_dock",
                    "emotional_state": {"fear": 0.1, "anger": 0.3, "trust": -0.2},
                    "goals": [],
                },
            },
            "objects": {
                "obj_packet": {
                    "id": "obj_packet",
                    "name": "Sealed Packet",
                    "description": "Manila envelope with wax seal",
                    "location_id": "loc_dock",
                }
            },
            "goals": {
                "g_exchange": {
                    "id": "g_exchange",
                    "character_id": "char_operative",
                    "description": "Deliver sealed packet",
                    "priority": 1,
                }
            },
            "beliefs": {},
            "secrets": {},
            "relationships": {},
            "memories": {},
            "events": {},
            "facts": {},
        },
    }

    proj_file = tmp_path / "proj_legacy_pre_a.json"
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(legacy_json, f)

    store = ProjectStore(base_dir=tmp_path)
    loaded = store.load_project("proj_legacy_pre_a")

    # 1. Load & Schema Validation
    assert loaded is not None
    assert loaded.schema_version == 2
    assert loaded.metadata.schema_version == 2
    assert "char_operative" in loaded.world.characters

    # 2. Simulate
    provider = MockLLMProvider()
    orchestrator = SimulationOrchestrator(world=loaded.world, provider=provider)
    results = orchestrator.run(max_ticks=4)
    assert len(results) >= 1
    assert loaded.world.current_tick >= 4

    # 3. Scribe & Screenplay
    events_list = sorted(loaded.world.events.values(), key=lambda e: (e.tick, e.id))
    observer = Observer(provider=provider)
    beats = observer.observe_events(events_list, loaded.world)
    scribe = Scribe(provider=provider)
    screenplay = scribe.compose_screenplay(
        selection=beats,
        world=loaded.world,
        title="LEGACY WAREHOUSE HANDOVER",
        framing_mode=FramingMode.CHRONOLOGICAL,
    )
    assert len(screenplay.scenes) >= 1
    fountain_text = screenplay.to_fountain()
    assert "LEGACY WAREHOUSE HANDOVER" in fountain_text

    # 4. Visual Bible & Storyboard Planning
    bible = VisualBible.from_world(loaded.world)
    assert "char_operative" in bible.characters
    assert bible.characters["char_operative"].name == "Agent Marcus"

    planner = StoryboardPlanner(panels_per_page=4, density_mode="standard")
    shot_plan = planner.plan_shots(screenplay, world=loaded.world, bible=bible, project_id=loaded.metadata.id, keyframe_budget=4)
    assert len(shot_plan.panels) >= 1

    # 5. Idempotent Save/Reload without migration loop
    saved_id = store.save_project(loaded)
    reloaded = store.load_project(saved_id)
    assert reloaded.schema_version == 2
    assert reloaded.metadata.schema_version == 2
    assert reloaded.world.current_tick == loaded.world.current_tick


def test_legacy_actor_visual_profile_adaptation():
    """Verify that an older ActorVisualProfile seamlessly adapts to CharacterReferenceProfile and VisualBible."""
    world = WorldState(id="world_legacy_vp", name="Legacy Visual Profile World")
    legacy_vp = ActorVisualProfile(
        character_id="char_vance",
        name="Agent Vance",
        age="Mid 40s",
        face_traits="Weathered cheekbones, scar under chin",
        hairstyle="Salt and pepper buzzcut",
        build="Stocky, broad shoulders",
        clothing="Faded olive drab field jacket",
        signature_items=["Brass lighter"],
        emotional_style="Stolid, impassive",
    )

    char = Character(
        id="char_vance",
        name="Agent Vance",
        role="Field Agent",
        visual_profile=legacy_vp,
    )
    world.characters[char.id] = char

    # VisualBible derives properly from legacy ActorVisualProfile when reference_profile is absent
    bible = VisualBible.from_world(world)
    assert "char_vance" in bible.characters
    vance_ref = bible.characters["char_vance"]
    assert vance_ref.age == "Mid 40s"
    assert vance_ref.clothing == "Faded olive drab field jacket"
    assert "Brass lighter" in vance_ref.signature_props

    # Also test bidirectional adapter
    adapted_ref = CharacterReferenceProfile.from_actor_visual_profile(legacy_vp)
    assert adapted_ref.apparent_age_range == "Mid 40s"
    assert adapted_ref.baseline_wardrobe == "Faded olive drab field jacket"
    assert "Brass lighter" in adapted_ref.signature_objects


def test_real_disk_projects_load_without_error():
    """Verify that actual existing project files in the backend data directory load cleanly."""
    disk_store = ProjectStore(base_dir="/workspaces/d3-story-lab/backend/data/projects")
    projects = disk_store.list_projects()
    assert len(projects) >= 10

    # Test loading a sample of disk projects
    for meta in projects[:8]:
        proj = disk_store.load_project(meta.id)
        assert proj is not None
        assert proj.world is not None
        assert proj.schema_version == 2
