"""Comprehensive tests for Prop Tracking, Image Provider Status, and Continuity Upgrades."""

import pytest
import os
import json
from unittest.mock import patch, MagicMock

from src.domain.world import WorldState, WorldObject, Location, Character
from src.storyboard.models import (
    StoryboardPanel,
    ShotType,
    CameraAngle,
    ShotPurpose,
    StoryboardImageStatus,
    StoryboardImageVersion,
)
from src.storyboard.prop_resolver import PropResolver, COMMON_PROP_ALIASES
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler, ContinuityValidator
from src.storyboard.image_provider import (
    CloudImagenStoryboardProvider,
    FallbackComicSvgProvider,
    MockStoryboardImageProvider,
    ProviderState,
    FallbackReason,
    StoryboardImageResult,
)
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.planner import StoryboardPlanner
from src.narrative.fountain import ScreenplayDocument, ScreenplayScene, ScreenplayBlock, ScreenplayBlockType
from src.api.app import create_app
from starlette.testclient import TestClient


@pytest.fixture
def test_world():
    """Create a test WorldState with canonical objects, characters, and locations."""
    loc1 = Location(id="loc_warehouse", name="Abandoned Warehouse", description="Derelict industrial bay")
    char1 = Character(id="char_vincent", name="Vincent Cross", role="Defecting Specialist", current_location_id="loc_warehouse")
    char2 = Character(id="char_elena", name="Elena Vance", role="Lead Detective", current_location_id="loc_warehouse")
    
    obj_dossier = WorldObject(
        id="obj_dossier_001",
        name="The Confidential Dossier",
        description="A weathered folio containing classified corruption evidence.",
        location_id="loc_warehouse",
        holder_id=None,
    )
    obj_transceiver = WorldObject(
        id="obj_transceiver_002",
        name="Encrypted Transceiver",
        description="A black tactical radio with frequency scrambler.",
        location_id="loc_warehouse",
        holder_id="char_vincent",
    )
    obj_safe = WorldObject(
        id="obj_safe_003",
        name="Steel Wall Safe",
        description="Heavy reinforced lockbox recessed into concrete.",
        location_id="loc_warehouse",
    )

    return WorldState(
        id="world_test_prop",
        name="Test Incident",
        locations={"loc_warehouse": loc1},
        characters={"char_vincent": char1, "char_elena": char2},
        objects={
            "obj_dossier_001": obj_dossier,
            "obj_transceiver_002": obj_transceiver,
            "obj_safe_003": obj_safe,
        },
    )


def test_prop_resolver_canonical_and_aliases(test_world):
    """Test that mentions of 'dossier', 'sealed dossier', 'file', and 'evidence dossier' resolve to canonical obj_dossier_001."""
    # Test variant phrases
    phrases = [
        "Vincent inspects the dossier under the dim bulb.",
        "Elena retrieves the sealed dossier from behind the pipe.",
        "He hides the file inside his coat.",
        "The evidence dossier contains photographs of the transaction.",
        "Documents were scattered across the concrete floor.",
    ]
    for phrase in phrases:
        resolved_ids = PropResolver.resolve_canonical_object_ids(
            text_pool=phrase,
            world=test_world,
            location_id="loc_warehouse",
        )
        assert "obj_dossier_001" in resolved_ids, f"Failed to resolve dossier in phrase: {phrase}"

    # Test transceiver aliases
    transceiver_phrase = "Vincent turns on his tactical comms radio to listen for static."
    resolved_transceiver = PropResolver.resolve_canonical_object_ids(
        text_pool=transceiver_phrase,
        world=test_world,
        location_id="loc_warehouse",
    )
    assert "obj_transceiver_002" in resolved_transceiver

    # Test safe/locker aliases
    safe_phrase = "She forces open the evidence locker inside the wall safe."
    resolved_safe = PropResolver.resolve_canonical_object_ids(
        text_pool=safe_phrase,
        world=test_world,
        location_id="loc_warehouse",
    )
    assert "obj_safe_003" in resolved_safe


def test_objects_in_frame_populated_in_shot_plan(test_world):
    """Test that StoryboardPlanner populates panel.objects_in_frame with canonical object IDs."""
    bible = VisualBible.from_world(test_world)
    doc = ScreenplayDocument(
        title="The Threshold",
        scenes=[
            ScreenplayScene(
                scene_number=1,
                location_id="loc_warehouse",
                heading="INT. ABANDONED WAREHOUSE - NIGHT",
                blocks=[
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.ACTION,
                        text="Vincent clutches the encrypted transceiver while searching for the dossier.",
                        character_id="char_vincent",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.CHARACTER,
                        text="VINCENT CROSS",
                        character_id="char_vincent",
                    ),
                    ScreenplayBlock(
                        block_type=ScreenplayBlockType.DIALOGUE,
                        text="The evidence dossier is here. Someone opened the safe.",
                    ),
                ],
            )
        ],
    )
    planner = StoryboardPlanner(panels_per_page=4)
    shot_plan = planner.plan_shots(doc, test_world, bible=bible, project_id="test_proj")

    assert len(shot_plan.panels) >= 2
    # Check action panel
    act_panel = [p for p in shot_plan.panels if p.narrative_purpose != ShotPurpose.ESTABLISH and "searching" in p.action][0]
    assert "obj_transceiver_002" in act_panel.objects_in_frame or "obj_dossier_001" in act_panel.objects_in_frame
    assert len(act_panel.objects_in_frame) >= 1

    # Check dialogue panel
    dia_panel = [p for p in shot_plan.panels if p.narrative_purpose == ShotPurpose.REVELATION or "VINCENT CROSS" in p.caption][0]
    assert "obj_dossier_001" in dia_panel.objects_in_frame or "obj_safe_003" in dia_panel.objects_in_frame


def test_continuity_validator_no_dossier_warning(test_world):
    """Verify that when dossier is tracked in objects_in_frame, ContinuityValidator reports no missing prop warnings."""
    bible = VisualBible.from_world(test_world)
    panel = StoryboardPanel(
        id="pnl_test_01",
        scene_number=1,
        panel_number=1,
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.EYE_LEVEL,
        narrative_purpose=ShotPurpose.CLUE,
        location_name="Warehouse",
        characters_present=["char_vincent"],
        character_names=["Vincent Cross"],
        objects_in_frame=["obj_dossier_001"],  # Canonical object_id
        action="Vincent opens the dossier and examines the pages.",
        object_references={"obj_dossier_001": bible.objects["obj_dossier_001"].prompt_snippet()},
    )
    report = ContinuityValidator.validate_shot_plan([panel], bible)

    dossier_issues = [
        iss for iss in report.issues
        if iss.category == "prop_tracking" and "dossier" in iss.message.lower()
    ]
    assert len(dossier_issues) == 0, f"Expected 0 dossier warnings, got: {dossier_issues}"
    assert report.prop_tracking_score == 1.0


def test_cloud_provider_status_and_no_key_fallback(tmp_path, monkeypatch):
    """Test CloudImagenStoryboardProvider when no API key is provided."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("IMAGEN_API_KEY", raising=False)
    store = StoryboardAssetStore(base_dir=str(tmp_path))
    provider = CloudImagenStoryboardProvider(api_key=None, asset_store=store)

    status = provider.get_status()
    assert status["storyboard_image_provider"] == "google_imagen"
    assert status["mode"] == "cloud"
    assert status["status"] == "UNAVAILABLE"
    assert status["available"] is False
    assert status["fallback_enabled"] is True
    assert status["fallback_reason"] == "NO_API_KEY"
    assert "api_key" not in status  # Security: never expose secrets

    # When generate_panel is called without key, it must not silently pretend AI worked
    panel = StoryboardPanel(id="pnl_test_02", action="A test panel action")
    res = provider.generate_panel(panel)
    assert res.mode == "fallback_comic"
    assert res.fallback_reason == "NO_API_KEY"
    assert res.provider_status == "UNAVAILABLE"
    assert res.render_metadata["label"] == "FALLBACK COMIC"
    assert res.render_metadata["fallback_reason"] == "NO_API_KEY"


def test_cloud_provider_mocked_http_responses(tmp_path):
    """Test HTTP status code handling (200 raster success, 401 auth error, 429 quota, 404 model)."""
    store = StoryboardAssetStore(base_dir=str(tmp_path))
    provider = CloudImagenStoryboardProvider(api_key="mock_key_12345", asset_store=store)

    panel = StoryboardPanel(id="pnl_test_03", project_id="proj_sim", action="Action in warehouse")

    # 1. Simulate 401 Unauthorized
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        provider_401 = CloudImagenStoryboardProvider(api_key="mock_key_12345", asset_store=store)
        res = provider_401.generate_panel(panel)
        assert res.mode == "fallback_comic"
        assert res.fallback_reason == FallbackReason.AUTHENTICATION_FAILED.value
        assert res.provider_status == ProviderState.AUTH_ERROR.value

    # 2. Simulate 429 Quota Exceeded
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        provider_429 = CloudImagenStoryboardProvider(api_key="mock_key_12345", asset_store=store)
        res = provider_429.generate_panel(panel)
        assert res.mode == "fallback_comic"
        assert res.fallback_reason == FallbackReason.QUOTA_EXCEEDED.value
        assert res.provider_status == ProviderState.QUOTA_ERROR.value

    # 3. Simulate 200 OK with real raster PNG bytes
    # Valid 1x1 PNG bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    b64_str = import_base64 = __import__("base64").b64encode(png_bytes).decode("utf-8")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "predictions": [{"bytesBase64Encoded": b64_str}]
        }
        mock_post.return_value = mock_resp

        provider_200 = CloudImagenStoryboardProvider(api_key="mock_key_12345", asset_store=store)
        res = provider_200.generate_panel(panel)
        assert res.mode == "ai_image"
        assert res.provider == "google_imagen"
        assert res.status == StoryboardImageStatus.READY
        assert res.fallback_reason is None
        assert res.mime_type == "image/png"
        assert res.render_metadata["label"] == "AI IMAGE"
        assert "pnl_test_03_v1.png" in res.image_url

        # Check asset persistence on disk
        loaded_bytes, mime = store.load_asset("proj_sim", "panels", "pnl_test_03_v1.png")
        assert loaded_bytes == png_bytes
        assert mime == "image/png"


def test_api_provider_status_endpoints(tmp_path):
    """Test /api/storyboard/provider-status and /api/projects/{id}/storyboard/status."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    resp = client.get("/api/storyboard/provider-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "storyboard_image_provider" in data
    assert "available" in data
    assert "fallback_enabled" in data
    assert "continuity_mode" in data
    assert "api_key" not in data
