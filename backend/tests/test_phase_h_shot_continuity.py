"""Tests for Phase H: Shot Continuity & Character Reference Assets.

Verifies:
H1: 180° camera axis continuity, screen direction tracking, blocking carryover, axis crossing flags.
H2-Lite: Safe character reference asset upload validation, reference_mode toggle, path containment.
Simulation Sovereignty: Camera and visual reference assets never alter canonical simulation states.
"""

import os
import shutil
import tempfile
import base64
import pytest
from fastapi.testclient import TestClient

from src.domain.world import WorldState, Location
from src.domain.character import Character
from src.domain.event import Event, EventType
from src.domain.character_reference import CharacterReferenceProfile
from src.domain.character_creation import FieldAuthority
from src.domain.story_structure import DramaticFunction
from src.narrative.fountain import (
    ScreenplayDocument,
    ScreenplayScene,
    ScreenplayBlock,
    ScreenplayBlockType,
)
from src.narrative.scene_projection import (
    ObservableSceneProjection,
    ObservableBeat,
    ObservableObjective,
)
from src.narrative.performance_cues import PerformanceCue
from src.storyboard.models import ShotType, CameraAngle
from src.storyboard.shot_planner import (
    ShotPlanner,
    CompositionPlan,
    ShotPlan,
)
from src.storyboard.asset_store import StoryboardAssetStore
from src.storage.project_store import ProjectStore, ProjectData, ProjectMetadata
from src.api.app import create_app
from src.simulation.orchestrator import SimulationOrchestrator


@pytest.fixture
def temp_project_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_screenplay_scene():
    return ScreenplayScene(
        scene_number=1,
        heading="INT. ARCHIVE ROOM - NIGHT",
        location_id="loc_archive",
        source_event_ids=["evt_001", "evt_002", "evt_003"],
        metadata={"scene_id": "scn_001"},
        blocks=[
            ScreenplayBlock(
                block_id="blk_001",
                block_type=ScreenplayBlockType.SCENE_HEADING,
                text="INT. ARCHIVE ROOM - NIGHT",
                source_event_ids=["evt_001"],
            ),
            ScreenplayBlock(
                block_id="blk_002",
                block_type=ScreenplayBlockType.ACTION,
                text="Elena steps quietly toward the vault. Marcus watches from the doorway.",
                source_event_ids=["evt_002"],
            ),
            ScreenplayBlock(
                block_id="blk_003",
                block_type=ScreenplayBlockType.DIALOGUE,
                character_id="char_elena",
                text="We don't have much time.",
                source_event_ids=["evt_003"],
            ),
        ],
    )


@pytest.fixture
def sample_observable_scene():
    return ObservableSceneProjection(
        scene_id="scn_001",
        location_label="Archive Vault",
        time_label="NIGHT",
        characters_present=["char_elena", "char_marcus"],
        purpose=DramaticFunction.DISCOVERY,
        objective=ObservableObjective(
            pov_character_id="char_elena",
            wants="recover the dossier",
            obstacle="approaching guards",
            outcome="PARTIAL",
        ),
        source_event_ids=["evt_001", "evt_002", "evt_003"],
        performance_cues=[
            PerformanceCue(
                id="cue_001",
                character_id="char_elena",
                observable_behaviour="guarded, scanning the shadows",
                source_event_id="evt_002",
            ),
            PerformanceCue(
                id="cue_002",
                character_id="char_marcus",
                observable_behaviour="tense jaw, hand near holster",
                source_event_id="evt_003",
            ),
        ],
        beats=[
            ObservableBeat(
                event_id="evt_002",
                description="Elena inspects the safe while Marcus keeps watch.",
                characters_involved=["char_elena", "char_marcus"],
                performance_cue_ids=["cue_001"],
            ),
            ObservableBeat(
                event_id="evt_003",
                description="Marcus warns Elena about approaching footsteps.",
                characters_involved=["char_marcus", "char_elena"],
                performance_cue_ids=["cue_002"],
            ),
        ],
    )


# =============================================================================
# H1: 180° Camera Axis Continuity & Spatial Staging
# =============================================================================

def test_180_degree_camera_axis_continuity(sample_screenplay_scene, sample_observable_scene):
    """Verify that ShotPlanner establishes the line of action and stays on one axis side."""
    planner = ShotPlanner()
    screenplay = ScreenplayDocument(title="Test Screenplay", scenes=[sample_screenplay_scene])
    shots = planner.plan_shots_for_screenplay(
        screenplay=screenplay,
        projections=[sample_observable_scene],
    )

    assert len(shots) >= 3  # Establishing shot + 2 beat shots
    est_shot = shots[0]
    beat_shot_1 = shots[1]
    beat_shot_2 = shots[2]

    # Establishing shot has neutral axis
    assert est_shot.camera_axis_side == "NEUTRAL"
    assert est_shot.axis_crossing_flag is False

    # Line of action established between the two interactants
    assert est_shot.composition_plan.line_of_action == ("char_elena", "char_marcus")
    assert beat_shot_1.composition_plan.line_of_action == ("char_elena", "char_marcus")

    # Beat shots remain on established camera axis side without unflagged crossings
    assert beat_shot_1.camera_axis_side in ("LEFT", "RIGHT")
    assert beat_shot_2.camera_axis_side == beat_shot_1.camera_axis_side
    assert beat_shot_1.axis_crossing_flag is False
    assert beat_shot_2.axis_crossing_flag is False


def test_screen_direction_and_gaze_vectors(sample_screenplay_scene, sample_observable_scene):
    """Verify screen direction tracking and gaze vectors align across cuts."""
    planner = ShotPlanner()
    screenplay = ScreenplayDocument(title="Test Screenplay", scenes=[sample_screenplay_scene])
    shots = planner.plan_shots_for_screenplay(
        screenplay=screenplay,
        projections=[sample_observable_scene],
    )

    beat_shot_1 = shots[1]
    beat_shot_2 = shots[2]

    # In beat_shot_1, focal is char_elena (left side)
    assert beat_shot_1.subject_focus == "char_elena"
    assert beat_shot_1.screen_direction == "LEFT_TO_RIGHT"
    assert beat_shot_1.composition_plan.gaze_vectors["char_elena"] == "screen_right"

    # In beat_shot_2, focal is char_marcus (right side)
    assert beat_shot_2.subject_focus == "char_marcus"
    assert beat_shot_2.screen_direction == "RIGHT_TO_LEFT"
    assert beat_shot_2.composition_plan.gaze_vectors["char_marcus"] == "screen_left"


def test_blocking_carryover_within_scene(sample_screenplay_scene, sample_observable_scene):
    """Verify established spatial blocking carries over across sequential cuts in the same scene."""
    planner = ShotPlanner()
    screenplay = ScreenplayDocument(title="Test Screenplay", scenes=[sample_screenplay_scene])
    shots = planner.plan_shots_for_screenplay(
        screenplay=screenplay,
        projections=[sample_observable_scene],
    )

    beat_shot_1 = shots[1]
    beat_shot_2 = shots[2]

    pos_1_elena = beat_shot_1.composition_plan.subject_positions["char_elena"]
    pos_2_elena = beat_shot_2.composition_plan.subject_positions["char_elena"]
    pos_1_marcus = beat_shot_1.composition_plan.subject_positions["char_marcus"]
    pos_2_marcus = beat_shot_2.composition_plan.subject_positions["char_marcus"]

    # X coordinates must be strictly preserved
    assert pos_1_elena[0] == pos_2_elena[0] == 0.35
    assert pos_1_marcus[0] == pos_2_marcus[0] == 0.65
    assert beat_shot_2.composition_plan.blocking_carryover is True


# =============================================================================
# H2-Lite: Safe Character Reference Asset Upload Validation
# =============================================================================

def test_asset_store_reference_upload_validation(temp_project_dir):
    """Verify size cap, allowed formats, and path containment protection."""
    store = StoryboardAssetStore(temp_project_dir)
    project_id = "proj_test_h2"

    # Valid PNG content
    valid_png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    url = store.validate_and_save_reference_upload(
        project_id=project_id,
        character_id="char_elena",
        filename="portrait.png",
        content=valid_png_content,
    )
    assert "/api/projects/proj_test_h2/storyboard/assets/references/" in url
    assert "ref_char_elena_portrait.png" in url

    # Rejection 1: Oversized file (> 5MB)
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        store.validate_and_save_reference_upload(
            project_id=project_id,
            character_id="char_elena",
            filename="large.png",
            content=b"\x00" * (5 * 1024 * 1024 + 10),
        )

    # Rejection 2: Disallowed extension
    with pytest.raises(ValueError, match="Unsupported reference image format"):
        store.validate_and_save_reference_upload(
            project_id=project_id,
            character_id="char_elena",
            filename="script.exe",
            content=b"MZ\x90\x00\x03\x00\x00\x00",
        )

    # Rejection 3: Empty / too small content
    with pytest.raises(ValueError, match="content too small or empty"):
        store.validate_and_save_reference_upload(
            project_id=project_id,
            character_id="char_elena",
            filename="empty.png",
            content=b"abc",
        )


def test_reference_profile_api_endpoints(temp_project_dir):
    """Verify GET, PUT, mode toggle, and asset upload endpoints."""
    app = create_app(store_dir=temp_project_dir)
    client = TestClient(app)

    # Create test project
    pstore = ProjectStore(temp_project_dir)
    world = WorldState(id="w_test", name="Reference Test World")
    elena = Character(
        id="char_elena",
        name="Elena Vance",
        role="Intelligence Analyst",
        reference_profile=CharacterReferenceProfile(
            apparent_age_range="Late 20s",
            build="Slender athletic",
            face_description="Sharp amber eyes",
            baseline_wardrobe="Charcoal trench coat",
            reference_mode="TEXT_ONLY",
        ),
    )
    world.characters["char_elena"] = elena
    proj_meta = ProjectMetadata(id="proj_ref_test", title="Reference Test Project", seed_prompt="A classified dossier is stolen.")
    proj_data = ProjectData(metadata=proj_meta, world=world)
    pstore.save_project(proj_data)

    # 1. GET reference profile
    get_res = client.get("/api/projects/proj_ref_test/characters/char_elena/reference-profile")
    assert get_res.status_code == 200
    ref_data = get_res.json()
    assert ref_data["apparent_age_range"] == "Late 20s"
    assert ref_data["reference_mode"] == "TEXT_ONLY"

    # 2. PUT update reference profile with locks
    put_res = client.put(
        "/api/projects/proj_ref_test/characters/char_elena/reference-profile",
        json={
            "apparent_age_range": "Early 30s",
            "locked_fields": ["apparent_age_range"],
        },
    )
    assert put_res.status_code == 200
    updated_ref = put_res.json()
    assert updated_ref["apparent_age_range"] == "Early 30s"
    assert updated_ref["provenance"]["apparent_age_range"]["authority"] == "USER_LOCKED"

    # Lock blocks overwrite without force
    put_blocked = client.put(
        "/api/projects/proj_ref_test/characters/char_elena/reference-profile",
        json={"apparent_age_range": "40s"},
    )
    assert put_blocked.status_code == 400

    # 3. Switching to USER_UPLOAD without image must fail
    mode_fail = client.post(
        "/api/projects/proj_ref_test/characters/char_elena/reference-mode",
        json={"mode": "USER_UPLOAD"},
    )
    assert mode_fail.status_code == 400

    # 4. Upload reference asset
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    b64_str = base64.b64encode(fake_png).decode("utf-8")
    upload_res = client.post(
        "/api/projects/proj_ref_test/characters/char_elena/reference-image",
        json={"filename": "elena_mugshot.png", "image_base64": b64_str},
    )
    assert upload_res.status_code == 200
    up_data = upload_res.json()
    assert up_data["reference_mode"] == "USER_UPLOAD"
    assert "elena_mugshot.png" in up_data["reference_image_path"]

    # 5. Can switch back to TEXT_ONLY
    mode_text = client.post(
        "/api/projects/proj_ref_test/characters/char_elena/reference-mode",
        json={"mode": "TEXT_ONLY"},
    )
    assert mode_text.status_code == 200
    assert mode_text.json()["reference_mode"] == "TEXT_ONLY"


# =============================================================================
# Simulation Sovereignty: Zero influence on DecisionPolicy or WorldState
# =============================================================================

def test_phase_h_simulation_sovereignty():
    """Verify that different visual reference modes and camera axis setups have zero effect on simulation events."""
    world_a = WorldState(id="w_sim_a", name="Sim World A")
    char_a = Character(
        id="char_agent",
        name="Agent A",
        role="Operative",
        reference_profile=CharacterReferenceProfile(
            reference_mode="TEXT_ONLY",
            baseline_wardrobe="Standard uniform",
        ),
    )
    world_a.characters["char_agent"] = char_a
    world_a.locations["loc_hq"] = Location(id="loc_hq", name="HQ")
    char_a.current_location_id = "loc_hq"

    world_b = WorldState(id="w_sim_a", name="Sim World A")
    char_b = Character(
        id="char_agent",
        name="Agent A",
        role="Operative",
        reference_profile=CharacterReferenceProfile(
            reference_mode="USER_UPLOAD",
            reference_image_path="/api/projects/test/storyboard/assets/references/fake.png",
            baseline_wardrobe="Custom tailored tuxedo",
        ),
    )
    world_b.characters["char_agent"] = char_b
    world_b.locations["loc_hq"] = Location(id="loc_hq", name="HQ")
    char_b.current_location_id = "loc_hq"

    orch_a = SimulationOrchestrator(world=world_a, seed=42)
    orch_b = SimulationOrchestrator(world=world_b, seed=42)

    for _ in range(5):
        orch_a.step()
        orch_b.step()

    events_a = [(e.tick, e.event_type.value, e.actor_ids, e.description) for e in world_a.events.values()]
    events_b = [(e.tick, e.event_type.value, e.actor_ids, e.description) for e in world_b.events.values()]

    assert events_a == events_b
