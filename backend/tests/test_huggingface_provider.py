"""Security and Resilience Tests for External Storyboard Providers.

Verifies:
1. Canonical storyboard generation is 100% offline (HandDrawnStoryboardProvider).
2. HuggingFaceStoryboardProvider fails safely without HF_TOKEN (fallback).
3. 401, 429, and 503 responses are gracefully handled with transparent fallback.
4. No secrets or tokens are ever exposed in API responses or provider status.
5. Assets are safely written to StoryboardAssetStore.
6. Generated versions (v1, v2, v3) are preserved and never overwrite prior versions.
7. Required pricing disclaimer is consistently attached.
"""

import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app, get_image_provider
from src.storyboard.image_provider import (
    ExternalStoryboardImageProvider,
    HuggingFaceStoryboardProvider,
    FallbackReason,
    ProviderState,
)
from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
from src.storyboard.models import StoryboardPanel, ShotType, CameraAngle
from src.storyboard.asset_store import StoryboardAssetStore


DISCLAIMER = (
    "Optional external provider. Availability, quotas and pricing depend on the provider/account."
)


@pytest.fixture
def sample_panel():
    return StoryboardPanel(
        id="panel_test_101",
        scene_number=1,
        panel_number=1,
        shot_number=1,
        page_number=1,
        shot_type=ShotType.CLOSE_UP,
        camera_angle=CameraAngle.LOW_ANGLE,
        action_description="Detective investigates a clue in the dark.",
        visual_prompt="Close up low angle of detective with flashlight.",
        location_id="loc_warehouse",
        location_name="Abandoned Warehouse",
        characters_present=["char_detective"],
        character_names=["Detective"],
        aspect_ratio="16:9",
        source_event_ids=["evt_1"],
    )


def test_offline_default_provider_safety(tmp_path):
    """Verify offline HandDrawnStoryboardProvider safety and open model default."""
    from src.storyboard.image_provider import OpenModelImageProviderAdapter
    store = StoryboardAssetStore(base_dir=tmp_path)
    provider = get_image_provider(provider_type="hand_drawn", asset_store=store)

    assert isinstance(provider, HandDrawnStoryboardProvider)
    status = provider.get_status()
    assert status["mode"] == "local"
    assert status["storyboard_image_provider"] == "hand_drawn_storyboard"

    # Verify default provider without args is the new open model adapter
    default_provider = get_image_provider(asset_store=store)
    assert isinstance(default_provider, OpenModelImageProviderAdapter)


def test_huggingface_provider_disabled_without_token(tmp_path, sample_panel):
    """Verify that without HF_TOKEN, HuggingFaceStoryboardProvider falls back gracefully."""
    with patch.dict(os.environ, {}, clear=True):
        store = StoryboardAssetStore(base_dir=tmp_path)
        hf_provider = HuggingFaceStoryboardProvider(token=None, asset_store=store)

        # Status inspection reveals no token
        status = hf_provider.get_status()
        assert status["available"] is False
        assert "token" not in str(status).lower() or "no hf_token" in str(status).lower()
        assert status["pricing_disclaimer"] == DISCLAIMER

        # Panel generation produces transparent fallback with zero network calls
        result = hf_provider.generate_panel(sample_panel, bible=None, version=2)
        assert result.mode == "fallback_comic" or result.mode == "hand_drawn"
        assert result.fallback_reason == FallbackReason.NO_API_KEY.value
        assert result.render_metadata["label"] == "HAND-DRAWN STORYBOARD"
        assert result.render_metadata["pricing_disclaimer"] == DISCLAIMER
        assert "token" not in str(result.render_metadata).lower() or "no hf_token" in str(result.render_metadata).lower()


def test_huggingface_provider_handles_401_gracefully(tmp_path, sample_panel):
    """Verify 401 Unauthorized fails immediately without endless retries and falls back cleanly."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    hf_provider = HuggingFaceStoryboardProvider(token="invalid_hf_secret_token", asset_store=store)

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"error": "Invalid username or password."}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = hf_provider.generate_panel(sample_panel, bible=None, version=2)

        # Should only call once, no retries on 401
        assert mock_post.call_count == 1
        assert result.fallback_reason == FallbackReason.AUTHENTICATION_FAILED.value
        assert result.render_metadata["label"] == "HAND-DRAWN STORYBOARD"
        assert "invalid_hf_secret_token" not in str(result.model_dump())


def test_huggingface_provider_handles_503_cold_start_retry(tmp_path, sample_panel):
    """Verify 503 Model is Loading retries with backoff and succeeds if model warms up."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    hf_provider = HuggingFaceStoryboardProvider(token="valid_test_token", asset_store=store)

    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.headers = {"content-type": "application/json"}
    mock_503.json.return_value = {"error": "Model is loading", "estimated_time": 0.01}

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.headers = {"content-type": "image/jpeg"}
    mock_200.content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00test_jpg_data"

    with patch("httpx.Client.post", side_effect=[mock_503, mock_200]) as mock_post:
        with patch("time.sleep"):
            result = hf_provider.generate_panel(sample_panel, bible=None, version=2)

            assert mock_post.call_count == 2
            assert result.mode == "ai_image"
            assert result.provider == "huggingface"
            assert result.render_metadata["label"] == "EXTERNAL AI IMAGE"
            assert result.render_metadata["pricing_disclaimer"] == DISCLAIMER
            assert result.image_url.startswith("/api/projects/")


def test_huggingface_provider_handles_429_rate_limit(tmp_path, sample_panel):
    """Verify 429 Rate Limit exhaustion falls back cleanly without server crash."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    hf_provider = HuggingFaceStoryboardProvider(token="test_token", asset_store=store)

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"content-type": "application/json"}
    mock_429.json.return_value = {"error": "Rate limit reached."}

    with patch("httpx.Client.post", return_value=mock_429):
        with patch("time.sleep"):
            result = hf_provider.generate_panel(sample_panel, bible=None, version=2)

            assert result.fallback_reason == FallbackReason.QUOTA_EXCEEDED.value
            assert result.render_metadata["label"] == "HAND-DRAWN STORYBOARD"


def test_api_external_render_endpoint_and_version_preservation(tmp_path):
    """Verify external render endpoint creates new version without destroying hand-drawn v1."""
    app = create_app(store_dir=str(tmp_path))
    client = TestClient(app)

    # 1. Create project and plan shots (offline hand-drawn v1)
    create_res = client.post(
        "/api/projects",
        json={"seed_prompt": "A detective examines evidence under flickering neon lights.", "title": "Noir Case"},
    )
    assert create_res.status_code == 200
    proj_id = create_res.json()["id"]

    # Step simulation to generate events
    client.post(f"/api/projects/{proj_id}/run", json={"num_ticks": 2})

    # Generate screenplay
    sc_res = client.post(f"/api/projects/{proj_id}/generate-screenplay")
    assert sc_res.status_code == 200

    # Plan storyboard (offline hand-drawn)
    plan_res = client.post(f"/api/projects/{proj_id}/storyboard/plan", json={"density_mode": "quick", "panels_per_page": 2})
    assert plan_res.status_code == 200
    panels = plan_res.json()["shot_plan"]["panels"]
    assert len(panels) > 0
    first_panel_id = panels[0]["id"]
    assert len(panels[0]["versions"]) == 1
    assert panels[0]["versions"][0]["version"] == 1

    # 2. Call external-render endpoint with mocked HF success
    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.headers = {"content-type": "image/jpeg"}
    mock_200.content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00image_content"

    import httpx
    original_post = httpx.Client.post

    def selective_post(self, url, *args, **kwargs):
        if "api-inference.huggingface.co" in str(url):
            return mock_200
        return original_post(self, url, *args, **kwargs)

    with patch.dict(os.environ, {"HF_TOKEN": "mock_secret_hf_token"}):
        with patch.object(httpx.Client, "post", selective_post):
            ext_res = client.post(
                f"/api/projects/{proj_id}/storyboard/panels/{first_panel_id}/external-render",
                json={"provider": "huggingface"},
            )

    assert ext_res.status_code == 200
    ext_data = ext_res.json()
    assert ext_data["version"] == 2
    updated_versions = ext_data["panel"]["versions"]
    assert len(updated_versions) == 2

    # Verify v1 is still preserved as hand-drawn
    assert updated_versions[0]["version"] == 1
    # Verify v2 is the external AI image
    assert updated_versions[1]["version"] == 2
    assert updated_versions[1]["mode"] == "ai_image"
    assert updated_versions[1]["render_metadata"]["label"] == "EXTERNAL AI IMAGE"

    # Verify no secret token leaked in response body
    assert "mock_secret_hf_token" not in ext_res.text
    assert "HF_TOKEN" not in ext_res.text
