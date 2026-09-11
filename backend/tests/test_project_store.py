"""Tests for ProjectStore persistence."""

import tempfile
from pathlib import Path
from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.event import Event, EventType
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata


class TestProjectStore:
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            world = WorldState(id="world_proj1", name="Project 1 World")
            loc = Location(id="loc_1", name="Gallery", description="An art gallery")
            world.locations[loc.id] = loc
            char = Character(id="char_1", name="Elena", role="Curator", location_id="loc_1")
            world.characters[char.id] = char
            evt = Event(id="evt_1", tick=1, event_type=EventType.OTHER, description="Elena adjusts a painting.")
            world.events[evt.id] = evt

            screenplay = ScreenplayDocument(
                title="THE CURATOR",
                scenes=[
                    ScreenplayScene(
                        scene_number=1,
                        location_id="loc_1",
                        heading="INT. GALLERY - DAY",
                        blocks=[
                            ScreenplayBlock(
                                block_type=ScreenplayBlockType.ACTION,
                                text="Elena adjusts a painting.",
                                source_event_ids=["evt_1"],
                            )
                        ],
                        source_event_ids=["evt_1"],
                    )
                ]
            )

            meta = ProjectMetadata(
                id="proj_alpha",
                title="The Curator",
                seed_prompt="An art curator discovers a hidden forgery.",
            )

            project = ProjectData(
                metadata=meta,
                world=world,
                screenplay=screenplay,
            )

            # Save
            pid = store.save_project(project)
            assert pid == "proj_alpha"

            # Verify on disk
            loaded = store.load_project("proj_alpha")
            assert loaded is not None
            assert loaded.metadata.title == "The Curator"
            assert loaded.metadata.total_events == 1
            assert loaded.metadata.total_scenes == 1
            assert "loc_1" in loaded.world.locations
            assert loaded.world.locations["loc_1"].name == "Gallery"
            assert loaded.world.characters["char_1"].name == "Elena"
            assert loaded.fountain_text is not None
            assert "INT. GALLERY - DAY" in loaded.fountain_text

    def test_list_and_delete_projects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            for i in range(3):
                p = ProjectData(
                    metadata=ProjectMetadata(id=f"proj_{i}", title=f"Project {i}", seed_prompt=f"Seed {i}"),
                    world=WorldState(id=f"w_{i}", name=f"World {i}"),
                )
                store.save_project(p)

            projects = store.list_projects()
            assert len(projects) == 3

            # Delete proj_1
            success = store.delete_project("proj_1")
            assert success is True
            assert store.load_project("proj_1") is None
            assert len(store.list_projects()) == 2
