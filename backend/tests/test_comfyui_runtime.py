"""Tests for ComfyUI Runtime Adapter and Keyframe Integration.

Verifies:
1. Health check states:
   - RUNTIME_UNREACHABLE (unconfigured URL or connection failure)
   - MODEL_NOT_CONFIGURED (missing model name)
   - WORKFLOW_INVALID (missing required ComfyUI nodes or bad endpoint)
   - RUNTIME_READY (valid runtime and core nodes)
2. Workflow payload schema (standard 7-node API graph)
3. Job submission, history polling, image retrieval, and asset persistence
4. Recovery on generation timeout (previs guide preserved, no fake artwork)
5. 8-shot test scenario ("An undercover detective enters an abandoned warehouse...")
   selecting keyframes 1, 4, 5, 8
6. Zero multi-GB checkpoint downloads in Codespaces
"""

import os
import glob
from unittest.mock import MagicMock, patch
import pytest

from src.storyboard.models import StoryboardPanel, StoryboardImageStatus
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.open_model_provider import (
    ComfyUIStoryboardAdapter,
    OpenModelStoryboardProvider,
    select_keyframe_indices,
    RenderMode,
)
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
)


def test_health_check_runtime_unreachable_empty_url():
    """Verify RUNTIME_UNREACHABLE when STORYBOARD_RUNTIME_URL is empty."""
    adapter = ComfyUIStoryboardAdapter(runtime_url="", model_name="sdxl_graphite")
    health = adapter.health_check()
    assert health["available"] is False
    assert health["status"] == "RUNTIME_UNREACHABLE"
    assert "STORYBOARD_RUNTIME_URL not configured" in health["message"]

    caps = adapter.get_capabilities()
    assert caps.available is False
    assert caps.status == "RUNTIME_UNREACHABLE"
    assert caps.provider == "comfyui"


def test_health_check_runtime_unreachable_connection_error():
    """Verify RUNTIME_UNREACHABLE when URL points to unreachable host."""
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:59999",
        model_name="sdxl_graphite",
    )
    health = adapter.health_check()
    assert health["available"] is False
    assert health["status"] == "RUNTIME_UNREACHABLE"
    assert "Could not reach ComfyUI runtime" in health["message"]


def test_health_check_model_not_configured():
    """Verify MODEL_NOT_CONFIGURED when model is empty string."""
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="",
    )
    health = adapter.health_check()
    assert health["available"] is False
    assert health["status"] == "MODEL_NOT_CONFIGURED"
    assert "STORYBOARD_MODEL is not configured" in health["message"]


def test_health_check_workflow_invalid():
    """Verify WORKFLOW_INVALID when /system_stats succeeds but required nodes are missing."""
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="sdxl_graphite",
    )

    mock_stats_resp = MagicMock()
    mock_stats_resp.status_code = 200
    mock_stats_resp.json.return_value = {"system": {"os": "linux"}}

    # Missing KSampler and VAEDecode
    mock_obj_resp = MagicMock()
    mock_obj_resp.status_code = 200
    mock_obj_resp.json.return_value = {
        "CheckpointLoaderSimple": {},
        "CLIPTextEncode": {},
        "EmptyLatentImage": {},
        "SaveImage": {},
    }

    def mock_get(url, *args, **kwargs):
        if url.endswith("/system_stats"):
            return mock_stats_resp
        if url.endswith("/object_info"):
            return mock_obj_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        MockClient.return_value.__enter__.return_value = mock_client_instance

        health = adapter.health_check()
        assert health["available"] is False
        assert health["status"] == "WORKFLOW_INVALID"
        assert "missing required core nodes" in health["message"]


def test_health_check_runtime_ready():
    """Verify RUNTIME_READY when /system_stats and required nodes succeed."""
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="sdxl_storyboard_graphite_v1",
    )

    mock_stats_resp = MagicMock()
    mock_stats_resp.status_code = 200
    mock_stats_resp.json.return_value = {"system": {"os": "linux"}}

    mock_obj_resp = MagicMock()
    mock_obj_resp.status_code = 200
    mock_obj_resp.json.return_value = {
        "CheckpointLoaderSimple": {},
        "CLIPTextEncode": {},
        "EmptyLatentImage": {},
        "KSampler": {},
        "VAEDecode": {},
        "SaveImage": {},
        "ControlNetLoader": {},
        "ControlNetApply": {},
    }

    def mock_get(url, *args, **kwargs):
        if url.endswith("/system_stats"):
            return mock_stats_resp
        if url.endswith("/object_info"):
            return mock_obj_resp
        raise ValueError(f"Unexpected URL: {url}")

    with patch("httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        MockClient.return_value.__enter__.return_value = mock_client_instance

        health = adapter.health_check()
        assert health["available"] is True
        assert health["status"] == "RUNTIME_READY"
        assert health["supports_controlnet"] is True

        caps = adapter.get_capabilities()
        assert caps.available is True
        assert caps.status == "RUNTIME_READY"
        assert caps.pose_control is True
        assert caps.depth_control is True


def test_workflow_payload_structure():
    """Verify workflow payload contains canonical 7 ComfyUI node graph."""
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="sdxl_storyboard_graphite_v1",
    )

    payload = adapter._build_workflow_payload(
        compiled_prompt="Cinematic wide shot of abandoned warehouse",
        negative_prompt="photorealistic, 3d render",
        seed=101,
        panel_id="panel_1",
    )

    assert "client_id" in payload
    assert "prompt" in payload
    nodes = payload["prompt"]

    # 1. Checkpoint loader
    assert nodes["4"]["class_type"] == "CheckpointLoaderSimple"
    assert nodes["4"]["inputs"]["ckpt_name"] == "sdxl_storyboard_graphite_v1"

    # 2. Empty Latent
    assert nodes["5"]["class_type"] == "EmptyLatentImage"
    assert nodes["5"]["inputs"]["width"] == 1280
    assert nodes["5"]["inputs"]["height"] == 720

    # 3. Positive CLIP
    assert nodes["6"]["class_type"] == "CLIPTextEncode"
    assert "abandoned warehouse" in nodes["6"]["inputs"]["text"]

    # 4. Negative CLIP
    assert nodes["7"]["class_type"] == "CLIPTextEncode"
    assert "photorealistic" in nodes["7"]["inputs"]["text"]

    # 5. KSampler
    assert nodes["3"]["class_type"] == "KSampler"
    assert nodes["3"]["inputs"]["seed"] == 101

    # 6. VAE Decode
    assert nodes["8"]["class_type"] == "VAEDecode"

    # 7. Save Image
    assert nodes["9"]["class_type"] == "SaveImage"


def test_prompt_submission_polling_retrieval_and_asset_persistence(tmp_path):
    """Verify full end-to-end execution: submit prompt -> poll history -> retrieve image -> save asset."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="sdxl_storyboard_graphite_v1",
        asset_store=store,
        timeout=5.0,
    )

    panel = StoryboardPanel(
        id="panel_test_submit",
        panel_id="panel_test_submit",
        project_id="proj_warehouse",
        shot_number=1,
        shot_type="wide",
        camera_angle="eye_level",
        action="Detective enters dark warehouse entrance",
        aspect_ratio="16:9",
    )


    fake_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    # Mock responses
    stats_resp = MagicMock(status_code=200, json=lambda: {"system": {}})
    obj_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "CheckpointLoaderSimple": {},
            "CLIPTextEncode": {},
            "EmptyLatentImage": {},
            "KSampler": {},
            "VAEDecode": {},
            "SaveImage": {},
        },
    )
    submit_resp = MagicMock(status_code=200, json=lambda: {"prompt_id": "prompt_abc_999"})
    history_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "prompt_abc_999": {
                "status": {"completed": True},
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "warehouse_01.png", "subfolder": "", "type": "output"}
                        ]
                    }
                },
            }
        },
    )
    view_resp = MagicMock(status_code=200, content=fake_png_bytes)

    def mock_get(url, *args, **kwargs):
        if "/system_stats" in url:
            return stats_resp
        if "/object_info" in url:
            return obj_resp
        if "/history/" in url:
            return history_resp
        if "/view" in url:
            return view_resp
        raise ValueError(f"Unexpected GET URL: {url}")

    def mock_post(url, *args, **kwargs):
        if "/prompt" in url:
            return submit_resp
        raise ValueError(f"Unexpected POST URL: {url}")

    with patch("httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        mock_client_instance.post.side_effect = mock_post
        MockClient.return_value.__enter__.return_value = mock_client_instance

        res = adapter.render_panel(panel, version=1)

        assert res.status == StoryboardImageStatus.READY
        assert res.image_url is not None
        assert res.image_url.endswith(".png")
        assert res.mime_type == "image/png"
        assert res.provider == "comfyui"

        # Check asset persistence
        saved_file = tmp_path / "proj_warehouse" / "storyboard" / "panels" / "panel_test_submit_v1.png"
        assert saved_file.exists()
        assert saved_file.read_bytes() == fake_png_bytes



def test_timeout_and_error_recovery(tmp_path):
    """Verify timeout produces clean failure result without crashing and preserves previs guide."""
    store = StoryboardAssetStore(base_dir=tmp_path)
    adapter = ComfyUIStoryboardAdapter(
        runtime_url="http://127.0.0.1:8188",
        model_name="sdxl_storyboard_graphite_v1",
        asset_store=store,
        timeout=1.0,  # Fast timeout for test
    )

    panel = StoryboardPanel(
        id="panel_test_timeout",
        panel_id="panel_test_timeout",
        project_id="proj_warehouse",
        shot_number=4,
        shot_type="medium",
        camera_angle="low_angle",
        action="Detective creeps along shipping crates",
    )

    stats_resp = MagicMock(status_code=200, json=lambda: {"system": {}})
    obj_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "CheckpointLoaderSimple": {},
            "CLIPTextEncode": {},
            "EmptyLatentImage": {},
            "KSampler": {},
            "VAEDecode": {},
            "SaveImage": {},
        },
    )
    submit_resp = MagicMock(status_code=200, json=lambda: {"prompt_id": "prompt_timeout_123"})
    # History never contains prompt_id
    history_resp = MagicMock(status_code=200, json=lambda: {})

    def mock_get(url, *args, **kwargs):
        if "/system_stats" in url:
            return stats_resp
        if "/object_info" in url:
            return obj_resp
        if "/history/" in url:
            return history_resp
        raise ValueError(f"Unexpected GET URL: {url}")

    with patch("httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        mock_client_instance.post.return_value = submit_resp
        MockClient.return_value.__enter__.return_value = mock_client_instance

        res = adapter.render_panel(panel, version=1)

        assert res.status == StoryboardImageStatus.FAILED
        assert res.fallback_reason == "TIMEOUT"
        assert "timed out" in res.status_message
        assert res.previs_guide_available is True
        assert res.image_url is None


def test_undercover_detective_scenario_selects_keyframes_1_4_5_8(tmp_path):
    """Verify 8-shot test scenario:
    'An undercover detective enters an abandoned warehouse at midnight to recover a stolen classified dossier.'
    Properly identifies and renders keyframes for Shot 1, Shot 4, Shot 5, Shot 8.
    """
    store = StoryboardAssetStore(base_dir=tmp_path)
    adapter = ComfyUIStoryboardAdapter(asset_store=store)
    provider = OpenModelStoryboardProvider(adapter=adapter, asset_store=store)

    # 8-shot scenario sequence
    panels = [
        StoryboardPanel(
            id="shot_1",
            shot_number=1,
            shot_type="wide",
            camera_angle="eye_level",
            action="Establishing wide: Undercover detective Elena Vance approaches the decaying waterfront warehouse at midnight under rain-slicked skies.",
            is_keyframe=True,
        ),
        StoryboardPanel(
            id="shot_2",
            shot_number=2,
            shot_type="medium",
            camera_angle="eye_level",
            action="Elena tests the padlocked service entrance, finding the rusted chain severed.",
        ),
        StoryboardPanel(
            id="shot_3",
            shot_number=3,
            shot_type="over_shoulder",
            camera_angle="low_angle",
            action="Elena slips through the cracked door into pitch darkness, silhouetted against moonlight.",
        ),
        StoryboardPanel(
            id="shot_4",
            shot_number=4,
            shot_type="medium",
            camera_angle="low_angle",
            action="Interior tension: Elena creeps past towering shipping crates, flashlight beam cutting through airborne dust.",
            is_keyframe=True,
        ),
        StoryboardPanel(
            id="shot_5",
            shot_number=5,
            shot_type="close_up",
            camera_angle="eye_level",
            action="Close up on Elena discovering the stolen classified dossier in a rusted lockbox, red classified stamp visible.",
            is_keyframe=True,
        ),
        StoryboardPanel(
            id="shot_6",
            shot_number=6,
            shot_type="close_up",
            camera_angle="high_angle",
            action="Elena inspects the contents of the dossier, verifying the microfilm inside.",
        ),
        StoryboardPanel(
            id="shot_7",
            shot_number=7,
            shot_type="extreme_wide",
            camera_angle="bird_eye",
            action="A metal catwalk creaks overhead as a shadowy figure aims a suppressed pistol downward.",
        ),
        StoryboardPanel(
            id="shot_8",
            shot_number=8,
            shot_type="medium",
            camera_angle="dutch_angle",
            action="Climax: Gunfire sparks off the steel container as Elena dives behind cover, shielding the recovered dossier.",
            is_keyframe=True,
        ),
    ]


    kf_indices = select_keyframe_indices(panels)
    # Expected keyframe indices in 0-indexed sequence: 0 (shot 1), 3 (shot 4), 4 (shot 5), 7 (shot 8)
    assert 0 in kf_indices  # Shot 1
    assert 3 in kf_indices  # Shot 4
    assert 4 in kf_indices  # Shot 5
    assert 7 in kf_indices  # Shot 8

    # When rendered in KEYFRAMES mode without runtime connected:
    results = provider.render_sequence(panels, mode=RenderMode.KEYFRAMES)
    assert len(results) == 8

    for idx, res in enumerate(results):
        if idx in kf_indices:
            # Keyframe attempted render: runtime unreachable produces FAILED with previs guide
            assert res.status == StoryboardImageStatus.FAILED
            assert res.fallback_reason == "RUNTIME_UNREACHABLE"
            assert res.previs_guide_available is True
        else:
            # Non-keyframe deferred: PLANNED with previs guide
            assert res.status == StoryboardImageStatus.PLANNED
            assert res.previs_guide_available is True


def test_zero_model_download_in_codespace():
    """Verify ZERO multi-GB weights or checkpoint files were downloaded into workspace."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    heavy_extensions = ["*.safetensors", "*.ckpt", "*.bin", "*.pth", "*.onnx"]
    matched_heavy_files = []

    for ext in heavy_extensions:
        matches = glob.glob(os.path.join(workspace_root, "**", ext), recursive=True)
        for m in matches:
            # Only consider files > 50MB as prohibited heavy model checkpoints
            if os.path.exists(m) and os.path.getsize(m) > 50 * 1024 * 1024:
                matched_heavy_files.append(m)

    assert matched_heavy_files == [], f"Found prohibited large model checkpoints: {matched_heavy_files}"
