"""Storyboard Image Provider Abstraction and Concrete Engines.

Provides provider-independent image generation supporting:
1. Cloud AI Image Generation (Google Imagen / Gemini)
2. High-fidelity Procedural Comic/Graphic Novel Illustration Fallback
3. Deterministic Mock Provider for offline testing and rapid development
"""

from __future__ import annotations
import os
import json
import logging
import base64
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import (
    StoryboardPanel,
    StoryboardImageStatus,
    StoryboardImageVersion,
)
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.provider import ComicGraphicStoryboardProvider
from src.providers.budget import BudgetGovernor, BudgetExceededError, ContentHashCache

logger = logging.getLogger(__name__)

def _load_env_file() -> None:
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        "/workspaces/d3-story-lab/backend/.env",
        "/workspaces/d3-story-lab/.env",
        ".env",
    ]
    for p in candidate_paths:
        p_abs = os.path.abspath(p)
        if os.path.exists(p_abs):
            try:
                with open(p_abs, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()


class ProviderState(str, Enum):
    """Runtime availability state of an image provider."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_ERROR = "AUTH_ERROR"
    QUOTA_ERROR = "QUOTA_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


class FallbackReason(str, Enum):
    """Explains why AI generation fell back to the procedural comic engine."""
    NO_API_KEY = "NO_API_KEY"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    UNSUPPORTED_MODEL = "UNSUPPORTED_MODEL"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    REQUEST_FAILED = "REQUEST_FAILED"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class StoryboardImageResult(BaseModel):
    """Normalized result returned by any storyboard image provider."""
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    version: int = 1
    image_url: str = ""
    svg_content: Optional[str] = None
    provider: str = "comic_procedural"
    mode: str = "fallback_comic"  # "ai_image" | "fallback_comic"
    compiled_prompt: str = ""
    negative_prompt: str = ""
    status: StoryboardImageStatus = StoryboardImageStatus.READY
    fallback_reason: Optional[str] = None
    provider_status: Optional[str] = None
    continuity_mode: str = "TEXTUAL CONTINUITY ONLY"
    mime_type: str = "image/svg+xml"
    render_metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryboardImageProvider(ABC):
    """Abstract interface for rendering storyboard panel images."""

    @abstractmethod
    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        """Generate artwork for a panel and return normalized StoryboardImageResult."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return provider runtime status and diagnostics without exposing secrets."""
        pass

    def render_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper returning dictionary matching API schema."""
        res = self.generate_panel(panel, bible=bible, version=version)
        data = {
            "panel_id": res.panel_id,
            "scene_number": panel.scene_number,
            "shot_number": panel.shot_number,
            "page_number": panel.page_number,
            "shot_type": panel.shot_type.value,
            "camera_angle": panel.camera_angle.value,
            "image_url": res.image_url,
            "rendered_svg": res.svg_content,
            "render_type": "ai_image" if res.mode == "ai_image" else "svg_graphic",
            "provider": res.provider,
            "mode": res.mode,
            "status": res.status.value,
            "fallback_reason": res.fallback_reason,
            "provider_status": res.provider_status,
            "continuity_mode": res.continuity_mode,
            "mime_type": res.mime_type,
            "version": res.version,
            "prompt_used": res.compiled_prompt,
            "negative_prompt": res.negative_prompt,
            "caption": panel.caption,
            "metadata": res.render_metadata,
        }
        return data


class CachedStoryboardImageProvider(StoryboardImageProvider):
    """Wraps any StoryboardImageProvider with ContentHashCache and BudgetGovernor.
    - Key = SHA-256 hash of (shot prompt + visual style prompt + character visual anchor descriptions + aspect ratio)
    - If key exists in cache, return cached image, do not call image provider, do not bill against budget.
    - If budget limit reached, raises BudgetExceededError.
    """

    def __init__(
        self,
        provider: StoryboardImageProvider,
        cache: Optional[ContentHashCache] = None,
        budget_governor: Optional[BudgetGovernor] = None,
    ):
        self.provider = provider
        self.cache = cache if cache is not None else ContentHashCache()
        self.budget_governor = budget_governor

    def get_status(self) -> Dict[str, Any]:
        status = self.provider.get_status()
        status["cache_size"] = self.cache.size
        if self.budget_governor:
            status["budget"] = self.budget_governor.get_summary()
        return status

    def compute_cache_key(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
    ) -> str:
        shot_prompt = panel.compiled_prompt or panel.image_prompt or panel.prompt
        style_prompt = getattr(bible, "style_prompt", "") if bible else ""
        anchors = ""
        if bible and hasattr(bible, "characters") and bible.characters:
            anchors = "|".join(
                f"{k}:{getattr(v, 'visual_summary', str(v))}"
                for k, v in sorted(bible.characters.items())
            )
        return ContentHashCache.compute_hash(
            shot_prompt=shot_prompt,
            visual_style_prompt=style_prompt,
            character_visual_anchors=anchors,
            aspect_ratio=panel.aspect_ratio or "16:9",
        )

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        cache_key = self.compute_cache_key(panel, bible)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            # Cache hit: Return cached image without calling provider or charging budget
            return cached_result

        # Check / charge budget
        if self.budget_governor:
            self.budget_governor.charge_panel()

        result = self.provider.generate_panel(panel, bible=bible, version=version)
        self.cache.set(cache_key, result)
        return result


class FallbackComicSvgProvider(StoryboardImageProvider):
    """High-fidelity procedural comic illustration engine serving as clean fallback.

    Outputs authentic inked noir comic artwork in SVG format with chiaroscuro lighting,
    silhouettes, and dynamic panels.
    """

    def __init__(self, asset_store: Optional[StoryboardAssetStore] = None):
        self.compiler = StoryboardPromptCompiler()
        self.engine = ComicGraphicStoryboardProvider()
        self.asset_store = asset_store or StoryboardAssetStore()

    def get_status(self) -> Dict[str, Any]:
        return {
            "storyboard_image_provider": "fallback_comic_svg",
            "mode": "fallback",
            "status": ProviderState.AVAILABLE.value,
            "available": True,
            "model": "procedural_vector_ink",
            "fallback_enabled": True,
            "fallback_reason": FallbackReason.PROVIDER_NOT_CONFIGURED.value,
            "continuity_mode": "TEXTUAL CONTINUITY ONLY",
            "supports_image_conditioning": False,
        }

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        # Render rich SVG from procedural comic engine
        render_dict = self.engine.render_panel(panel)
        svg_content = render_dict.get("svg_data") or render_dict.get("svg_content", "")

        # Save to asset store if project_id is available
        image_url = render_dict.get("image_url", "")
        if panel.project_id:
            try:
                filename = f"{panel.panel_id or panel.id}_v{version}.svg"
                image_url = self.asset_store.save_asset(
                    project_id=panel.project_id,
                    category="panels",
                    filename=filename,
                    content=svg_content,
                )
            except Exception as e:
                logger.warning(f"Could not persist panel asset to disk: {e}")

        fallback_reason = FallbackReason.NO_API_KEY.value

        return StoryboardImageResult(
            panel_id=panel.panel_id or panel.id,
            version=version,
            image_url=image_url,
            svg_content=svg_content,
            provider="fallback_comic_engine",
            mode="fallback_comic",
            compiled_prompt=compiled_prompt,
            negative_prompt=negative_prompt,
            status=StoryboardImageStatus.FALLBACK,
            fallback_reason=fallback_reason,
            provider_status=ProviderState.AVAILABLE.value,
            continuity_mode="TEXTUAL CONTINUITY ONLY",
            mime_type="image/svg+xml",
            render_metadata={
                "engine": "ComicGraphicStoryboardProvider",
                "is_fallback": True,
                "label": "FALLBACK COMIC",
                "fallback_reason": fallback_reason,
            },
        )


class ExternalStoryboardImageProvider(StoryboardImageProvider):
    """Abstract base class for external cloud and generative AI image providers.

    Guarantees:
    - Never exposes confidential API keys or access tokens in status or payloads
    - Standardizes the provider disclaimer for quotas and pricing
    - Preserves deterministic offline fallback
    """

    PRICING_DISCLAIMER: str = (
        "Optional external provider. Availability, quotas and pricing depend on the provider/account."
    )

    @abstractmethod
    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        """Generate panel using external service with graceful fallback."""
        pass


class CloudImagenStoryboardProvider(ExternalStoryboardImageProvider):
    """Cloud AI image generator using Google Gemini / Imagen API with transparent fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            if api_key is not None
            else (
                os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or os.environ.get("IMAGEN_API_KEY")
            )
        )
        self.model_name = (
            model_name
            or os.environ.get("STORYBOARD_IMAGE_MODEL")
            or "gemini-3.1-flash-image"
        )
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.fallback = FallbackComicSvgProvider(asset_store=self.asset_store)
        self._last_state: ProviderState = (
            ProviderState.AVAILABLE if self.api_key else ProviderState.UNAVAILABLE
        )
        self._last_fallback_reason: Optional[FallbackReason] = (
            None if self.api_key else FallbackReason.NO_API_KEY
        )
        self._quota_status: str = "UNCHECKED" if self.api_key else "NO_KEY"
        self._last_safe_message: Optional[str] = None
        self._last_error_details: Dict[str, Any] = {}

    def get_capabilities(self) -> Dict[str, Any]:
        """Expose image provider capabilities and model options without exposing secrets."""
        return {
            "provider": "google_imagen",
            "selected_model": self.model_name,
            "available": bool(self.api_key),
            "quota_status": self._quota_status,
            "last_error_category": (
                self._last_fallback_reason.value if self._last_fallback_reason else None
            ),
            "continuity_mode": "TEXTUAL CONTINUITY ONLY",
            "status_message": (
                self._last_safe_message
                or (
                    "Provider is ready for cloud image generation."
                    if self.api_key
                    else "No API key configured."
                )
            ),
            "supports_image_conditioning": False,
            "fallback_enabled": True,
        }

    def get_status(self) -> Dict[str, Any]:
        """Expose runtime state safely without revealing secrets."""
        caps = self.get_capabilities()
        caps["storyboard_image_provider"] = "google_imagen"
        caps["mode"] = "cloud"
        caps["status"] = self._last_state.value
        caps["model"] = self.model_name
        caps["fallback_reason"] = caps["last_error_category"]
        return caps

    def _detect_mime_and_ext(self, raw_bytes: bytes) -> Tuple[str, str]:
        """Detect raster MIME type and file extension from magic bytes."""
        if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png", "png"
        elif raw_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg", "jpg"
        elif raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:12]:
            return "image/webp", "webp"
        return "image/png", "png"

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        if not self.api_key:
            self._last_state = ProviderState.UNAVAILABLE
            self._last_fallback_reason = FallbackReason.NO_API_KEY
            self._quota_status = "NO_KEY"
            self._last_safe_message = "No Google API key configured for cloud image generation."
            res = self.fallback.generate_panel(panel, bible, version)
            res.fallback_reason = FallbackReason.NO_API_KEY.value
            res.provider_status = ProviderState.UNAVAILABLE.value
            res.render_metadata["fallback_reason"] = FallbackReason.NO_API_KEY.value
            res.render_metadata["provider_status"] = ProviderState.UNAVAILABLE.value
            res.render_metadata["status_message"] = self._last_safe_message
            res.render_metadata["model"] = self.model_name
            res.render_metadata["label"] = "FALLBACK COMIC"
            return res

        # Fast non-retrying circuit-breaker for quota exhaustion in this generation cycle
        if self._quota_status == "EXCEEDED":
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.fallback_reason = FallbackReason.QUOTA_EXCEEDED.value
            fallback_res.provider_status = ProviderState.QUOTA_ERROR.value
            fallback_res.render_metadata["fallback_reason"] = FallbackReason.QUOTA_EXCEEDED.value
            fallback_res.render_metadata["provider_status"] = ProviderState.QUOTA_ERROR.value
            fallback_res.render_metadata["status_message"] = self._last_safe_message
            fallback_res.render_metadata["quota_status"] = "EXCEEDED"
            fallback_res.render_metadata["model"] = self.model_name
            fallback_res.render_metadata["label"] = "FALLBACK COMIC"
            return fallback_res

        try:
            import httpx

            is_imagen_predict = self.model_name.startswith("imagen-")
            if is_imagen_predict:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:predict?key={self.api_key}"
                payload: Dict[str, Any] = {
                    "instances": [{"prompt": compiled_prompt}],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": "16:9",
                        "outputMimeType": "image/jpeg",
                        "personGeneration": "ALLOW_ADULT",
                        "negativePrompt": negative_prompt,
                    },
                }
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": compiled_prompt}]}],
                    "generationConfig": {"responseModalities": ["image", "text"]},
                }

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                status_code = resp.status_code

                if status_code == 200:
                    data = resp.json()
                    raw_bytes = b""
                    predictions = data.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        raw_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                    elif "candidates" in data:
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "inlineData" in part and "data" in part["inlineData"]:
                                    raw_bytes = base64.b64decode(part["inlineData"]["data"])
                                    break

                    if raw_bytes:
                        mime_type, ext = self._detect_mime_and_ext(raw_bytes)
                        filename = f"{panel.panel_id or panel.id}_v{version}.{ext}"
                        project_id = panel.project_id or "default"
                        asset_url = self.asset_store.save_asset(
                            project_id=project_id,
                            category="panels",
                            filename=filename,
                            content=raw_bytes,
                        )
                        self._last_state = ProviderState.AVAILABLE
                        self._last_fallback_reason = None
                        self._quota_status = "OK"
                        self._last_safe_message = None

                        return StoryboardImageResult(
                            panel_id=panel.panel_id or panel.id,
                            version=version,
                            image_url=asset_url,
                            provider="google_imagen",
                            mode="ai_image",
                            compiled_prompt=compiled_prompt,
                            negative_prompt=negative_prompt,
                            status=StoryboardImageStatus.READY,
                            fallback_reason=None,
                            provider_status=ProviderState.AVAILABLE.value,
                            continuity_mode="TEXTUAL CONTINUITY ONLY",
                            mime_type=mime_type,
                            render_metadata={
                                "model": self.model_name,
                                "label": "AI IMAGE",
                                "mime_type": mime_type,
                                "bytes_size": len(raw_bytes),
                            },
                        )
                    else:
                        fallback_reason = FallbackReason.INVALID_RESPONSE
                        self._last_state = ProviderState.CONFIG_ERROR
                        self._last_safe_message = "Google API response succeeded but contained no image data."

                elif status_code == 429:
                    # Explicit Quota Exhaustion handling — no loops or repeated retries
                    fallback_reason = FallbackReason.QUOTA_EXCEEDED
                    self._last_state = ProviderState.QUOTA_ERROR
                    self._quota_status = "EXCEEDED"
                    self._last_safe_message = (
                        "Cloud image generation unavailable because this Google project currently "
                        "has no usable quota for the selected image model."
                    )
                    try:
                        err_json = resp.json().get("error", {})
                        google_status = err_json.get("status", "RESOURCE_EXHAUSTED")
                    except Exception:
                        google_status = "RESOURCE_EXHAUSTED"

                    self._last_error_details = {
                        "http_status": 429,
                        "google_status": google_status,
                        "model": self.model_name,
                    }

                elif status_code in (400, 401, 403):
                    fallback_reason = FallbackReason.AUTHENTICATION_FAILED
                    self._last_state = ProviderState.AUTH_ERROR
                    self._last_safe_message = "Google API authentication failed. Please verify your GEMINI_API_KEY."
                elif status_code == 404:
                    fallback_reason = FallbackReason.UNSUPPORTED_MODEL
                    self._last_state = ProviderState.CONFIG_ERROR
                    self._last_safe_message = f"Selected model '{self.model_name}' is not supported on this Google API path."
                else:
                    fallback_reason = FallbackReason.REQUEST_FAILED
                    self._last_state = ProviderState.UNAVAILABLE
                    self._last_safe_message = f"Cloud image generation request failed with HTTP {status_code}."

            self._last_fallback_reason = fallback_reason
            logger.warning(
                f"Cloud image generation failed with HTTP {status_code} ({fallback_reason.value}): "
                f"using procedural comic fallback. Message: {self._last_safe_message}"
            )
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.fallback_reason = fallback_reason.value
            fallback_res.provider_status = self._last_state.value
            fallback_res.render_metadata["fallback_reason"] = fallback_reason.value
            fallback_res.render_metadata["provider_status"] = self._last_state.value
            fallback_res.render_metadata["status_message"] = self._last_safe_message
            fallback_res.render_metadata["model"] = self.model_name
            fallback_res.render_metadata["http_status"] = status_code
            if self._quota_status == "EXCEEDED":
                fallback_res.render_metadata["quota_status"] = "EXCEEDED"
            return fallback_res

        except Exception as err:
            logger.warning(f"Cloud image generation encountered error, falling back to procedural comic engine: {err}")
            self._last_state = ProviderState.UNAVAILABLE
            self._last_fallback_reason = FallbackReason.REQUEST_FAILED
            self._last_safe_message = "Cloud image generation encountered network exception."
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.fallback_reason = FallbackReason.REQUEST_FAILED.value
            fallback_res.provider_status = ProviderState.UNAVAILABLE.value
            fallback_res.render_metadata["fallback_reason"] = FallbackReason.REQUEST_FAILED.value
            fallback_res.render_metadata["status_message"] = self._last_safe_message
            fallback_res.render_metadata["exception"] = str(err)
            return fallback_res


class HuggingFaceStoryboardProvider(ExternalStoryboardImageProvider):
    """Hugging Face Inference API provider for generating storyboard panels.

    Uses server-side HF_TOKEN environment variable.
    Preserves transparent offline fallback to HandDrawnStoryboardProvider on 401, 429, 503,
    missing token, or network failure.
    """

    MANDATORY_STYLE_TAGS = (
        "professional storyboard panel, graphite pencil sketch, rough cross-hatching, "
        "highly detailed, high contrast, grayscale cinematic composition, masterpiece."
    )

    DEFAULT_NEGATIVE_PROMPT = (
        "color, saturation, 3d render, cgi, photorealistic skin, digital gloss, "
        "anime, cartoon, deformed hands, extra fingers, missing fingers, distorted face, "
        "blurry, text, watermark, signature, speech bubbles, low resolution, poorly drawn."
    )

    def __init__(
        self,
        token: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        model_name: Optional[str] = None,
    ):
        self.token = token if token is not None else os.environ.get("HF_TOKEN")
        self.model_name = (
            model_name
            or os.environ.get("HF_MODEL")
            or "stabilityai/stable-diffusion-xl-base-1.0"
        )
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider
        self.fallback = HandDrawnStoryboardProvider(asset_store=self.asset_store)
        self._last_state: ProviderState = (
            ProviderState.AVAILABLE if self.token else ProviderState.UNAVAILABLE
        )
        self._last_fallback_reason: Optional[FallbackReason] = (
            None if self.token else FallbackReason.NO_API_KEY
        )
        self._last_safe_message: Optional[str] = None

    def get_capabilities(self) -> Dict[str, Any]:
        """Expose capabilities without exposing credentials."""
        return {
            "provider": "huggingface",
            "selected_model": self.model_name,
            "available": bool(self.token),
            "pricing_disclaimer": self.PRICING_DISCLAIMER,
            "status_message": (
                self._last_safe_message
                or (
                    "Hugging Face external provider is configured."
                    if self.token
                    else "No HF_TOKEN configured on server."
                )
            ),
            "fallback_enabled": True,
        }

    def get_status(self) -> Dict[str, Any]:
        caps = self.get_capabilities()
        caps["storyboard_image_provider"] = "huggingface"
        caps["mode"] = "cloud"
        caps["status"] = self._last_state.value
        caps["model"] = self.model_name
        caps["fallback_reason"] = (
            self._last_fallback_reason.value if self._last_fallback_reason else None
        )
        return caps

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        base_prompt = self.compiler.compile_panel_prompt(panel, bible)
        full_prompt = f"{base_prompt} {self.MANDATORY_STYLE_TAGS}"
        negative_prompt = self.DEFAULT_NEGATIVE_PROMPT

        if not self.token:
            self._last_state = ProviderState.UNAVAILABLE
            self._last_fallback_reason = FallbackReason.NO_API_KEY
            self._last_safe_message = "No HF_TOKEN configured on server."
            res = self.fallback.generate_panel(panel, bible, version)
            res.fallback_reason = FallbackReason.NO_API_KEY.value
            res.provider_status = ProviderState.UNAVAILABLE.value
            res.render_metadata["fallback_reason"] = FallbackReason.NO_API_KEY.value
            res.render_metadata["pricing_disclaimer"] = self.PRICING_DISCLAIMER
            res.render_metadata["label"] = "HAND-DRAWN STORYBOARD"
            return res

        import httpx
        import time

        url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
            },
        }

        max_retries = 3
        attempt = 0
        last_status = None

        while attempt < max_retries:
            attempt += 1
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    last_status = resp.status_code

                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "")
                        raw_bytes = resp.content

                        if (
                            "image" in content_type
                            or raw_bytes.startswith(b"\x89PNG")
                            or raw_bytes.startswith(b"\xff\xd8")
                            or raw_bytes.startswith(b"RIFF")
                        ):
                            ext = "png" if raw_bytes.startswith(b"\x89PNG") else "jpg"
                            mime = "image/png" if ext == "png" else "image/jpeg"
                            filename = f"{panel.panel_id or panel.id}_v{version}.{ext}"
                            project_id = panel.project_id or "default"

                            asset_url = self.asset_store.save_asset(
                                project_id=project_id,
                                category="panels",
                                filename=filename,
                                content=raw_bytes,
                            )

                            self._last_state = ProviderState.AVAILABLE
                            self._last_fallback_reason = None
                            return StoryboardImageResult(
                                panel_id=panel.panel_id or panel.id,
                                version=version,
                                image_url=asset_url,
                                provider="huggingface",
                                mode="ai_image",
                                compiled_prompt=full_prompt,
                                negative_prompt=negative_prompt,
                                status=StoryboardImageStatus.READY,
                                fallback_reason=None,
                                provider_status=ProviderState.AVAILABLE.value,
                                continuity_mode="TEXTUAL CONTINUITY ONLY",
                                mime_type=mime,
                                render_metadata={
                                    "provider": "huggingface",
                                    "model": self.model_name,
                                    "label": "EXTERNAL AI IMAGE",
                                    "version": version,
                                    "pricing_disclaimer": self.PRICING_DISCLAIMER,
                                },
                            )

                    # Handle 401/403 Authentication Error (fail immediately without retry)
                    if resp.status_code in (401, 403):
                        self._last_state = ProviderState.AUTH_ERROR
                        self._last_fallback_reason = FallbackReason.AUTHENTICATION_FAILED
                        self._last_safe_message = "Hugging Face authentication failed. Check HF_TOKEN on server."
                        break

                    # Handle 503 Model Loading or 429 Rate Throttled
                    if resp.status_code in (503, 429, 504):
                        wait_sec = 2.0 * attempt
                        try:
                            err_json = resp.json()
                            if isinstance(err_json, dict) and "estimated_time" in err_json:
                                est = float(err_json["estimated_time"])
                                wait_sec = min(max(wait_sec, est), 30.0)
                        except Exception:
                            pass

                        if attempt < max_retries:
                            time.sleep(min(wait_sec, 2.0))
                            continue
                        else:
                            if resp.status_code == 429:
                                self._last_state = ProviderState.QUOTA_ERROR
                                self._last_fallback_reason = FallbackReason.QUOTA_EXCEEDED
                                self._last_safe_message = "Hugging Face rate limit / quota exceeded."
                            else:
                                self._last_state = ProviderState.UNAVAILABLE
                                self._last_fallback_reason = FallbackReason.REQUEST_FAILED
                                self._last_safe_message = "Hugging Face model warmup timed out."
                            break

                    self._last_state = ProviderState.UNAVAILABLE
                    self._last_fallback_reason = FallbackReason.REQUEST_FAILED
                    self._last_safe_message = f"Hugging Face request returned status {resp.status_code}."
                    break

            except Exception as e:
                logger.warning(f"Hugging Face request exception on attempt {attempt}: {e}")
                if attempt >= max_retries:
                    self._last_state = ProviderState.UNAVAILABLE
                    self._last_fallback_reason = FallbackReason.REQUEST_FAILED
                    self._last_safe_message = "Hugging Face network request failed."
                    break
                time.sleep(1.0)

        # Fallback to deterministic hand-drawn SVG
        fallback_res = self.fallback.generate_panel(panel, bible, version)
        fb_reason = (
            self._last_fallback_reason.value
            if self._last_fallback_reason
            else FallbackReason.REQUEST_FAILED.value
        )
        fallback_res.fallback_reason = fb_reason
        fallback_res.provider_status = self._last_state.value
        fallback_res.render_metadata["fallback_reason"] = fb_reason
        fallback_res.render_metadata["status_message"] = self._last_safe_message
        fallback_res.render_metadata["pricing_disclaimer"] = self.PRICING_DISCLAIMER
        fallback_res.render_metadata["label"] = "HAND-DRAWN STORYBOARD"
        fallback_res.render_metadata["http_status"] = last_status
        return fallback_res


class MockStoryboardImageProvider(StoryboardImageProvider):
    """Deterministic, fast mock provider for offline testing and test suites."""

    def __init__(
        self,
        asset_store: Optional[StoryboardAssetStore] = None,
        simulate_ai_mode: bool = False,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.fallback = FallbackComicSvgProvider(asset_store=self.asset_store)
        self.simulate_ai_mode = simulate_ai_mode

    def get_status(self) -> Dict[str, Any]:
        mode = "cloud" if self.simulate_ai_mode else "mock"
        return {
            "storyboard_image_provider": "mock_provider",
            "mode": mode,
            "status": ProviderState.AVAILABLE.value,
            "available": True,
            "model": "mock_imagen_raster" if self.simulate_ai_mode else "mock_procedural",
            "fallback_enabled": True,
            "fallback_reason": None if self.simulate_ai_mode else FallbackReason.PROVIDER_NOT_CONFIGURED.value,
            "continuity_mode": "TEXTUAL CONTINUITY ONLY",
            "supports_image_conditioning": False,
        }

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        if self.simulate_ai_mode:
            # Generate genuine offline 1x1 or test raster PNG bytes
            # Minimal valid PNG: 1x1 black pixel with PNG header
            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
                b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            filename = f"{panel.panel_id or panel.id}_v{version}.png"
            project_id = panel.project_id or "default"
            asset_url = self.asset_store.save_asset(
                project_id=project_id,
                category="panels",
                filename=filename,
                content=png_bytes,
            )
            return StoryboardImageResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                image_url=asset_url,
                provider="mock_ai_provider",
                mode="ai_image",
                compiled_prompt=compiled_prompt,
                negative_prompt=negative_prompt,
                status=StoryboardImageStatus.READY,
                fallback_reason=None,
                provider_status=ProviderState.AVAILABLE.value,
                continuity_mode="TEXTUAL CONTINUITY ONLY",
                mime_type="image/png",
                render_metadata={
                    "is_mock": True,
                    "label": "AI IMAGE",
                    "model": "mock_imagen_raster",
                    "mime_type": "image/png",
                },
            )

        # Procedural SVG fallback
        res = self.fallback.generate_panel(panel, bible, version)
        return StoryboardImageResult(
            panel_id=panel.panel_id or panel.id,
            version=version,
            image_url=res.image_url,
            svg_content=res.svg_content,
            provider="mock_comic_renderer",
            mode="fallback_comic",
            compiled_prompt=compiled_prompt,
            negative_prompt=negative_prompt,
            status=StoryboardImageStatus.READY,
            fallback_reason=FallbackReason.PROVIDER_NOT_CONFIGURED.value,
            provider_status=ProviderState.AVAILABLE.value,
            continuity_mode="TEXTUAL CONTINUITY ONLY",
            mime_type="image/svg+xml",
            render_metadata={
                "is_mock": True,
                "label": "FALLBACK COMIC",
                "fallback_reason": FallbackReason.PROVIDER_NOT_CONFIGURED.value,
            },
        )


class OpenModelImageProviderAdapter(StoryboardImageProvider):
    """Primary adapter bridging OpenModelStoryboardProvider into the StoryboardImageProvider interface."""

    def __init__(
        self,
        asset_store: Optional[StoryboardAssetStore] = None,
        runtime_url: Optional[str] = None,
        model_name: Optional[str] = None,
        adapter_type: Optional[str] = None,
    ):
        self.asset_store = asset_store or StoryboardAssetStore()
        from src.storyboard.open_model_provider import (
            OpenModelStoryboardProvider,
            ComfyUIStoryboardAdapter,
            DiffusersStoryboardAdapter,
            MockOpenModelStoryboardAdapter,
        )
        adapter = None
        if adapter_type in ("on_demand", "ondemand", "on-demand"):
            from src.storyboard.on_demand_provider import OnDemandStoryboardProvider
            adapter = OnDemandStoryboardProvider(asset_store=self.asset_store, model_name=model_name)
        elif adapter_type == "comfyui":
            adapter = ComfyUIStoryboardAdapter(runtime_url=runtime_url, model_name=model_name, asset_store=self.asset_store)
        elif adapter_type == "diffusers":
            adapter = DiffusersStoryboardAdapter(runtime_url=runtime_url, model_name=model_name, asset_store=self.asset_store)
        elif adapter_type in ("mock_ai", "mock_connected"):
            adapter = MockOpenModelStoryboardAdapter(asset_store=self.asset_store, simulate_connected=True)
        elif adapter_type in ("mock_unavailable", "mock"):
            adapter = MockOpenModelStoryboardAdapter(asset_store=self.asset_store, simulate_connected=False)
        self.engine = OpenModelStoryboardProvider(adapter=adapter, asset_store=self.asset_store)


    def health_check(self, probe: Optional[bool] = None) -> Dict[str, Any]:
        return self.engine.health_check(probe=probe)

    def get_capabilities(self, probe: Optional[bool] = None) -> Dict[str, Any]:
        return self.engine.get_capabilities(probe=probe).to_dict()

    def get_status(self) -> Dict[str, Any]:
        caps = self.get_capabilities()
        health = self.engine.health_check()
        return {
            "storyboard_image_provider": "open_model_storyboard",
            "mode": "open_model",
            "status": "AVAILABLE" if health.get("available") else "UNAVAILABLE",
            "available": health.get("available", False),
            "fallback_enabled": False,
            "continuity_mode": "Deterministic Visual Bible & Continuity Packs",
            "model": caps.get("model", ""),
            "status_message": health.get("message", ""),
            "provider_status": health.get("provider_status", caps.get("provider_status", "CONNECTED" if health.get("available") else "NOT_CONFIGURED")),
            "model_status": health.get("model_status", caps.get("model_status", "AVAILABLE" if health.get("available") else "UNAVAILABLE")),
            "supports_reference_images": caps.get("supports_reference_images", False),
            "pose_control": caps.get("pose_control", False),
            "depth_control": caps.get("depth_control", False),
            "edge_control": caps.get("edge_control", False),
            "max_resolution": caps.get("max_resolution", "1280x720"),
            "pricing_disclaimer": caps.get("pricing_disclaimer", ""),
        }

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        res = self.engine.render_panel(panel, bible=bible, version=version)
        ctrl_dict = res.control_bundle.to_dict() if res.control_bundle else None
        panel.control_bundle = ctrl_dict
        panel.previs_svg = res.control_bundle.previs_svg if res.control_bundle else None

        if res.status == StoryboardImageStatus.READY and res.image_url:
            panel.rendered_image_url = res.image_url
            panel.image_url = res.image_url
            panel.rendered_svg = None  # NEVER output procedural SVG as final artwork
            return StoryboardImageResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                image_url=res.image_url,
                svg_content=None,
                provider="open_model_storyboard",
                mode="open_model_storyboard",
                compiled_prompt=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                status=StoryboardImageStatus.READY,
                fallback_reason=None,
                provider_status="AVAILABLE",
                continuity_mode="Open-Model Continuity Pack",
                mime_type=res.mime_type,
                render_metadata={
                    "provider": "open_model_storyboard",
                    "model": res.model,
                    "label": "OPEN-MODEL STORYBOARD",
                    "prompt_hash": res.prompt_hash,
                    "seed": res.seed,
                    "previs_available": True,
                    "control_bundle": ctrl_dict,
                },
            )
        else:
            panel.rendered_image_url = None
            panel.image_url = None
            panel.rendered_svg = None  # NEVER output procedural SVG as final artwork
            return StoryboardImageResult(
                panel_id=panel.panel_id or panel.id,
                version=version,
                image_url="",
                svg_content=None,
                provider="open_model_storyboard",
                mode="previs_guide",
                compiled_prompt=res.compiled_prompt,
                negative_prompt=res.negative_prompt,
                status=StoryboardImageStatus.FAILED if res.status == StoryboardImageStatus.FAILED else StoryboardImageStatus.PLANNED,
                fallback_reason=res.fallback_reason or "RUNTIME_UNAVAILABLE",
                provider_status="UNAVAILABLE",
                continuity_mode="Open-Model Continuity Pack",
                mime_type="image/png",
                render_metadata={
                    "provider": "open_model_storyboard",
                    "model": res.model,
                    "label": "PREVIS GUIDE",
                    "previs_available": True,
                    "status_message": res.status_message or "Storyboard render unavailable. Previs guide available. Configure renderer.",
                    "control_bundle": ctrl_dict,
                },
            )


def get_default_storyboard_provider(
    asset_store: Optional[StoryboardAssetStore] = None,
) -> StoryboardImageProvider:
    """Return the default Open-Model Storyboard Provider."""
    return OpenModelImageProviderAdapter(asset_store=asset_store)
