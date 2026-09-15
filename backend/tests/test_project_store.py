"""Tests for ProjectStore persistence."""

import tempfile
import json
import concurrent.futures
from unittest.mock import patch
from pathlib import Path
import pytest

from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.event import Event, EventType
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storage.project_store import (
    ProjectStore,
    ProjectData,
    ProjectMetadata,
    ProjectStorageError,
    ProjectCorruptedError,
)


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

    def test_concurrent_saves_same_project_no_corruption(self):
        """Regression test: Concurrent saves to the SAME project must not race or corrupt JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            base_meta = ProjectMetadata(id="proj_shared", title="Shared Project", seed_prompt="Concurrent seed")
            base_world = WorldState(id="w_shared", name="Shared World")
            init_proj = ProjectData(metadata=base_meta, world=base_world)
            store.save_project(init_proj)

            # Prepare two different project payloads (one large, one small)
            proj_large = ProjectData(
                metadata=base_meta,
                world=base_world,
                fountain_text="EXT. LOCATION - NIGHT\n" + ("ACTION LINE GOES HERE. " * 3000),
            )
            proj_small = ProjectData(
                metadata=base_meta,
                world=base_world,
                fountain_text="INT. OFFICE - DAY\nShort.",
            )

            errors: list[Exception] = []

            def worker(index: int):
                try:
                    payload = proj_large if (index % 2 == 0) else proj_small
                    store.save_project(payload)
                except Exception as exc:
                    errors.append(exc)

            # Launch 40 concurrent saves to the same project
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i) for i in range(40)]
                concurrent.futures.wait(futures)

            # Assert zero exceptions occurred (no FileNotFoundError or OS errors)
            assert len(errors) == 0, f"Encountered save errors: {errors}"

            # Verify the project file on disk is valid JSON and loads cleanly
            target_file = Path(tmpdir) / "proj_shared.json"
            assert target_file.exists()
            with open(target_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            assert isinstance(raw, dict)

            loaded = store.load_project("proj_shared")
            assert loaded is not None
            assert loaded.metadata.id == "proj_shared"
            assert loaded.fountain_text in (proj_large.fountain_text, proj_small.fountain_text)

            # Verify no lingering .tmp files exist
            tmp_files = list(Path(tmpdir).glob("*.tmp"))
            assert len(tmp_files) == 0, f"Found lingering temporary files: {tmp_files}"

    def test_concurrent_saves_different_projects_succeed(self):
        """Verify concurrent saves to DIFFERENT projects succeed without blocking or interference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            def worker(index: int) -> str:
                meta = ProjectMetadata(id=f"proj_{index}", title=f"Project {index}", seed_prompt=f"Seed {index}")
                world = WorldState(id=f"w_{index}", name=f"World {index}")
                p = ProjectData(metadata=meta, world=world)
                return store.save_project(p)

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(worker, i) for i in range(20)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            assert len(results) == 20
            for i in range(20):
                loaded = store.load_project(f"proj_{i}")
                assert loaded is not None
                assert loaded.metadata.id == f"proj_{i}"

    def test_repeated_save_and_load_remains_valid(self):
        """Verify repeated save and load cycle maintains valid JSON and correct state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            meta = ProjectMetadata(id="proj_repeat", title="Repeat Project", seed_prompt="Repeat test")
            world = WorldState(id="w_repeat", name="Repeat World")
            project = ProjectData(metadata=meta, world=world)
            store.save_project(project)

            for tick in range(1, 25):
                loaded = store.load_project("proj_repeat")
                assert loaded is not None
                assert loaded.world.current_tick == tick - 1

                loaded.world.current_tick = tick
                store.save_project(loaded)

            final_loaded = store.load_project("proj_repeat")
            assert final_loaded is not None
            assert final_loaded.world.current_tick == 24
            assert final_loaded.metadata.current_tick == 24

    def test_atomic_replacement_leaves_no_partial_file_on_failure(self):
        """Verify atomic replacement cleans up temporary files when an error occurs during dump."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            meta = ProjectMetadata(id="proj_atomic", title="Atomic Test", seed_prompt="Seed")
            world = WorldState(id="w_atomic", name="World")
            project = ProjectData(metadata=meta, world=world)

            # Initial successful save
            store.save_project(project)
            initial_content = (Path(tmpdir) / "proj_atomic.json").read_text(encoding="utf-8")

            # Simulate failure during json.dump
            with patch("json.dump", side_effect=IOError("Simulated write error")):
                with pytest.raises(IOError, match="Simulated write error"):
                    store.save_project(project)

            # Ensure no stray .tmp files remain
            tmp_files = list(Path(tmpdir).glob("*.tmp"))
            assert len(tmp_files) == 0, f"Found stray .tmp files: {tmp_files}"

            # Ensure existing valid file remained completely untouched
            assert (Path(tmpdir) / "proj_atomic.json").read_text(encoding="utf-8") == initial_content

    def test_corrupted_json_raises_controlled_persistence_error(self):
        """Verify corrupted JSON raises ProjectCorruptedError instead of unhandled crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            # 1. Truncated JSON
            truncated_path = Path(tmpdir) / "proj_truncated.json"
            truncated_path.write_text('{"schema_version": 2, "metadata": {', encoding="utf-8")
            with pytest.raises(ProjectCorruptedError) as exc_info:
                store.load_project("proj_truncated")
            assert "corrupted or malformed JSON" in str(exc_info.value)
            assert isinstance(exc_info.value, ProjectStorageError)

            # 2. Extra trailing data JSON (the exact defect observed)
            extra_path = Path(tmpdir) / "proj_extra.json"
            extra_path.write_text('{"schema_version": 2, "metadata": {"id": "x", "title": "t", "seed_prompt": "s"}, "world": {"id": "w", "name": "wn"}}} trailing', encoding="utf-8")
            with pytest.raises(ProjectCorruptedError) as exc_info2:
                store.load_project("proj_extra")
            assert "corrupted or malformed JSON" in str(exc_info2.value)

            # 3. Invalid schema data (valid JSON but invalid structure)
            invalid_schema_path = Path(tmpdir) / "proj_bad_schema.json"
            invalid_schema_path.write_text('{"schema_version": 2, "metadata": "NOT_A_DICT", "world": 123}', encoding="utf-8")
            with pytest.raises(ProjectCorruptedError) as exc_info3:
                store.load_project("proj_bad_schema")
            assert "failed validation" in str(exc_info3.value)

    def test_legacy_migration_via_store(self):
        """Verify legacy project migration initializes defaults and saves schema_version 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ProjectStore(base_dir=tmpdir)

            legacy = {
                "metadata": {
                    "id": "proj_legacy",
                    "title": "Legacy Project",
                    "seed_prompt": "Old seed",
                },
                "world": {
                    "id": "w_legacy",
                    "name": "Legacy World",
                }
            }
            legacy_file = Path(tmpdir) / "proj_legacy.json"
            legacy_file.write_text(json.dumps(legacy), encoding="utf-8")

            loaded = store.load_project("proj_legacy")
            assert loaded is not None
            assert loaded.schema_version == 2
            assert loaded.metadata.schema_version == 2
            assert loaded.metadata.input_type == "beginning"
            assert loaded.world.propositions == {}
            assert loaded.world.facts == {}
