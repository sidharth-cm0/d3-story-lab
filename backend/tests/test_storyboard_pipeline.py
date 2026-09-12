"""Comprehensive unit and integration tests for the Upgraded Comic Storyboard Pipeline."""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.world import WorldState, Location, WorldObject
from src.domain.character import Character
from src.domain.continuity import ActorVisualProfile, ObjectVisualProfile, LocationVisualProfile
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.storyboard.models import (
    ShotType,
    CameraAngle,
    ShotPurpose,
    PageLayoutTemplate,
    StoryboardPanel,
    StoryboardImageStatus,
)
from src.storyboard.visual_bible import VisualBible, StoryboardStyleProfile
from src.storyboard.compiler import StoryboardPromptCompiler, ContinuityValidator
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.image_provider import (
    FallbackComicSvgProvider,
    MockStoryboardImageProvider,
    CloudImagenStoryboardProvider,
)
from src.storyboard.planner import StoryboardPlanner


@pytest.fixture
def sample_world() -> WorldState:
    world = WorldState(id="world_noir", name="Metropolis Noir")
    loc = Location(
        id="loc_penthouse",
        name="Apex Penthouse",
        description="A rain-streaked luxury penthouse overlooking neon skyscrapers",
        visual_profile=LocationVisualProfile(
            location_id="loc_penthouse",
            name="Apex Penthouse",
            environment_type="High-rise executive penthouse",
            lighting="Moody chiaroscuro, cold rain reflections",
            layout="Spacious open room, panoramic glass wall",
            palette="Charcoal slate, cold steel blue, amber highlights",
        ),
    )
    world.locations[loc.id] = loc

    char1 = Character(
        id="char_elena",
        name="Elena Cross",
        role="Corporate Detective",
        location_id=loc.id,
        visual_profile=ActorVisualProfile(
            character_id="char_elena",
            name="Elena Cross",
            age="Early 30s",
            face_traits="Sharp jawline, piercing green eyes",
            hairstyle="Sleek dark bob",
            clothing="Charcoal tailored trench coat and silk tie",
            signature_items=["Silver pocket watch"],
        ),
    )
    world.characters[char1.id] = char1

    obj = WorldObject(
        id="obj_dossier",
        name="Black Ledger",
        description="Classified ledger bound in black leather",
        location_id=loc.id,
        visual_profile=ObjectVisualProfile(
            object_id="obj_dossier",
            name="Black Ledger",
            material="Weathered black leather with brass clasp",
            size="Medium folio",
            color="Pitch black",
            condition="Worn corners",
            unique_markers="Wax seal imprint",
        ),
    )
    world.objects[obj.id] = obj

    return world


@pytest.fixture
def sample_screenplay() -> ScreenplayDocument:
    return ScreenplayDocument(
        title="MIDNIGHT INFILTRATION",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_penthouse",
                heading="INT. APEX PENTHOUSE - NIGHT",
                source_event_ids=["evt_01", "evt_02"],
                blocks=[
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Elena picks the heavy lock. The tumbler clicks open.",
                        source_event_ids=["evt_01"],
                        character_id="char_elena",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="She examines the Black Ledger inside the wall safe.",
                        source_event_ids=["evt_01"],
                        character_id="char_elena",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.CHARACTER,
                        text="ELENA CROSS",
                        source_event_ids=["evt_02"],
                        character_id="char_elena",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="They've been altering the transaction logs for months.",
                        source_event_ids=["evt_02"],
                        character_id="char_elena",
                    ),
                ],
            )
        ],
    )


def test_visual_bible_derivation(sample_world: WorldState):
    bible = VisualBible.from_world(sample_world)
    assert "char_elena" in bible.characters
    assert bible.characters["char_elena"].name == "Elena Cross"
    assert "Charcoal tailored trench coat" in bible.characters["char_elena"].clothing
    assert "obj_dossier" in bible.objects
    assert "Black Ledger" in bible.objects["obj_dossier"].name
    assert "loc_penthouse" in bible.locations
    assert "Apex Penthouse" in bible.locations["loc_penthouse"].name


def test_prompt_compiler_structured_output(sample_world: WorldState, sample_screenplay: ScreenplayDocument):
    bible = VisualBible.from_world(sample_world)
    planner = StoryboardPlanner()
    plan = planner.plan_shots(sample_screenplay, sample_world, bible=bible)

    compiler = StoryboardPromptCompiler()
    for p in plan.panels:
        prompt = compiler.compile_panel_prompt(p, bible)
        assert len(prompt) > 80
        assert "speech" in prompt.lower()
        # Framing check
        assert any(st.value.replace("_", " ").title() in prompt for st in ShotType)


def test_continuity_validator(sample_world: WorldState, sample_screenplay: ScreenplayDocument):
    bible = VisualBible.from_world(sample_world)
    planner = StoryboardPlanner()
    plan = planner.plan_shots(sample_screenplay, sample_world, bible=bible)

    report = ContinuityValidator.validate_shot_plan(plan.panels, bible)
    assert report.is_valid is True
    assert report.score >= 0.7
    assert report.total_panels == len(plan.panels)


def test_asset_store_path_traversal_defense(tmp_path: Path):
    store = StoryboardAssetStore(base_dir=tmp_path)

    # Valid write and read
    url = store.save_asset("proj_100", "panels", "shot_01_v1.svg", "<svg></svg>")
    assert url == "/api/projects/proj_100/storyboard/assets/panels/shot_01_v1.svg"

    content, mime = store.load_asset("proj_100", "panels", "shot_01_v1.svg")
    assert content == b"<svg></svg>"
    assert mime == "image/svg+xml"

    # Malicious path traversal attempts
    with pytest.raises(ValueError):
        store.save_asset("../evil_proj", "panels", "test.png", b"")

    with pytest.raises(ValueError):
        store.save_asset("proj_100", "unauthorized_cat", "test.png", b"")

    with pytest.raises(ValueError):
        store.save_asset("proj_100", "panels", "../../etc/passwd.png", b"")

    with pytest.raises(ValueError):
        store.load_asset("proj_100", "panels", "../secret.png")


def test_image_provider_and_versioning(tmp_path: Path, sample_world: WorldState, sample_screenplay: ScreenplayDocument):
    asset_store = StoryboardAssetStore(base_dir=tmp_path)
    bible = VisualBible.from_world(sample_world)
    planner = StoryboardPlanner()
    plan = planner.plan_shots(sample_screenplay, sample_world, bible=bible, project_id="proj_test")

    fallback_provider = FallbackComicSvgProvider(asset_store=asset_store)
    panel = plan.panels[0]

    # Generate version 1
    res_v1 = fallback_provider.generate_panel(panel, bible=bible, version=1)
    assert res_v1.version == 1
    assert res_v1.mode == "fallback_comic"
    assert "<svg" in res_v1.svg_content

    # Generate version 2
    res_v2 = fallback_provider.generate_panel(panel, bible=bible, version=2)
    assert res_v2.version == 2
    assert "shot_01" in res_v2.image_url or "pnl_" in res_v2.image_url


def test_storyboard_api_flow(tmp_path: Path):
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    # 1. Create project
    create_resp = client.post(
        "/api/projects",
        json={
            "seed_prompt": "A detective discovers a hidden ledger in a locked penthouse suite.",
            "title": "Penthouse Ledger",
            "target_duration_minutes": 15,
        },
    )
    assert create_resp.status_code == 200
    proj_id = create_resp.json()["id"]

    # 2. Step simulation
    step_resp = client.post(f"/api/projects/{proj_id}/step", json={"ticks": 2})
    assert step_resp.status_code == 200

    # 3. Generate screenplay
    screenplay_resp = client.post(f"/api/projects/{proj_id}/generate-screenplay")
    assert screenplay_resp.status_code == 200
    assert screenplay_resp.json()["total_panels"] > 0

    # 4. Get Visual Bible
    bible_resp = client.get(f"/api/projects/{proj_id}/visual-bible")
    assert bible_resp.status_code == 200
    bible_data = bible_resp.json()
    assert "characters" in bible_data
    assert "locations" in bible_data

    # 5. Plan Storyboard with density options
    plan_resp = client.post(
        f"/api/projects/{proj_id}/storyboard/plan",
        json={"density_mode": "detailed", "panels_per_page": 4},
    )
    assert plan_resp.status_code == 200
    shot_plan = plan_resp.json()["shot_plan"]
    assert shot_plan["density_mode"] == "detailed"
    assert len(shot_plan["panels"]) > 0

    panel_id = shot_plan["panels"][0]["panel_id"]

    # 6. Regenerate single panel (version 2)
    regen_resp = client.post(
        f"/api/projects/{proj_id}/storyboard/panels/{panel_id}/regenerate",
        json={"provider": "fallback"},
    )
    assert regen_resp.status_code == 200
    regen_data = regen_resp.json()
    assert regen_data["version"] >= 2
    assert len(regen_data["panel"]["versions"]) >= 2

    # 7. Select version 1 back
    select_resp = client.post(
        f"/api/projects/{proj_id}/storyboard/panels/{panel_id}/select-version",
        json={"version": 1},
    )
    assert select_resp.status_code == 200
    assert select_resp.json()["selected_version"] == 1

    # 8. Test secure asset serving
    asset_url = regen_data["panel"]["versions"][0]["image_url"]
    if asset_url.startswith("/api/projects/"):
        get_asset_resp = client.get(asset_url)
        assert get_asset_resp.status_code == 200

    # 9. Path traversal attempt via API
    evil_resp = client.get(f"/api/projects/{proj_id}/storyboard/assets/panels/..%2Fsecret.txt")
    assert evil_resp.status_code in (403, 404)
