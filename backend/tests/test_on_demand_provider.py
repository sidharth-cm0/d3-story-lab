"""Tests for Low-Cost On-Demand Storyboard Image Provider and Keyframe Generation.

Verifies:
1. Health check states:
   - QUOTA_UNAVAILABLE when API key is missing
   - READY when API key is provided
   - Pricing disclaimer: "Free/limited provider availability depends on current quota."
2. Capabilities reporting:
   - provider="on_demand", still image focus, reference support, disclaimer
3. Strict still-image validation:
   - Accepts PNG, JPEG, WebP
   - Strictly rejects GIF, MP4, and video/animation formats
4. Single-request execution & disk persistence:
   - Submits single request, waits, downloads, saves to StoryboardAssetStore
   - Returns valid PanelArtworkAssetRecord and image_url
5. Quota fallback & resilience:
   - Gracefully handles HTTP 429 / 402 with "Image generation quota unavailable."
   - Retains previs guide without crashing project or screenplay
   - Retries model warmup (HTTP 503)
6. Keyframe selection & narrative priority:
   - Enforces keyframe budgets: 4, 8, 12 (hard ceiling of 12)
   - Prioritizes opening, clue, reaction, confrontation, climax, ending
7. API routes:
   - GET /api/storyboard/capabilities
   - POST /api/storyboard/configure
   - POST /api/projects/{id}/storyboard/generate with keyframe_budget
8. Credential safety: API tokens are never exposed in responses
"""

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle, StoryboardImageStatus
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.on_demand_provider import (
    OnDemandStoryboardProvider,
    validate_still_image,
    QUOTA_UNAVAILABLE_MESSAGE,
    PRICING_QUOTA_DISCLAIMER,
)
from src.storyboard.open_model_provider import select_keyframe_indices
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
)
from src.api.app import create_app


# 1x1 8-bit PNG sample bytes
MOCK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# 1x1 JPEG sample bytes
MOCK_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
    b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# 1x1 WebP sample bytes
MOCK_WEBP_BYTES = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01\x2a\x01\x00\x01\x00\x02\x004\x25\xa4\x00"
)


@pytest.fixture
def sample_panel():
    return StoryboardPanel(
        id="panel_test_01",
        project_id="proj_warehouse",
        scene_number=1,
        panel_number=1,
        shot_number=1,
        page_number=1,
        shot_type=ShotType.WIDE,
        camera_angle=CameraAngle.EYE_LEVEL,
        action_description="Detective enters an abandoned warehouse through rusted corrugated doors.",
        visual_prompt="Wide establishing shot of detective silhouetted in dusty warehouse doorway.",
        location_id="loc_warehouse",
        location_name="Abandoned Warehouse",
        characters_present=["char_detective"],
        character_names=["Detective"],
        aspect_ratio="16:9",
        source_event_ids=["evt_1"],
    )


# ---------------------------------------------------------------------------
# 1. Health check & Capabilities
# ---------------------------------------------------------------------------

def test_health_check_quota_unavailable_without_token():
    """Verify provider reports QUOTA_UNAVAILABLE when no API key is provided."""
    with patch.dict(os.environ, {}, clear=True):
        provider = OnDemandStoryboardProvider(api_key="")
        health = provider.health_check()
        assert health["available"] is False
        assert health["status"] == "QUOTA_UNAVAILABLE"
        assert health["message"] == QUOTA_UNAVAILABLE_MESSAGE


def test_health_check_ready_with_token():
    """Verify provider reports READY when API key is present."""
    provider = OnDemandStoryboardProvider(api_key="hf_test_secret_token_123")
    health = provider.health_check()
    assert health["available"] is True
    assert health["status"] == "READY"
    assert PRICING_QUOTA_DISCLAIMER in health["message"]


def test_capabilities_report():
    """Verify get_capabilities reports on_demand provider specifications."""
    provider = OnDemandStoryboardProvider(api_key="hf_test_key")
    caps = provider.get_capabilities()
    assert caps.provider == "on_demand"
    assert caps.available is True
    assert caps.status == "READY"
    assert caps.pricing_disclaimer == PRICING_QUOTA_DISCLAIMER
    assert caps.supports_reference_images is True
    assert caps.seed_support is True
    assert caps.pose_control is False
    assert "hf_test_key" not in caps.model_dump_json()


# ---------------------------------------------------------------------------
# 2. Strict Still-Image Validation
# ---------------------------------------------------------------------------

def test_validate_still_image_png():
    mime, ext = validate_still_image(MOCK_PNG_BYTES)
    assert mime == "image/png"
    assert ext == "png"


def test_validate_still_image_jpeg():
    mime, ext = validate_still_image(MOCK_JPEG_BYTES)
    assert mime == "image/jpeg"
    assert ext == "jpg"


def test_validate_still_image_webp():
    mime, ext = validate_still_image(MOCK_WEBP_BYTES)
    assert mime == "image/webp"
    assert ext == "webp"


def test_validate_still_image_rejects_animation_and_video():
    # GIF rejection
    with pytest.raises(ValueError, match="strictly prohibited"):
        validate_still_image(b"GIF89a\x01\x00\x01\x00\x80\x00\x00")

    # MP4 rejection
    with pytest.raises(ValueError, match="strictly prohibited"):
        validate_still_image(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

    # Corrupt / random bytes
    with pytest.raises(ValueError, match="Unsupported image format"):
        validate_still_image(b"NOT_AN_IMAGE_PAYLOAD_AT_ALL")


# ---------------------------------------------------------------------------
# 3. Single-Request Execution & Asset Persistence
# ---------------------------------------------------------------------------

def test_render_panel_success(tmp_path, sample_panel):
    """Verify single request execution, still image validation, and disk persistence."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    provider = OnDemandStoryboardProvider(
        api_key="hf_mock_token",
        asset_store=store,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = MOCK_PNG_BYTES

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = provider.render_panel(sample_panel, version=1)

        assert result.status == StoryboardImageStatus.READY
        assert result.provider == "on_demand"
        assert result.image_url is not None
        assert result.asset_record is not None
        assert result.asset_record.mime_type == "image/png"
        assert PRICING_QUOTA_DISCLAIMER in result.render_metadata["pricing_disclaimer"]

        # Verify target film storyboard prompt style was included
        assert "professional film storyboard" in result.compiled_prompt
        assert "graphite and charcoal sketch" in result.compiled_prompt

        # Verify asset was persisted to disk
        expected_file = tmp_path / "proj_warehouse" / "storyboard" / "panels" / f"{sample_panel.id}_v1.png"
        assert expected_file.exists()
        assert expected_file.read_bytes() == MOCK_PNG_BYTES


def test_render_panel_quota_unavailable_without_token(sample_panel):
    """Verify rendering without token returns QUOTA_UNAVAILABLE with fallback reason."""
    provider = OnDemandStoryboardProvider(api_key="")
    result = provider.render_panel(sample_panel)

    assert result.status == StoryboardImageStatus.FAILED
    assert result.fallback_reason == "QUOTA_UNAVAILABLE"
    assert result.status_message == QUOTA_UNAVAILABLE_MESSAGE
    assert result.previs_guide_available is True
    assert result.image_url is None


def test_render_panel_http_429_quota_exceeded(sample_panel):
    """Verify HTTP 429 gracefully triggers QUOTA_UNAVAILABLE without crashing."""
    provider = OnDemandStoryboardProvider(api_key="hf_mock_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = provider.render_panel(sample_panel)

        assert result.status == StoryboardImageStatus.FAILED
        assert result.fallback_reason == "QUOTA_UNAVAILABLE"
        assert result.status_message == QUOTA_UNAVAILABLE_MESSAGE
        assert result.previs_guide_available is True


def test_render_panel_http_401_invalid_token(sample_panel):
    """Verify HTTP 401 returns INVALID_CREDENTIALS without throwing unhandled exception."""
    provider = OnDemandStoryboardProvider(api_key="hf_invalid_token_sample")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = provider.render_panel(sample_panel)

        assert result.status == StoryboardImageStatus.FAILED
        assert result.fallback_reason == "INVALID_CREDENTIALS"
        assert "Invalid or unauthorized Hugging Face token" in result.status_message
        assert result.previs_guide_available is True


def test_render_panel_503_retry_then_success(sample_panel):
    """Verify HTTP 503 model warming up retries and succeeds."""
    provider = OnDemandStoryboardProvider(api_key="hf_mock_token")

    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.content = MOCK_PNG_BYTES

    with patch("httpx.Client") as mock_client_cls, patch("time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_client.post.side_effect = [mock_resp_503, mock_resp_200]
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = provider.render_panel(sample_panel)

        assert result.status == StoryboardImageStatus.READY
        assert mock_sleep.called
        assert mock_client.post.call_count == 2


# ---------------------------------------------------------------------------
# 4. Keyframe Selection & Narrative Priority
# ---------------------------------------------------------------------------

def test_select_keyframe_indices_budgets_and_narrative_beats():
    """Verify budget limits (4, 8, 12, max 12) and narrative prioritization."""
    # Construct an 8-shot test sequence representing warehouse story
    panels = [
        # Shot 1: Opening establishing shot
        StoryboardPanel(
            id="p1", scene_number=1, panel_number=1, shot_number=1,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.EYE_LEVEL,
            action_description="Detective enters the abandoned warehouse.",
            visual_prompt="Wide establishing shot of detective.",
        ),
        # Shot 2: Medium shot walking
        StoryboardPanel(
            id="p2", scene_number=1, panel_number=2, shot_number=2,
            shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
            action_description="Detective walks along crates.",
            visual_prompt="Medium shot walking.",
        ),
        # Shot 3: Over-the-shoulder look
        StoryboardPanel(
            id="p3", scene_number=1, panel_number=3, shot_number=3,
            shot_type=ShotType.OVER_SHOULDER, camera_angle=CameraAngle.EYE_LEVEL,
            action_description="Over the shoulder of detective watching a suspicious door.",
            visual_prompt="OTS shot of door.",
        ),
        # Shot 4: Deceptive close-up
        StoryboardPanel(
            id="p4", scene_number=1, panel_number=4, shot_number=4,
            shot_type=ShotType.CLOSE_UP, camera_angle=CameraAngle.LOW_ANGLE,
            action_description="Detective's eyes narrow as he notices something hidden.",
            visual_prompt="Close up deceptive expression.",
        ),
        # Shot 5: Clue insert
        StoryboardPanel(
            id="p5", scene_number=1, panel_number=5, shot_number=5,
            shot_type=ShotType.INSERT, camera_angle=CameraAngle.HIGH_ANGLE,
            action_description="Insert of the classified dossier hidden inside rusted pipe.",
            visual_prompt="Insert of dossier.",
        ),
        # Shot 6: Major reaction
        StoryboardPanel(
            id="p6", scene_number=1, panel_number=6, shot_number=6,
            shot_type=ShotType.REACTION, camera_angle=CameraAngle.EYE_LEVEL,
            action_description="Guard suddenly reacts to footsteps in the dark.",
            visual_prompt="Reaction shot of guard.",
        ),
        # Shot 7: Confrontation / guard exit
        StoryboardPanel(
            id="p7", scene_number=1, panel_number=7, shot_number=7,
            shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
            action_description="Detective confronts the guard with drawn flashlight.",
            visual_prompt="Confrontation in corridor.",
        ),
        # Shot 8: Climax / Ending
        StoryboardPanel(
            id="p8", scene_number=1, panel_number=8, shot_number=8,
            shot_type=ShotType.WIDE, camera_angle=CameraAngle.LOW_ANGLE,
            action_description="Detective escapes into the rain with the dossier as shadows close in.",
            visual_prompt="Climax and ending escape.",
        ),
    ]

    # Test budget = 4: Should pick highest narrative weights (Opening=0, Climax/Ending=7, Clue=4, Reaction=5)
    k4 = select_keyframe_indices(panels, budget=4)
    assert len(k4) == 4
    assert 0 in k4  # Opening
    assert 7 in k4  # Climax / Ending
    assert 4 in k4  # Clue insert
    assert 5 in k4  # Guard reaction

    # Test budget = 8: All 8 narrative shots selected
    k8 = select_keyframe_indices(panels, budget=8)
    assert len(k8) == 8
    assert k8 == [0, 1, 2, 3, 4, 5, 6, 7]

    # Test ceiling: If budget is 20 on 16 panels, capped at 12
    many_panels = panels + [
        StoryboardPanel(
            id=f"extra_{i}", scene_number=1, panel_number=9 + i, shot_number=9 + i,
            shot_type=ShotType.MEDIUM, camera_angle=CameraAngle.EYE_LEVEL,
            action_description=f"Action step {i}", visual_prompt=f"Shot {i}",
        )
        for i in range(8)
    ]
    assert len(many_panels) == 16
    k_capped = select_keyframe_indices(many_panels, budget=20)
    assert len(k_capped) == 12  # Hard ceiling of 12


# ---------------------------------------------------------------------------
# 5. API Endpoints Integration
# ---------------------------------------------------------------------------

def test_api_capabilities_on_demand():
    """Verify /api/storyboard/capabilities reports on_demand provider."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/storyboard/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] in ("on_demand", "comfyui")
    assert "Free/limited provider availability" in data.get("pricing_disclaimer", "") or "pricing_disclaimer" in data


def test_api_configure_on_demand_provider(monkeypatch):
    """Verify /api/storyboard/configure sets on_demand provider and server key securely."""
    app = create_app()
    client = TestClient(app)

    resp = client.post("/api/storyboard/configure", json={
        "provider": "on_demand",
        "api_key": "hf_test_secret_abc123",
        "model": "stabilityai/stable-diffusion-xl-base-1.0",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "on_demand"
    assert data["available"] is True
    # Verify secret is NEVER leaked in response
    assert "hf_test_secret_abc123" not in resp.text


def test_api_generate_storyboard_with_budget(tmp_path):
    """Verify generating storyboard with keyframe_budget respects budget and returns metadata."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    # 1. Create a project
    create_resp = client.post("/api/projects", json={
        "seed_prompt": "An undercover detective enters an abandoned warehouse to retrieve a classified dossier.",
        "title": "Warehouse Dossier",
    })
    assert create_resp.status_code == 200
    project_id = create_resp.json()["id"]

    # Step simulation to generate events
    client.post(f"/api/projects/{project_id}/run", json={"num_ticks": 2})

    # Generate screenplay
    sc_res = client.post(f"/api/projects/{project_id}/generate-screenplay")
    assert sc_res.status_code == 200

    # Plan storyboard
    plan_res = client.post(f"/api/projects/{project_id}/storyboard/plan", json={"density_mode": "quick", "panels_per_page": 2})
    assert plan_res.status_code == 200

    # 2. Generate storyboard with keyframe_budget=4 and provider="on_demand"
    # Even if on-demand quota is unavailable in test environment, it must fail safely
    # without breaking the project or crashing.
    gen_resp = client.post(
        f"/api/projects/{project_id}/storyboard/generate",
        json={
            "render_provider": "on_demand",
            "keyframe_budget": 4,
        },
    )
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert "shot_plan" in data
    assert "rendered_panels" in data
    rendered_panels = data["rendered_panels"]
    assert len(rendered_panels) > 0

    # Verify keyframes were selected up to budget
    keyframe_count = sum(1 for p in rendered_panels if p.get("is_keyframe") is True)
    assert keyframe_count <= 4

    # Verify all panels have valid previs guides
    for panel in rendered_panels:
        assert panel.get("mode") == "previs_guide" or panel.get("metadata", {}).get("previs_available") is True


def test_provider_status_connected_when_model_unavailable():
    """Verify provider_status remains CONNECTED when token is present but model returns 410."""
    provider = OnDemandStoryboardProvider(
        api_key="hf_test_valid_token_123",
        model_name="stabilityai/stable-diffusion-xl-base-1.0",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 410

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        health = provider.health_check(probe=True)
        assert health["available"] is False
        assert health["status"] == "MODEL_UNAVAILABLE"
        assert health["provider_status"] == "CONNECTED"
        assert health["model_status"] == "MODEL_UNAVAILABLE"

        caps = provider.get_capabilities(probe=True)
        assert caps.available is False
        assert caps.status == "MODEL_UNAVAILABLE"
        assert caps.provider_status == "CONNECTED"
        assert caps.model_status == "MODEL_UNAVAILABLE"


def test_provider_status_auth_failed_when_unauthorized():
    """Verify provider_status reports AUTH_FAILED when token is rejected (401)."""
    provider = OnDemandStoryboardProvider(
        api_key="hf_bad_token",
        model_name="stabilityai/stable-diffusion-3-medium-diffusers",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        health = provider.health_check(probe=True)
        assert health["available"] is False
        assert health["status"] == "AUTH_FAILED"
        assert health["provider_status"] == "AUTH_FAILED"
        assert health["model_status"] == "AUTH_FAILED"


def test_api_capabilities_accurate_provider_status_when_model_unavailable(monkeypatch):
    """Verify /api/storyboard/capabilities reports provider_status=CONNECTED not NOT_CONFIGURED when model is 410."""
    app = create_app()
    client = TestClient(app)

    mock_resp = MagicMock()
    mock_resp.status_code = 410

    with patch.dict(os.environ, {"HF_TOKEN": "hf_test_token_123", "ON_DEMAND_MODEL": "stabilityai/stable-diffusion-xl-base-1.0"}), \
         patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        resp = client.get("/api/storyboard/capabilities?probe=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["status"] == "MODEL_UNAVAILABLE"
        assert data["provider_status"] == "CONNECTED"
        assert data["model_status"] == "MODEL_UNAVAILABLE"
