"""On-Demand Storyboard Image Provider.

Provides lightweight, low-cost or zero-cost still image generation for storyboard keyframes:
- Single request execution: submit, wait, download, persist to StoryboardAssetStore, release
- Requires no permanently running GPU or long-lived daemon
- Server-side credential management: supports Hugging Face / ZeroGPU without leaking client tokens
- Guarantees STILL IMAGES ONLY: PNG, JPEG, WebP. Prohibits all video/animation outputs
- Clear quota messaging: 'Free/limited provider availability depends on current quota.'
- Quota fallback: gracefully returns 'Image generation quota unavailable.' without breaking screenplay
- Persists all outputs to disk so subsequent views require no GPU
- Model and provider verification with honest status codes: READY, QUOTA_UNAVAILABLE, MODEL_UNAVAILABLE, AUTH_FAILED, RATE_LIMITED, TIMEOUT, PROVIDER_ERROR, INVALID_IMAGE
"""

from __future__ import annotations
import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel

from src.storyboard.models import StoryboardPanel, StoryboardImageStatus
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.provider_base import (
    StoryboardRenderProvider,
    ProviderCapabilityReport,
    StoryboardRenderResult,
    PanelArtworkAssetRecord,
)
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
)
from src.storyboard.control import StoryboardControlBundle
from src.storyboard.visual_bible import VisualBible
from src.storyboard.prompt_compiler import (
    StoryboardImagePromptCompiler,
    StructuredPromptResult,
)

logger = logging.getLogger("d3.storyboard.on_demand")


def _load_env_fallback():
    """Load missing env vars from backend/.env if available (except during automated tests)."""
    if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("USE_MOCK_LLM") == "1":
        return
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    # search upwards for backend/.env
    for _ in range(4):
        env_path = os.path.join(cur_dir, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break
        parent = os.path.dirname(cur_dir)
        if parent == cur_dir:
            break
        cur_dir = parent


_load_env_fallback()

# Mandatory high-quality prompt style target
ON_DEMAND_STORYBOARD_STYLE = (
    "professional film storyboard, graphite and charcoal sketch, semi-realistic anatomy, "
    "cinematic composition, strong lighting, production-board drawing, detailed environment, "
    "consistent characters, grayscale, rough cross-hatching"
)

ON_DEMAND_NEGATIVE_PROMPT = (
    "dialogue text, subtitles, captions, speech bubbles, word balloons, watermark, logo, signature, "
    "shot labels, frame numbers, letters, words, font, photorealism, 3d render, cgi, anime, cartoon, "
    "video, animation, motion blur, animated gif, mp4, glossy digital painting, smooth plastic skin, "
    "deformed hands, extra fingers, missing fingers, distorted anatomy, broken perspective, blurry, low resolution"
)

QUOTA_UNAVAILABLE_MESSAGE = "Image generation quota unavailable."
PRICING_QUOTA_DISCLAIMER = "Free/limited provider availability depends on current quota."
MODEL_UNAVAILABLE_MESSAGE = "Configured storyboard model is not currently available through this provider."


def validate_still_image(bytes_data: bytes) -> Tuple[str, str]:
    """Validate that data is strictly a supported still image (PNG, JPEG, WebP).
    
    Raises ValueError if data is invalid or indicates video/animation.
    """
    if not bytes_data or len(bytes_data) < 8:
        raise ValueError("Invalid image payload: payload is empty or too short.")

    # 1. PNG check (8-byte magic header)
    if bytes_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"

    # 2. JPEG check (SOI marker 0xFFD8)
    if bytes_data.startswith(b"\xff\xd8"):
        return "image/jpeg", "jpg"

    # 3. WebP check (RIFF....WEBP)
    if bytes_data.startswith(b"RIFF") and len(bytes_data) > 12 and bytes_data[8:12] == b"WEBP":
        return "image/webp", "webp"

    # Prohibit video, animated gif, or unknown formats
    if bytes_data.startswith(b"GIF8") or b"ftyp" in bytes_data[:32]:
        raise ValueError("Animation and video outputs are strictly prohibited in D3 Story Lab.")

    raise ValueError("Unsupported image format: only still images (PNG, JPEG, WebP) are allowed.")


class OnDemandStoryboardProvider(StoryboardRenderProvider):
    """On-demand ephemeral image generator for storyboard keyframes."""

    # Module-level cache for model route probe results (url -> (timestamp, is_compatible, status_code, message))
    _probe_cache: Dict[str, Tuple[float, bool, str, str]] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model_name: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        timeout: float = 60.0,
    ):
        _load_env_fallback()
        self.api_key = (
            api_key
            if api_key is not None
            else (
                os.environ.get("ON_DEMAND_API_KEY")
                or os.environ.get("HF_TOKEN")
                or os.environ.get("HUGGINGFACE_API_KEY")
                or ""
            )
        )
        self.model_name = (
            model_name
            or os.environ.get("ON_DEMAND_MODEL")
            or os.environ.get("HF_MODEL")
            or "stabilityai/stable-diffusion-3-medium-diffusers"
        )
        self.api_url = (
            api_url
            or os.environ.get("ON_DEMAND_API_URL")
            or f"https://router.huggingface.co/hf-inference/models/{self.model_name}"
        )
        self.asset_store = asset_store or StoryboardAssetStore()
        self.timeout = timeout
        self.compiler = StoryboardImagePromptCompiler()

    def verify_model_compatibility(self, force: bool = False) -> Tuple[bool, str, str]:
        """Probe model availability through the configured inference path.
        
        Distinguishes:
        - READY
        - QUOTA_UNAVAILABLE
        - MODEL_UNAVAILABLE
        - AUTH_FAILED
        - RATE_LIMITED
        - TIMEOUT
        - PROVIDER_ERROR
        
        Returns: (is_compatible, status_code, human_message)
        """
        if not self.api_key:
            return False, "QUOTA_UNAVAILABLE", "No on-demand API token configured on server (HF_TOKEN / ON_DEMAND_API_KEY)."

        cache_key = f"{self.api_url}:{self.api_key[:6]}"
        now = time.time()
        if not force and cache_key in self._probe_cache:
            cached_time, is_compat, status_code, msg = self._probe_cache[cache_key]
            if now - cached_time < 60.0:  # 60 second cache TTL
                return is_compat, status_code, msg

        # Probe model route
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "D3StoryLab/1.0",
            }
            # Send a fast lightweight GET probe to verify model route
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    self.api_url,
                    headers=headers,
                )
                if resp.status_code == 200:
                    result = (True, "READY", f"On-demand model ready ({self.model_name}). {PRICING_QUOTA_DISCLAIMER}")
                elif resp.status_code in (401, 403):
                    result = (False, "AUTH_FAILED", "Invalid or unauthorized Hugging Face token. Please verify your HF_TOKEN.")
                elif resp.status_code in (404, 410, 400):
                    result = (False, "MODEL_UNAVAILABLE", MODEL_UNAVAILABLE_MESSAGE)
                elif resp.status_code == 429:
                    result = (False, "RATE_LIMITED", "On-demand rate limit reached. Please try again shortly.")
                elif resp.status_code == 402:
                    result = (False, "QUOTA_UNAVAILABLE", QUOTA_UNAVAILABLE_MESSAGE)
                elif resp.status_code in (503, 504):
                    result = (True, "READY", f"On-demand model warming up ({self.model_name}).")
                else:
                    result = (False, "PROVIDER_ERROR", f"Provider returned HTTP {resp.status_code}.")

            self._probe_cache[cache_key] = (now, result[0], result[1], result[2])
            return result
        except Exception as e:
            logger.warning(f"On-demand route probe failed for {self.api_url}: {e}")
            result = (False, "TIMEOUT", f"Connection to model provider timed out or failed: {e}")
            self._probe_cache[cache_key] = (now, result[0], result[1], result[2])
            return result

    def health_check(self, probe: Optional[bool] = None) -> Dict[str, Any]:
        """Verify on-demand provider availability and model route compatibility without exposing secrets."""
        _load_env_fallback()
        if not self.api_key:
            return {
                "available": False,
                "status": "QUOTA_UNAVAILABLE",
                "provider_status": "NOT_CONFIGURED",
                "model_status": "UNCHECKED",
                "message": QUOTA_UNAVAILABLE_MESSAGE,
                "details": "No on-demand API token configured on server (HF_TOKEN / ON_DEMAND_API_KEY).",
                "model": self.model_name,
            }

        provider_status = "CONNECTED"

        if probe is None:
            # Auto-probe unless running inside automated offline unit test suite
            probe = "PYTEST_CURRENT_TEST" not in os.environ and os.environ.get("USE_MOCK_LLM") != "1"

        if probe:
            is_compat, status_code, message = self.verify_model_compatibility(force=False)
            model_status = "AVAILABLE" if is_compat else status_code
            if status_code == "AUTH_FAILED":
                provider_status = "AUTH_FAILED"
            elif status_code == "QUOTA_UNAVAILABLE":
                provider_status = "QUOTA_UNAVAILABLE"
            elif status_code == "RATE_LIMITED":
                provider_status = "RATE_LIMITED"
            elif status_code == "TIMEOUT":
                provider_status = "TIMEOUT"
            elif status_code == "PROVIDER_ERROR":
                provider_status = "PROVIDER_ERROR"
            else:
                provider_status = "CONNECTED"

            return {
                "available": is_compat,
                "status": status_code,
                "provider_status": provider_status,
                "model_status": model_status,
                "message": message,
                "details": f"Model: {self.model_name}, Endpoint: {self.api_url}",
                "model": self.model_name,
            }

        return {
            "available": True,
            "status": "READY",
            "provider_status": provider_status,
            "model_status": "AVAILABLE",
            "message": f"On-demand provider configured ({self.model_name}). {PRICING_QUOTA_DISCLAIMER}",
            "details": f"Model: {self.model_name}",
            "model": self.model_name,
        }

    def get_capabilities(self, probe: Optional[bool] = None) -> ProviderCapabilityReport:
        """Report on-demand capabilities conforming to the standard contract."""
        health = self.health_check(probe=probe)
        return ProviderCapabilityReport(
            provider="on_demand",
            model=self.model_name,
            available=health["available"],
            status=health["status"],
            status_message=health["message"],
            provider_status=health.get("provider_status", "NOT_CONFIGURED"),
            model_status=health.get("model_status", "AVAILABLE" if health["available"] else "UNCHECKED"),
            supports_reference_images=True,
            supports_ip_adapter=False,
            supports_identity_conditioning=True,
            pose_control=False,
            depth_control=False,
            edge_control=False,
            seed_support=True,
            max_resolution="1280x720",
            pricing_disclaimer=PRICING_QUOTA_DISCLAIMER,
        )

    def smoke_test(self, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Execute single-request smoke test to verify real image generation end-to-end.
        
        Persists generated still image to backend/data/projects/_smoke_test/storyboard/panels/storyboard_smoke_test.png (or .jpg).
        Reports exact status without Pillow or SVG faking.
        """
        test_prompt = prompt or "cinematic storyboard sketch, undercover detective holding a dossier in rain, graphite drawing"
        full_prompt = f"{test_prompt}, {ON_DEMAND_STORYBOARD_STYLE}"
        negative_prompt = ON_DEMAND_NEGATIVE_PROMPT

        if not self.api_key:
            return {
                "success": False,
                "status": "QUOTA_UNAVAILABLE",
                "message": "No on-demand API token configured (HF_TOKEN / ON_DEMAND_API_KEY).",
                "model": self.model_name,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "D3StoryLab/1.0",
        }
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "seed": 42,
            },
        }

        try:
            import httpx
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(self.api_url, json=payload, headers=headers)

                if resp.status_code == 200:
                    raw_bytes = resp.content
                    mime_type, ext = validate_still_image(raw_bytes)

                    # Determine target persistence path
                    base_data_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "data",
                    )
                    smoke_dir = os.path.join(base_data_dir, "projects", "_smoke_test", "storyboard", "panels")
                    os.makedirs(smoke_dir, exist_ok=True)
                    out_path = os.path.join(smoke_dir, f"storyboard_smoke_test.{ext}")
                    with open(out_path, "wb") as f:
                        f.write(raw_bytes)

                    file_size = os.path.getsize(out_path)
                    if file_size < 1024:
                        return {
                            "success": False,
                            "status": "INVALID_IMAGE",
                            "message": f"Generated image file is unexpectedly small ({file_size} bytes).",
                            "model": self.model_name,
                        }

                    return {
                        "success": True,
                        "status": "READY",
                        "message": f"Smoke test succeeded. Generated {file_size} bytes still image.",
                        "file_path": out_path,
                        "image_url": f"/api/projects/_smoke_test/storyboard/assets/panels/storyboard_smoke_test.{ext}",
                        "size_bytes": file_size,
                        "mime_type": mime_type,
                        "model": self.model_name,
                    }

                elif resp.status_code in (401, 403):
                    return {
                        "success": False,
                        "status": "AUTH_FAILED",
                        "message": "Invalid or unauthorized Hugging Face token.",
                        "model": self.model_name,
                    }
                elif resp.status_code in (404, 410, 400):
                    return {
                        "success": False,
                        "status": "MODEL_UNAVAILABLE",
                        "message": MODEL_UNAVAILABLE_MESSAGE,
                        "model": self.model_name,
                    }
                elif resp.status_code == 429:
                    return {
                        "success": False,
                        "status": "RATE_LIMITED",
                        "message": "Rate limited by provider.",
                        "model": self.model_name,
                    }
                elif resp.status_code == 402:
                    return {
                        "success": False,
                        "status": "QUOTA_UNAVAILABLE",
                        "message": QUOTA_UNAVAILABLE_MESSAGE,
                        "model": self.model_name,
                    }
                else:
                    return {
                        "success": False,
                        "status": "PROVIDER_ERROR",
                        "message": f"Provider HTTP error {resp.status_code}.",
                        "model": self.model_name,
                    }
        except Exception as e:
            return {
                "success": False,
                "status": "TIMEOUT",
                "message": f"Smoke test network error: {e}",
                "model": self.model_name,
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
        """Execute single on-demand still image generation request."""
        # 1. Compile structured prompt using D3 continuity packs
        compiled: StructuredPromptResult = self.compiler.compile(
            panel=panel,
            bible=bible,
            char_packs=char_packs,
            loc_pack=loc_pack,
            prop_packs=prop_packs,
            control_bundle=control_bundle,
            sequence_context=sequence_context,
        )

        # Inject mandatory film storyboard target style
        full_prompt = f"{compiled.full_prompt}, {ON_DEMAND_STORYBOARD_STYLE}"
        negative_prompt = f"{compiled.negative}, {ON_DEMAND_NEGATIVE_PROMPT}"

        pid = panel.panel_id or panel.id
        seed = 42 + version

        # 2. Verify token presence
        if not self.api_key:
            return StoryboardRenderResult(
                panel_id=pid,
                version=version,
                status=StoryboardImageStatus.FAILED,
                image_url=None,
                provider="on_demand",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=full_prompt,
                negative_prompt=negative_prompt,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason="QUOTA_UNAVAILABLE",
                status_message=QUOTA_UNAVAILABLE_MESSAGE,
            )

        # 3. Submit single request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "D3StoryLab/1.0",
        }
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "seed": seed,
            },
        }

        try:
            import httpx
            max_retries = 2
            raw_bytes: Optional[bytes] = None

            for attempt in range(max_retries + 1):
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(self.api_url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        raw_bytes = resp.content
                        break

                    # 401 / 403 Invalid or unauthorized token
                    if resp.status_code in (401, 403):
                        return StoryboardRenderResult(
                            panel_id=pid,
                            version=version,
                            status=StoryboardImageStatus.FAILED,
                            provider="on_demand",
                            model=self.model_name,
                            prompt_hash=compiled.prompt_hash,
                            compiled_prompt=full_prompt,
                            negative_prompt=negative_prompt,
                            previs_guide_available=True,
                            control_bundle=control_bundle,
                            fallback_reason="INVALID_CREDENTIALS",
                            status_message="Invalid or unauthorized Hugging Face token. Please verify your HF_TOKEN.",
                        )

                    # 410 / 404 / 400 Model deprecated or not supported by provider
                    if resp.status_code in (410, 404, 400):
                        return StoryboardRenderResult(
                            panel_id=pid,
                            version=version,
                            status=StoryboardImageStatus.FAILED,
                            provider="on_demand",
                            model=self.model_name,
                            prompt_hash=compiled.prompt_hash,
                            compiled_prompt=full_prompt,
                            negative_prompt=negative_prompt,
                            previs_guide_available=True,
                            control_bundle=control_bundle,
                            fallback_reason="MODEL_UNAVAILABLE",
                            status_message=MODEL_UNAVAILABLE_MESSAGE,
                        )

                    # 429 Rate Limit / Quota Exceeded
                    if resp.status_code == 429:
                        return StoryboardRenderResult(
                            panel_id=pid,
                            version=version,
                            status=StoryboardImageStatus.FAILED,
                            provider="on_demand",
                            model=self.model_name,
                            prompt_hash=compiled.prompt_hash,
                            compiled_prompt=full_prompt,
                            negative_prompt=negative_prompt,
                            previs_guide_available=True,
                            control_bundle=control_bundle,
                            fallback_reason="QUOTA_UNAVAILABLE",
                            status_message=QUOTA_UNAVAILABLE_MESSAGE,
                        )

                    # 402 Quota / Payment Required
                    if resp.status_code == 402:
                        return StoryboardRenderResult(
                            panel_id=pid,
                            version=version,
                            status=StoryboardImageStatus.FAILED,
                            provider="on_demand",
                            model=self.model_name,
                            prompt_hash=compiled.prompt_hash,
                            compiled_prompt=full_prompt,
                            negative_prompt=negative_prompt,
                            previs_guide_available=True,
                            control_bundle=control_bundle,
                            fallback_reason="QUOTA_UNAVAILABLE",
                            status_message=QUOTA_UNAVAILABLE_MESSAGE,
                        )

                    # 503 / 504 Model Warming up -> brief pause and retry
                    if resp.status_code in (503, 504) and attempt < max_retries:
                        time.sleep(3.0)
                        continue

                    # Other HTTP error
                    return StoryboardRenderResult(
                        panel_id=pid,
                        version=version,
                        status=StoryboardImageStatus.FAILED,
                        provider="on_demand",
                        model=self.model_name,
                        prompt_hash=compiled.prompt_hash,
                        compiled_prompt=full_prompt,
                        negative_prompt=negative_prompt,
                        previs_guide_available=True,
                        control_bundle=control_bundle,
                        fallback_reason="PROVIDER_ERROR",
                        status_message=f"On-demand request failed (HTTP {resp.status_code}).",
                    )

            if not raw_bytes:
                return StoryboardRenderResult(
                    panel_id=pid,
                    version=version,
                    status=StoryboardImageStatus.FAILED,
                    provider="on_demand",
                    model=self.model_name,
                    prompt_hash=compiled.prompt_hash,
                    compiled_prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    previs_guide_available=True,
                    control_bundle=control_bundle,
                    fallback_reason="TIMEOUT",
                    status_message="On-demand generation timed out.",
                )

            # 4. Strictly validate STILL IMAGE format (PNG, JPEG, WebP)
            try:
                mime_type, file_ext = validate_still_image(raw_bytes)
            except ValueError as ve:
                return StoryboardRenderResult(
                    panel_id=pid,
                    version=version,
                    status=StoryboardImageStatus.FAILED,
                    provider="on_demand",
                    model=self.model_name,
                    prompt_hash=compiled.prompt_hash,
                    compiled_prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    previs_guide_available=True,
                    control_bundle=control_bundle,
                    fallback_reason="INVALID_IMAGE",
                    status_message=str(ve),
                )

            # 5. Persist image to disk in StoryboardAssetStore
            filename = f"{pid}_v{version}.{file_ext}"
            proj_id = panel.project_id or "default"
            asset_url = self.asset_store.save_asset(proj_id, "panels", filename, raw_bytes)

            record = PanelArtworkAssetRecord(
                panel_id=pid,
                version=version,
                provider="on_demand",
                model=self.model_name,
                seed=seed,
                prompt_hash=compiled.prompt_hash,
                file_path=f"panels/{filename}",
                image_url=asset_url,
                mime_type=mime_type,
                structured_prompt=compiled.to_dict(),
                metadata={"provider_type": "on_demand", "disclaimer": PRICING_QUOTA_DISCLAIMER},
            )

            # 6. Return successful render result
            return StoryboardRenderResult(
                panel_id=pid,
                version=version,
                status=StoryboardImageStatus.READY,
                image_url=asset_url,
                mime_type=mime_type,
                provider="on_demand",
                model=self.model_name,
                seed=seed,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=full_prompt,
                negative_prompt=negative_prompt,
                control_bundle=control_bundle,
                asset_record=record,
                render_metadata={
                    "provider": "on_demand",
                    "model": self.model_name,
                    "version": version,
                    "label": "ON-DEMAND STORYBOARD",
                    "pricing_disclaimer": PRICING_QUOTA_DISCLAIMER,
                },
            )

        except Exception as e:
            logger.warning(f"On-demand render error on panel {pid}: {e}")
            return StoryboardRenderResult(
                panel_id=pid,
                version=version,
                status=StoryboardImageStatus.FAILED,
                provider="on_demand",
                model=self.model_name,
                prompt_hash=compiled.prompt_hash,
                compiled_prompt=full_prompt,
                negative_prompt=negative_prompt,
                previs_guide_available=True,
                control_bundle=control_bundle,
                fallback_reason="TIMEOUT",
                status_message=str(e),
            )
