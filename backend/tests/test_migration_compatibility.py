"""Tests for project schema versioning, backward compatibility, and legacy migration."""

import json
from pathlib import Path
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata


def test_legacy_project_migration_and_defaults(tmp_path):
    """Verify that a legacy JSON project without schema_version loads cleanly with v2 defaults."""
    legacy_json = {
        "metadata": {
            "id": "legacy_proj_001",
            "title": "Legacy Noir Story",
            "seed_prompt": "An operative meets a courier at the docks.",
            "created_at": "2026-09-01T12:00:00+00:00",
            "updated_at": "2026-09-01T12:00:00+00:00",
            "current_tick": 4,
            "total_events": 6,
            "total_scenes": 2,
        },
        "world": {
            "id": "legacy_proj_001",
            "name": "Legacy Noir World",
            "current_tick": 4,
            "locations": {
                "loc_dock": {
                    "id": "loc_dock",
                    "name": "Docks",
                    "description": "Rain-slicked shipping pier",
                    "connected_locations": [],
                }
            },
            "characters": {
                "char_spy": {
                    "id": "char_spy",
                    "name": "Agent Vance",
                    "role": "Operative",
                    "location_id": "loc_dock",
                }
            },
            "objects": {},
            "goals": {},
            "beliefs": {},
            "secrets": {},
            "relationships": {},
            "memories": {},
            "events": {},
            "facts": {},
        }
    }

    proj_file = tmp_path / "legacy_proj_001.json"
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(legacy_json, f)

    store = ProjectStore(base_dir=tmp_path)
    loaded = store.load_project("legacy_proj_001")

    assert loaded is not None
    assert loaded.schema_version == 2
    assert loaded.metadata.schema_version == 2
    assert loaded.metadata.input_type == "beginning"
    assert loaded.metadata.story_structure is None
    assert loaded.story_blueprint is None
    assert loaded.causal_summary is None
    assert loaded.character_arcs is None
    assert loaded.scenes is None

    # Test roundtrip saving with v2 fields
    saved_id = store.save_project(loaded)
    reloaded = store.load_project(saved_id)
    assert reloaded is not None
    assert reloaded.schema_version == 2
    assert reloaded.metadata.schema_version == 2


def test_all_existing_disk_projects_load_and_migrate():
    """Verify that all pre-existing projects on disk load without validation errors."""
    disk_store = ProjectStore(base_dir="/workspaces/d3-story-lab/backend/data/projects")
    projects = disk_store.list_projects()
    assert len(projects) >= 15

    for meta in projects:
        loaded = disk_store.load_project(meta.id)
        assert loaded is not None, f"Failed to load project {meta.id}"
        assert loaded.schema_version == 2
        assert loaded.metadata.schema_version == 2
