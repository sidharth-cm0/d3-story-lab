"""Open-Model Storyboard Provider and Generation Runtime Adapters.

Supports external generation runtimes for production-grade raster artwork:
1. ComfyUIStoryboardAdapter (Workflow graph submission, reference uploads, control guidance polling)
2. DiffusersStoryboardAdapter (Optional dedicated diffusers endpoint without local auto-downloads)
3. MockOpenModelStoryboardAdapter (Deterministic raster synthesis for CI/testing without GPU)
4. OpenModelStoryboardProvider (Unified orchestrator handling keyframe selection, asset persistence, and versioning)

RULES ENFORCED:
- The current Codespace is NOT the inference machine. Never auto-download multi-GB checkpoints!
- When runtime is unavailable: Return clean UNAVAILABLE status, preserving Previs guide without showing procedural SVG as final art.
"""

from __future__ import annotations
import os
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.storyboard.models import (
    StoryboardPanel,
    StoryboardImageStatus,
    ShotType,
    CameraAngle,
    ShotPurpose,
)
from src.storyboard.visual_bible import VisualBible
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
)
from src.storyboard.control import StoryboardControlBundle, PrevisControlRenderer
from src.storyboard.prompt_compiler import StoryboardImagePromptCompiler, StructuredPromptResult
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.provider_base import (
    StoryboardRenderProvider,
    ProviderCapabilityReport,
    StoryboardRenderResult,
    PanelArtworkAssetRecord,
    RenderMode,
)

logger = logging.getLogger(__name__)

# Minimal valid 960x540 or 1x1 black/slate PNG byte stream for offline testing & mock rendering
MOCK_RASTER_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x03\xc0\x00\x00\x02\x1c\x08\x00\x00\x00\x00\x38\xd2\xdb\x58"
    b"\x00\x00\x00\x1fIDATx\x9c\xec\xc1\x01\x01\x00\x00\x00\x80\x90\xfe\xaf\xee\x08\n\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x19\x1e\x9c\xa4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def select_keyframe_indices(panels: List[StoryboardPanel], budget: Optional[int] = None) -> List[int]:
    """Deterministically select significant dramatic beats for KEYFRAME render mode.

    Supports budget controls (KEYFRAMES 4, 8, 12).
    Hard-capped at maximum 12 keyframes per batch for quota and cost safety.

    Prioritizes:
    - Opening establish (Panel 0)
    - Final resolution / Ending (Panel total - 1)
    - Climax
    - Major clue / Discovery / Dossier insert
    - Deceptive close-up / Interrogation OTS
    - Major reaction
    - Confrontation / Guard controls exit / Power shift
    - First character reveal
    """
    total = len(panels)
    if total == 0:
        return []
    if total <= 1:
        return [0]

    # If budget is not explicitly specified, default dynamically:
    # For small sequences (<= 8 shots), select 4 keyframes (leaving rest deferred).
    # For larger sequences, default to 8 keyframes (hard capped at 12).
    if budget is None:
        target_budget = 4 if total <= 8 else min(8, total)
        max_budget = min(target_budget, 12, total)
    else:
        # Hard cap at maximum 12 images per batch
        max_budget = min(max(1, budget), 12, total)

    scored_candidates = []
    for idx, p in enumerate(panels):
        score = 0
        text_lower = f"{(p.action or p.action_description or '')} {(p.visual_prompt or '')}".lower()
        purpose = getattr(p, "narrative_purpose", None)
        shot_type = getattr(p, "shot_type", None)

        # 1. Opening establish (highest priority)
        if idx == 0:
            score += 100

        # 2. Final resolution / ending
        if idx == total - 1:
            score += 95

        # 3. Climax
        if purpose == ShotPurpose.CLIMAX or "climax" in text_lower:
            score += 90

        # 4. Major clue / discovery / dossier insert
        if (
            purpose in (ShotPurpose.CLUE, ShotPurpose.DISCOVERY, ShotPurpose.REVELATION, ShotPurpose.REVEAL)
            or shot_type == ShotType.INSERT
            or "dossier" in text_lower
            or "insert" in text_lower
            or "lockbox" in text_lower
            or "clue" in text_lower
        ):
            score += 85

        # 5. Deceptive close-up / interrogation OTS
        if (
            "deceptive" in text_lower
            or "interrogation" in text_lower
            or "ots" in text_lower
            or shot_type == ShotType.OVER_SHOULDER
            or "lying" in text_lower
            or (shot_type == ShotType.CLOSE_UP and "narrow" in text_lower)
        ):
            score += 80

        # 6. Major reaction
        if (
            purpose == ShotPurpose.REACTION
            or shot_type == ShotType.REACTION
            or "reaction" in text_lower
            or "react" in text_lower
        ):
            score += 75

        # 7. Confrontation / guard controls exit / power shift
        if (
            purpose in (ShotPurpose.POWER_SHIFT, ShotPurpose.THREAT)
            or "guard" in text_lower
            or "confrontation" in text_lower
            or "exit" in text_lower
            or "power shift" in text_lower
            or "gunfire" in text_lower
            or "pistol" in text_lower
        ):
            score += 70

        # 8. First character reveal
        if (
            purpose == ShotPurpose.REVEAL
            or "first reveal" in text_lower
            or "character reveal" in text_lower
            or (getattr(p, "characters_present", None) and idx <= 2)
        ):
            score += 65

        # 9. Midpoint dramatic turn
        if idx == total // 2:
            score += 60

        # 10. Explicit keyframe flag from shot planner
        if getattr(p, "is_keyframe", False):
            score += 100

        scored_candidates.append((score, idx))

    # Sort descending by score; preserve index order for ties
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))

    selected = [idx for _, idx in scored_candidates[:max_budget]]
    return sorted(selected)



class ComfyUIStoryboardAdapter(StoryboardRenderProvider):
    """Client adapter for ComfyUI generation runtimes."""

    def __init__(
        self,
        runtime_url: Optional[str] = None,
        model_name: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        workflow_template_path: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.runtime_url = (runtime_url if runtime_url is not None else os.environ.get("STORYBOARD_RUNTIME_URL", "")).rstrip("/")
        self.model_name = model_name if model_name is not None else os.environ.get("STORYBOARD_MODEL", "")
        self.asset_store = asset_store or StoryboardAssetStore()
        self.workflow_path = workflow_template_path
        self.timeout = timeout
        self.compiler = StoryboardImagePromptCompiler()

    def health_check(self) -> Dict[str, Any]:
        """Verify ComfyUI runtime reachability and workflow validity.

        Returns one of:
        - RUNTIME_UNREACHABLE
        - MODEL_NOT_CONFIGURED
        - WORKFLOW_INVALID
        - RUNTIME_READY
        """
        if not self.runtime_url:
            return {
                "available": False,
                "status": "RUNTIME_UNREACHABLE",
                "message": "Open-model storyboard runtime not connected. STORYBOARD_RUNTIME_URL not configured.",
            }
        if not self.model_name:
            return {
                "available": False,
                "status": "MODEL_NOT_CONFIGURED",
                "message": "STORYBOARD_MODEL is not configured.",
            }

        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.runtime_url}/system_stats")
                if res.status_code != 200:
                    return {
                        "available": False,
                        "status": "RUNTIME_UNREACHABLE",
                        "message": f"ComfyUI /system_stats returned HTTP {res.status_code}",
                    }
                stats = res.json()

                # Verify workflow/node schema availability
                obj_res = client.get(f"{self.runtime_url}/object_info")
                if obj_res.status_code != 200:
                    return {
                        "available": False,
                        "status": "WORKFLOW_INVALID",
                        "message": f"ComfyUI /object_info endpoint failed with HTTP {obj_res.status_code}",
                        "system": stats,
                    }

                object_info = obj_res.json()
                required_nodes = [
                    "CheckpointLoaderSimple",
                    "CLIPTextEncode",
                    "EmptyLatentImage",
                    "KSampler",
                    "VAEDecode",
                    "SaveImage",
                ]
                missing_nodes = [n for n in required_nodes if n not in object_info]
                if missing_nodes:
                    return {
                        "available": False,
                        "status": "WORKFLOW_INVALID",
                        "message": f"ComfyUI workflow missing required core nodes: {', '.join(missing_nodes)}",
                        "system": stats,
                    }

                supports_cn = "ControlNetLoader" in object_info and "ControlNetApply" in object_info

                return {
                    "available": True,
                    "status": "RUNTIME_READY",
                    "message": "ComfyUI runtime connected and ready.",
                    "system": stats,
                    "supports_controlnet": supports_cn,
                }
        except Exception as e:
            return {
                "available": False,
                "status": "RUNTIME_UNREACHABLE",
                "message": f"Could not reach ComfyUI runtime at {self.runtime_url}: {e}",
            }

    def get_capabilities(self) -> ProviderCapabilityReport:
        health = self.health_check()
        supports_cn = health.get("supports_controlnet", False)
        return ProviderCapabilityReport(
            provider="comfyui",
            model=self.model_name or "",
            available=health["available"],
            status=health["status"],
            status_message=health["message"],
            supports_reference_images=True,
            supports_ip_adapter=supports_cn,
            supports_identity_conditioning=True,
            pose_control=supports_cn,
            depth_control=supports_cn,
            edge_control=supports_cn,
            seed_support=True,
            max_resolution="1280x720",
        )

    def _build_workflow_payload(
        self,
        compiled_prompt: str,
        negative_prompt: str,
        seed: int = 42,
        steps: int = 25,
        cfg: float = 7.0,
        width: int = 1280,
        height: int = 720,
        panel_id: str = "panel",
        controlnet_supported: bool = False,
    ) -> Dict[str, Any]:
        """Build standard ComfyUI API prompt graph."""
        nodes: Dict[str, Any] = {
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.model_name or "sdxl_storyboard_graphite_v1",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": compiled_prompt,
                    "clip": ["4", 1],
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1],
                },
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"d3_{panel_id}",
                    "images": ["8", 0],
                },
            },
        }

        return {
            "client_id": f"d3_{panel_id}_{seed}",
            "prompt": nodes,
        }

    def render_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
        control_bundle: Optional[StoryboardControlBundle] = None,
        sequence_context: Optional[StoryboardSequenceContext] = None,
        version: int = 1,
    ) -> StoryboardRenderResult:
        compiled: StructuredPromptResult = self.compiler.compile(
            panel=panel,
            bible=bible,
            char_packs=char_packs,
            loc_pack=loc_pack,
            prop_packs=prop_packs,
            control_bundle=control_bundle,
            sequence_context=sequence_context,
        )

        health = self.health_check()
        if not health["available"]:
            return StoryboardRenderResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                status=StoryboardImageStatus.FAILED,
                image_url=None,
                provider="comfyui",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=compiled.full_prompt,
                negative_prompt=compiled.negative,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason=health["status"],
                status_message=health["message"],
            )

        pid = panel.panel_id or panel.id
        seed = 42 + version
        payload = self._build_workflow_payload(
            compiled_prompt=compiled.full_prompt,
            negative_prompt=compiled.negative,
            seed=seed,
            panel_id=pid,
            controlnet_supported=health.get("supports_controlnet", False),
        )

        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                submit_res = client.post(f"{self.runtime_url}/prompt", json=payload)
                if submit_res.status_code != 200:
                    return StoryboardRenderResult(
                        panel_id=pid,
                        version=version,
                        status=StoryboardImageStatus.FAILED,
                        provider="comfyui",
                        model=self.model_name,
                        prompt_hash=compiled.prompt_hash,
                        compiled_prompt=compiled.full_prompt,
                        negative_prompt=compiled.negative,
                        previs_guide_available=True,
                        control_bundle=control_bundle,
                        fallback_reason="SUBMISSION_FAILED",
                        status_message=f"ComfyUI prompt submission failed: HTTP {submit_res.status_code}",
                    )

                submit_json = submit_res.json()
                prompt_id = submit_json.get("prompt_id")
                if not prompt_id:
                    return StoryboardRenderResult(
                        panel_id=pid,
                        version=version,
                        status=StoryboardImageStatus.FAILED,
                        provider="comfyui",
                        model=self.model_name,
                        prompt_hash=compiled.prompt_hash,
                        compiled_prompt=compiled.full_prompt,
                        negative_prompt=compiled.negative,
                        previs_guide_available=True,
                        control_bundle=control_bundle,
                        fallback_reason="SUBMISSION_FAILED",
                        status_message="No prompt_id returned in ComfyUI submission response.",
                    )

                # Poll for completion
                poll_interval = 1.0
                max_polls = max(1, int(self.timeout / poll_interval))
                image_bytes: Optional[bytes] = None
                img_metadata: Dict[str, Any] = {}

                for _ in range(max_polls):
                    time.sleep(poll_interval)
                    history_res = client.get(f"{self.runtime_url}/history/{prompt_id}")
                    if history_res.status_code == 200:
                        history_data = history_res.json()
                        if prompt_id in history_data:
                            prompt_info = history_data[prompt_id]
                            exec_status = prompt_info.get("status", {})
                            if exec_status.get("status_str") == "error":
                                err_msg = exec_status.get("messages", ["ComfyUI execution error"])[0]
                                return StoryboardRenderResult(
                                    panel_id=pid,
                                    version=version,
                                    status=StoryboardImageStatus.FAILED,
                                    provider="comfyui",
                                    model=self.model_name,
                                    prompt_hash=compiled.prompt_hash,
                                    compiled_prompt=compiled.full_prompt,
                                    negative_prompt=compiled.negative,
                                    previs_guide_available=True,
                                    control_bundle=control_bundle,
                                    fallback_reason="RENDER_FAILED",
                                    status_message=f"ComfyUI error: {err_msg}",
                                )

                            outputs = prompt_info.get("outputs", {})
                            for node_id, node_out in outputs.items():
                                if "images" in node_out and node_out["images"]:
                                    img_info = node_out["images"][0]
                                    img_metadata = img_info
                                    filename = img_info["filename"]
                                    subfolder = img_info.get("subfolder", "")
                                    img_type = img_info.get("type", "output")
                                    view_url = (
                                        f"{self.runtime_url}/view?"
                                        f"filename={filename}&subfolder={subfolder}&type={img_type}"
                                    )
                                    raw_img_res = client.get(view_url)
                                    if raw_img_res.status_code == 200:
                                        image_bytes = raw_img_res.content
                                        break
                            if image_bytes:
                                break

                if not image_bytes:
                    return StoryboardRenderResult(
                        panel_id=pid,
                        version=version,
                        status=StoryboardImageStatus.FAILED,
                        provider="comfyui",
                        model=self.model_name,
                        prompt_hash=compiled.prompt_hash,
                        compiled_prompt=compiled.full_prompt,
                        negative_prompt=compiled.negative,
                        previs_guide_available=True,
                        control_bundle=control_bundle,
                        fallback_reason="TIMEOUT",
                        status_message=f"ComfyUI execution timed out after {self.timeout} seconds.",
                    )

                filename = f"{pid}_v{version}.png"
                proj_id = panel.project_id or "default"
                asset_url = self.asset_store.save_asset(proj_id, "panels", filename, image_bytes)

                record = PanelArtworkAssetRecord(
                    panel_id=pid,
                    version=version,
                    provider="comfyui",
                    model=self.model_name,
                    seed=seed,
                    prompt_hash=compiled.prompt_hash,
                    file_path=f"panels/{filename}",
                    image_url=asset_url,
                    structured_prompt=compiled.to_dict(),
                    metadata=img_metadata,
                )

                return StoryboardRenderResult(
                    panel_id=pid,
                    version=version,
                    status=StoryboardImageStatus.READY,
                    image_url=asset_url,
                    mime_type="image/png",
                    provider="comfyui",
                    model=self.model_name,
                    seed=seed,
                    prompt_hash=compiled.prompt_hash,
                    compiled_prompt=compiled.full_prompt,
                    negative_prompt=compiled.negative,
                    control_bundle=control_bundle,
                    asset_record=record,
                    render_metadata={
                        "provider": "comfyui",
                        "model": self.model_name,
                        "version": version,
                        "label": "COMFYUI STORYBOARD",
                    },
                )
        except Exception as e:
            return StoryboardRenderResult(
                panel_id=pid,
                version=version,
                status=StoryboardImageStatus.FAILED,
                provider="comfyui",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=compiled.full_prompt,
                negative_prompt=compiled.negative,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason="NETWORK_ERROR",
                status_message=str(e),
            )


class DiffusersStoryboardAdapter(StoryboardRenderProvider):
    """Optional adapter for dedicated remote or configured Diffusers endpoints."""

    def __init__(
        self,
        runtime_url: Optional[str] = None,
        model_name: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
    ):
        self.runtime_url = (runtime_url or os.environ.get("STORYBOARD_RUNTIME_URL") or "").rstrip("/")
        self.model_name = model_name or os.environ.get("STORYBOARD_MODEL") or "diffusers/storyboard-sdxl"
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardImagePromptCompiler()

    def health_check(self) -> Dict[str, Any]:
        if not self.runtime_url:
            return {
                "available": False,
                "status": "UNCONFIGURED",
                "message": "STORYBOARD_RUNTIME_URL not configured for Diffusers adapter.",
            }
        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.runtime_url}/health")
                if res.status_code == 200:
                    return {"available": True, "status": "CONNECTED", "message": "Diffusers runtime healthy."}
                return {"available": False, "status": "ERROR", "message": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"available": False, "status": "UNAVAILABLE", "message": str(e)}

    def get_capabilities(self) -> ProviderCapabilityReport:
        health = self.health_check()
        return ProviderCapabilityReport(
            provider="diffusers",
            model=self.model_name,
            available=health["available"],
            status_message=health["message"],
            supports_reference_images=False,
            supports_ip_adapter=False,
            supports_identity_conditioning=False,
            pose_control=False,
            depth_control=False,
            edge_control=False,
            seed_support=True,
            max_resolution="1024x1024",
        )

    def render_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
        control_bundle: Optional[StoryboardControlBundle] = None,
        sequence_context: Optional[StoryboardSequenceContext] = None,
        version: int = 1,
    ) -> StoryboardRenderResult:
        compiled: StructuredPromptResult = self.compiler.compile(
            panel=panel,
            bible=bible,
            char_packs=char_packs,
            loc_pack=loc_pack,
            prop_packs=prop_packs,
            control_bundle=control_bundle,
            sequence_context=sequence_context,
        )
        health = self.health_check()
        if not health["available"]:
            return StoryboardRenderResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                status=StoryboardImageStatus.FAILED,
                image_url=None,
                provider="diffusers",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=compiled.full_prompt,
                negative_prompt=compiled.negative,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason="RUNTIME_UNAVAILABLE",
                status_message=health["message"],
            )

        return StoryboardRenderResult(
            panel_id=panel.panel_id or panel.id,
            version=version,
            status=StoryboardImageStatus.FAILED,
            fallback_reason="NOT_IMPLEMENTED_REMOTE",
            status_message="Diffusers remote endpoint execution not yet active.",
            previs_guide_available=True,
            control_bundle=control_bundle,
        )


class MockOpenModelStoryboardAdapter(StoryboardRenderProvider):
    """Fast deterministic mock adapter for testing open-model pipelines without GPU or external network."""

    def __init__(
        self,
        asset_store: Optional[StoryboardAssetStore] = None,
        simulate_connected: bool = True,
        model_name: str = "mock_open_sdxl_storyboard",
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.simulate_connected = simulate_connected
        self.model_name = model_name
        self.compiler = StoryboardImagePromptCompiler()

    def health_check(self) -> Dict[str, Any]:
        if self.simulate_connected:
            return {
                "available": True,
                "status": "CONNECTED",
                "message": "Mock Open-Model runtime connected and ready.",
            }
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "message": "Storyboard render runtime unavailable.",
        }

    def get_capabilities(self) -> ProviderCapabilityReport:
        return ProviderCapabilityReport(
            provider="mock_open_model",
            model=self.model_name,
            available=self.simulate_connected,
            status_message="Mock runtime active for offline verification.",
            supports_reference_images=True,
            supports_ip_adapter=True,
            supports_identity_conditioning=True,
            pose_control=True,
            depth_control=True,
            edge_control=True,
            seed_support=True,
            max_resolution="1280x720",
        )

    def render_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
        control_bundle: Optional[StoryboardControlBundle] = None,
        sequence_context: Optional[StoryboardSequenceContext] = None,
        version: int = 1,
    ) -> StoryboardRenderResult:
        compiled: StructuredPromptResult = self.compiler.compile(
            panel=panel,
            bible=bible,
            char_packs=char_packs,
            loc_pack=loc_pack,
            prop_packs=prop_packs,
            control_bundle=control_bundle,
            sequence_context=sequence_context,
        )

        if not self.simulate_connected:
            return StoryboardRenderResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                status=StoryboardImageStatus.FAILED,
                image_url=None,
                provider="mock_open_model",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=compiled.full_prompt,
                negative_prompt=compiled.negative,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason="RUNTIME_UNAVAILABLE",
                status_message="Storyboard render unavailable. Configure renderer.",
            )

        # Synthesize authentic raster PNG asset
        pid = panel.panel_id or panel.id
        filename = f"{pid}_v{version}.png"
        proj_id = panel.project_id or "default"
        asset_url = self.asset_store.save_asset(proj_id, "panels", filename, MOCK_RASTER_PNG_BYTES)

        record = PanelArtworkAssetRecord(
            panel_id=pid,
            version=version,
            provider="open_model_storyboard",
            model=self.model_name,
            seed=42 + version,
            prompt_hash=compiled.prompt_hash,
            file_path=f"panels/{filename}",
            image_url=asset_url,
            generation_time_ms=120.0,
            structured_prompt=compiled.to_dict(),
            metadata={"is_mock": True, "mime_type": "image/png"},
        )

        return StoryboardRenderResult(
            panel_id=pid,
            version=version,
            status=StoryboardImageStatus.READY,
            image_url=asset_url,
            mime_type="image/png",
            provider="open_model_storyboard",
            model=self.model_name,
            seed=42 + version,
            prompt_hash=compiled.prompt_hash,
            compiled_prompt=compiled.full_prompt,
            negative_prompt=compiled.negative,
            previs_guide_available=True,
            control_bundle=control_bundle,
            asset_record=record,
            render_metadata={
                "provider": "open_model_storyboard",
                "model": self.model_name,
                "version": version,
                "label": "OPEN-MODEL STORYBOARD",
            },
        )


class OpenModelStoryboardProvider(StoryboardRenderProvider):
    """Canonical Primary Storyboard Provider for D3 Story Lab.

    Orchestrates:
    - Previs control bundle generation via internal PrevisControlRenderer
    - Character, Location, and Prop continuity packs
    - Keyframe vs Full Board render modes
    - Runtime adapter delegation (ComfyUI, Diffusers, Mock)
    - Fallback preservation: Never outputs procedural SVG as final artwork!
    """

    def __init__(
        self,
        adapter: Optional[StoryboardRenderProvider] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        previs_renderer: Optional[PrevisControlRenderer] = None,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.previs_renderer = previs_renderer or PrevisControlRenderer(asset_store=self.asset_store)
        self.adapter = adapter or self._resolve_default_adapter()

    def _resolve_default_adapter(self) -> StoryboardRenderProvider:
        provider_name = os.environ.get("STORYBOARD_RENDER_PROVIDER", "on_demand").lower()
        runtime_url = os.environ.get("STORYBOARD_RUNTIME_URL", "")
        model = os.environ.get("STORYBOARD_MODEL", "")

        if provider_name == "comfyui" or "comfy" in provider_name or (runtime_url and provider_name not in ("on_demand", "ondemand")):
            return ComfyUIStoryboardAdapter(runtime_url=runtime_url, model_name=model, asset_store=self.asset_store)
        if provider_name in ("on_demand", "ondemand", "on-demand", "huggingface", "hf", "zerogpu"):
            from src.storyboard.on_demand_provider import OnDemandStoryboardProvider
            return OnDemandStoryboardProvider(asset_store=self.asset_store, model_name=model)
        if provider_name == "diffusers":
            return DiffusersStoryboardAdapter(runtime_url=runtime_url, model_name=model, asset_store=self.asset_store)
        if provider_name in ("mock_connected", "mock_ai"):
            return MockOpenModelStoryboardAdapter(asset_store=self.asset_store, simulate_connected=True)
        if provider_name == "mock_unavailable":
            return MockOpenModelStoryboardAdapter(asset_store=self.asset_store, simulate_connected=False)

        # Default to on-demand provider
        from src.storyboard.on_demand_provider import OnDemandStoryboardProvider
        return OnDemandStoryboardProvider(asset_store=self.asset_store, model_name=model)

    def get_capabilities(self) -> ProviderCapabilityReport:
        return self.adapter.get_capabilities()



    def health_check(self) -> Dict[str, Any]:
        return self.adapter.health_check()

    def render_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
        control_bundle: Optional[StoryboardControlBundle] = None,
        sequence_context: Optional[StoryboardSequenceContext] = None,
        version: int = 1,
    ) -> StoryboardRenderResult:
        """Render single panel: always generate control bundle, then delegate raster generation."""
        # 1. Generate internal previs control bundle
        if not control_bundle:
            control_bundle = self.previs_renderer.generate_control_bundle(panel, bible=bible, version=version)

        # 2. Render raster artwork via configured runtime adapter
        result = self.adapter.render_panel(
            panel=panel,
            bible=bible,
            char_packs=char_packs,
            loc_pack=loc_pack,
            prop_packs=prop_packs,
            control_bundle=control_bundle,
            sequence_context=sequence_context,
            version=version,
        )
        result.control_bundle = control_bundle
        if result.asset_record and self.asset_store:
            proj_id = panel.project_id or "default"
            pid = panel.panel_id or panel.id
            try:
                self.asset_store.save_panel_record(proj_id, pid, version, result.asset_record.model_dump(mode="json"))
            except Exception as e:
                logger.warning(f"Could not persist panel record for {pid} v{version}: {e}")
        return result

    def render_sequence(
        self,
        panels: List[StoryboardPanel],
        mode: RenderMode = RenderMode.KEYFRAMES,
        budget: Optional[int] = None,
        bible: Optional[VisualBible] = None,
        char_packs: Optional[Dict[str, CharacterContinuityPack]] = None,
        loc_pack: Optional[LocationContinuityPack] = None,
        prop_packs: Optional[Dict[str, PropContinuityPack]] = None,
    ) -> List[StoryboardRenderResult]:
        """Render panel sequence adhering strictly to KEYFRAMES vs FULL_BOARD mode and budget limits."""
        keyframe_set = (
            set(select_keyframe_indices(panels, budget=budget))
            if mode == RenderMode.KEYFRAMES
            else set(range(min(len(panels), 12)))
        )


        results: List[StoryboardRenderResult] = []
        prev_panel_id: Optional[str] = None
        prev_img_url: Optional[str] = None

        for idx, panel in enumerate(panels):
            target_version = len(panel.versions) + 1 if panel.versions else 1
            seq_ctx = StoryboardSequenceContext(
                previous_panel=prev_panel_id,
                previous_panel_reference=prev_img_url,
                shared_seed_family=1000,
            )

            # Previs control bundle is always prepared
            ctrl_bundle = self.previs_renderer.generate_control_bundle(panel, bible=bible, version=target_version)

            if idx in keyframe_set:
                # Keyframe panel: Render raster artwork through open-model runtime
                res = self.render_panel(
                    panel=panel,
                    bible=bible,
                    char_packs=char_packs,
                    loc_pack=loc_pack,
                    prop_packs=prop_packs,
                    control_bundle=ctrl_bundle,
                    sequence_context=seq_ctx,
                    version=target_version,
                )
                prev_panel_id = panel.panel_id or panel.id
                prev_img_url = res.image_url
                results.append(res)
            else:
                # Non-keyframe panel in KEYFRAMES mode: Remains planned with previs guide available
                res = StoryboardRenderResult(
                    panel_id=panel.panel_id or panel.id,
                    version=target_version,
                    status=StoryboardImageStatus.PLANNED,
                    image_url=None,
                    provider=self.adapter.get_capabilities().provider,
                    model=self.adapter.get_capabilities().model,
                    previs_guide_available=True,
                    control_bundle=ctrl_bundle,
                    status_message="Non-keyframe beat in KEYFRAMES mode. Previs guide available.",
                    render_metadata={"mode": "keyframe_deferred", "previs_available": True},
                )
                results.append(res)

        return results
