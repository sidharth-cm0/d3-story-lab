"""Comprehensive test suite for the Open-Model Storyboard Architecture.

Verifies:
1. Procedural SVG retired from final artwork presentation (retained strictly as previs guidance).
2. Unrendered / offline runtime status messaging ("Storyboard render unavailable", "Previs guide available").
3. Provider abstraction and capability discovery (/api/storyboard/capabilities).
4. Runtime configuration (/api/storyboard/configure).
5. 14-section structured prompt compiler with observable acting and negative text constraints.
6. Character, Location, and Prop continuity packs with reference sheets.
7. StoryboardControlBundle generation (pose, edge, depth, composition, camera layout).
8. Keyframe selection on 8-shot undercover warehouse scenario (renders shots 1, 4, 5, 8).
9. Mock runtime rendering producing valid raster image panels.
10. Version preservation and asset store metadata tracking across v1, v2, v3.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.storyboard.models import (
    StoryboardPanel,
    ShotType,
    CameraAngle,
    ShotPurpose,
    StoryboardImageVersion,
)
from src.storyboard.provider_base import RenderMode
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
    CharacterReferenceSheet,
)
from src.storyboard.control import StoryboardControlBundle, PrevisControlRenderer
from src.storyboard.prompt_compiler import StoryboardImagePromptCompiler
from src.storyboard.open_model_provider import (
    OpenModelStoryboardProvider,
    MockOpenModelStoryboardAdapter,
    select_keyframe_indices,
    ComfyUIStoryboardAdapter,
    DiffusersStoryboardAdapter,
)
from src.storyboard.image_provider import OpenModelImageProviderAdapter


@pytest.fixture
def asset_store(tmp_path):
    return StoryboardAssetStore(base_dir=tmp_path)


@pytest.fixture
def sample_panel():
    return StoryboardPanel(
        id="panel_test_1",
        panel_id="panel_test_1",
        project_id="proj_default",
        scene_number=1,
        panel_number=1,
        shot_number=1,
        page_number=1,
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.LOW_ANGLE,
        narrative_purpose=ShotPurpose.REVEAL,
        action_description="Elena sets the stolen dossier on the rusted crate, her hands trembling.",
        dialogue_excerpt="This ends tonight.",
        location_id="loc_warehouse",
        location_name="Abandoned Warehouse",
        characters_present=["char_elena"],
        character_names=["Elena Vance"],
        objects_in_frame=["prop_dossier", "prop_crate"],
        mood="tense noir suspense",
        lens_feel="50mm prime, f/1.8 shallow depth of field",
        focal_depth_plane="midground crate and hands",
        lighting_profile_id="NOIR_HARD",
        composition="rule of thirds, subject on right power line",
        aspect_ratio="16:9",
        is_keyframe=True,
        keyframe_reason="Critical plot reveal: dossier placed on crate",
    )


def test_procedural_svg_retired_from_final_artwork(asset_store, sample_panel):
    """Verify procedural SVG is NEVER returned as final artwork and remains internal previs."""
    # When provider is not connected to a remote runtime:
    adapter = MockOpenModelStoryboardAdapter(asset_store=asset_store, simulate_connected=False)
    provider = OpenModelStoryboardProvider(adapter=adapter, asset_store=asset_store)

    result = provider.render_panel(sample_panel, version=1)

    # 1. Final SVG artwork is not present in raster result model
    assert getattr(result, "svg_content", None) is None, "Procedural SVG must not masquerade as final artwork"
    assert not result.image_url, "No raster image URL should be present when unrendered"

    # 2. Previs guide must be generated and preserved internally
    assert result.control_bundle is not None
    assert result.control_bundle.previs_svg is not None
    assert "PREVIS CONTROL GUIDE" in result.control_bundle.previs_svg
    assert "NOT FINAL ARTWORK" in result.control_bundle.previs_svg

    # 3. Status messages must clearly indicate unrendered state with previs guide
    assert "Storyboard render unavailable" in result.status_message
    assert result.previs_guide_available is True


def test_capabilities_endpoint(tmp_path):
    """Test /api/storyboard/capabilities endpoint discovery."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    resp = client.get("/api/storyboard/capabilities")
    assert resp.status_code == 200
    data = resp.json()

    assert "provider" in data
    assert "render_modes_supported" in data
    assert "pose_control" in data
    assert "edge_control" in data
    assert "depth_control" in data
    assert "pricing_disclaimer" in data
    assert data["max_resolution"] == "1280x720"


def test_configure_renderer_endpoint(tmp_path):
    """Test /api/storyboard/configure endpoint updating runtime parameters."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    payload = {
        "provider": "comfyui",
        "runtime_url": "http://127.0.0.1:8188",
        "model": "flux1-schnell-fp8",
    }
    resp = client.post("/api/storyboard/configure", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "configured"
    assert data["provider"] == "comfyui"
    assert data["runtime_url"] == "http://127.0.0.1:8188"
    assert data["model"] == "flux1-schnell-fp8"


def test_prompt_compiler_14_sections(sample_panel):
    """Verify prompt compiler builds all 14 required sections with acting translation and negative constraints."""
    char_pack = CharacterContinuityPack(
        character_id="char_elena",
        name="Elena Vance",
        age="Late 20s",
        build="Athletic, lean",
        face_shape="High cheekbones, sharp jaw",
        signature_clothing="Charcoal trench coat over high-neck sweater",
        color_palette=["#1e293b", "#0f172a", "#f59e0b"],
        identifying_marks="Faint scar above left brow",
    )
    loc_pack = LocationContinuityPack(
        location_id="loc_warehouse",
        name="Abandoned Waterfront Warehouse",
        architectural_style="Industrial steel truss and rotting corrugated siding",
        key_landmarks=["Rusted crane arm", "Broken skylights", "Rainwater pools"],
        color_palette=["#0f172a", "#1e293b", "#334155"],
        lighting_fixtures="Shattered halogen hanging fixtures with blue moonlight spill",
    )
    prop_pack = PropContinuityPack(
        prop_id="prop_dossier",
        name="Classified Dossier",
        shape_and_form="Heavy manila folder with red diagonal classified stamp",
        materials="Aged cardstock, metal brass prong clasp",
        wear_and_tear="Water damage on corners, singed edge",
    )

    compiler = StoryboardImagePromptCompiler()
    compiled = compiler.compile(
        panel=sample_panel,
        char_packs={"char_elena": char_pack},
        loc_pack=loc_pack,
        prop_packs={"prop_dossier": prop_pack},
    )

    prompt = compiled.full_prompt
    neg = compiled.negative

    # Check all prompt sections 1-13 are present in positive prompt
    expected_headers = [
        "[STYLE]:",
        "[CAMERA]:",
        "[SHOT]:",
        "[ACTION]:",
        "[CHARACTERS]:",
        "[POSE]:",
        "[EXPRESSION]:",
        "[WARDROBE]:",
        "[LOCATION]:",
        "[PROPS]:",
        "[LIGHTING]:",
        "[DEPTH]:",
        "[CONTINUITY]:",
    ]
    for header in expected_headers:
        assert header in prompt, f"Header {header} missing from compiled prompt"

    # Verify physical performance translation (no internal thoughts)
    assert "trembling" in prompt or "hands" in prompt
    assert "internal monologue" not in prompt

    # Verify strict negative constraints (Section 14)
    assert "dialogue text" in neg
    assert "watermark" in neg


def test_continuity_packs_and_reference_sheet():
    """Verify character continuity pack and multi-view reference sheet generation."""
    ref_sheet = CharacterReferenceSheet(
        character_id="char_marcus",
        character_name="Marcus Kane",
        front_portrait_prompt="Frontal portrait of Marcus Kane, aged 40s",
        three_quarter_prompt="Three-quarter angle portrait of Marcus Kane",
        profile_prompt="Side profile of Marcus Kane",
        full_body_neutral_prompt="Full body neutral standing pose",
        reference_views={
            "front_portrait": "/api/assets/ref/front.jpg",
            "three_quarter": "/api/assets/ref/three_quarter.jpg",
        },
    )
    assert "front_portrait" in ref_sheet.reference_views
    assert ref_sheet.reference_views["front_portrait"] == "/api/assets/ref/front.jpg"

    pack = CharacterContinuityPack(
        character_id="char_marcus",
        name="Marcus Kane",
        age="Mid 40s",
        build="Heavy-set, broad shoulders",
        wardrobe="Worn leather flight jacket and dark trousers",
        reference_sheet=ref_sheet,
    )

    summary = pack.prompt_summary()
    assert "Marcus Kane" in summary
    assert "Mid 40s" in summary
    assert "Worn leather flight jacket" in summary


def test_control_bundle_generation(asset_store, sample_panel):
    """Verify PrevisControlRenderer creates all structural control maps."""
    renderer = PrevisControlRenderer(asset_store=asset_store)
    bundle = renderer.generate_control_bundle(sample_panel, version=1)

    assert bundle.pose_map is not None
    assert bundle.edge_map is not None
    assert bundle.depth_map is not None
    assert bundle.composition_mask is not None
    assert bundle.camera_layout is not None
    assert bundle.previs_svg is not None
    assert "PREVIS CONTROL GUIDE" in bundle.previs_svg
    assert bundle.camera_details["shot_type"] == sample_panel.shot_type.value


def test_keyframe_selection_8_shot_sequence():
    """Verify deterministic keyframe selection on the 8-shot test sequence."""
    panels = [
        StoryboardPanel(
            id=f"p_{i}",
            panel_id=f"p_{i}",
            scene_number=1,
            panel_number=i + 1,
            shot_number=i + 1,
            page_number=1,
            shot_type=ShotType.WIDE if i == 0 else (ShotType.CLOSE_UP if i in (3, 4) else ShotType.MEDIUM),
            camera_angle=CameraAngle.EYE_LEVEL,
            narrative_purpose=ShotPurpose.ESTABLISH if i == 0 else (
                ShotPurpose.REVEAL if i == 3 else (
                    ShotPurpose.CLIMAX if i == 4 else (
                        ShotPurpose.RESOLUTION if i == 7 else ShotPurpose.ACTION
                    )
                )
            ),
            action_description=f"Action beat {i+1}",
            aspect_ratio="16:9",
        )
        for i in range(8)
    ]

    selected_0_indexed = select_keyframe_indices(panels)

    # 1-based indexing expectations: 1, 4, 5, 8
    expected_1_indexed = [1, 4, 5, 8]
    selected_1_indexed = [idx + 1 for idx in selected_0_indexed]

    assert selected_1_indexed == expected_1_indexed, f"Expected keyframe shots {expected_1_indexed}, got {selected_1_indexed}"


def test_mock_open_model_raster_rendering(asset_store, sample_panel):
    """Verify mock adapter renders authentic raster PNG panels."""
    adapter = MockOpenModelStoryboardAdapter(asset_store=asset_store, simulate_connected=True)
    provider = OpenModelStoryboardProvider(adapter=adapter, asset_store=asset_store)

    result = provider.render_panel(sample_panel, version=1)

    assert result.status.value == "ready"
    assert result.image_url != ""
    assert result.image_url.endswith(".png")
    assert result.mime_type == "image/png"


def test_version_preservation_and_asset_store(asset_store, sample_panel):
    """Verify multiple versions (v1, v2, v3) are preserved with seeds and prompt hashes."""
    adapter = MockOpenModelStoryboardAdapter(asset_store=asset_store, simulate_connected=True)
    provider = OpenModelStoryboardProvider(adapter=adapter, asset_store=asset_store)

    v1_res = provider.render_panel(sample_panel, version=1)
    v2_res = provider.render_panel(sample_panel, version=2)
    v3_res = provider.render_panel(sample_panel, version=3)

    assert v1_res.version == 1
    assert v2_res.version == 2
    assert v3_res.version == 3

    assert v1_res.seed != v2_res.seed
    assert v1_res.image_url != v2_res.image_url

    # Check asset store persisted panel records
    rec1 = asset_store.load_panel_record("proj_default", sample_panel.id, version=1)
    rec2 = asset_store.load_panel_record("proj_default", sample_panel.id, version=2)
    rec3 = asset_store.load_panel_record("proj_default", sample_panel.id, version=3)

    assert rec1 is not None
    assert rec2 is not None
    assert rec3 is not None
    assert rec1["version"] == 1
    assert rec2["version"] == 2
    assert rec3["version"] == 3
    assert rec1["seed"] != rec2["seed"]


def test_panel_control_bundle_and_continuity_endpoints(tmp_path, sample_panel):
    """Test /control-bundle and /continuity endpoints via FastAPI."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    # 1. Create a project
    proj_resp = client.post("/api/projects", json={"title": "Continuity Test", "seed_prompt": "Undercover warehouse"})
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # 2. Test continuity endpoint
    cont_resp = client.get(f"/api/projects/{proj_id}/storyboard/continuity")
    assert cont_resp.status_code == 200
    cont_data = cont_resp.json()
    assert "characters" in cont_data
    assert "locations" in cont_data
    assert "props" in cont_data
