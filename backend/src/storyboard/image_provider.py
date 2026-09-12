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
from typing import Dict, Any, Optional, List
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


class CloudImagenStoryboardProvider(StoryboardImageProvider):
    """Cloud AI image generator using Google Gemini / Imagen API with transparent fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
        model_name: str = "imagen-3.0-generate-002",
    ):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("IMAGEN_API_KEY")
        )
        self.model_name = model_name
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.fallback = FallbackComicSvgProvider(asset_store=self.asset_store)
        self._last_state: ProviderState = (
            ProviderState.AVAILABLE if self.api_key else ProviderState.UNAVAILABLE
        )
        self._last_fallback_reason: Optional[FallbackReason] = (
            None if self.api_key else FallbackReason.NO_API_KEY
        )

    def get_status(self) -> Dict[str, Any]:
        """Expose runtime state safely without revealing secrets."""
        return {
            "storyboard_image_provider": "google_imagen",
            "mode": "cloud",
            "status": self._last_state.value,
            "available": bool(self.api_key),
            "model": self.model_name,
            "fallback_enabled": True,
            "fallback_reason": self._last_fallback_reason.value if self._last_fallback_reason else None,
            "continuity_mode": "TEXTUAL CONTINUITY ONLY",
            "supports_image_conditioning": False,
        }

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
            res = self.fallback.generate_panel(panel, bible, version)
            res.fallback_reason = FallbackReason.NO_API_KEY.value
            res.provider_status = ProviderState.UNAVAILABLE.value
            res.render_metadata["fallback_reason"] = FallbackReason.NO_API_KEY.value
            res.render_metadata["provider_status"] = ProviderState.UNAVAILABLE.value
            res.render_metadata["model"] = self.model_name
            res.render_metadata["label"] = "FALLBACK COMIC"
            return res

        try:
            import httpx

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:predict?key={self.api_key}"
            payload = {
                "instances": [
                    {"prompt": compiled_prompt}
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "outputMimeType": "image/jpeg",
                    "personGeneration": "ALLOW_ADULT",
                    "negativePrompt": negative_prompt,
                }
            }

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                status_code = resp.status_code

                if status_code == 200:
                    data = resp.json()
                    predictions = data.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        raw_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
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
                elif status_code in (400, 401, 403):
                    fallback_reason = FallbackReason.AUTHENTICATION_FAILED
                    self._last_state = ProviderState.AUTH_ERROR
                elif status_code == 404:
                    # Attempt multimodal Gemini image generation endpoint
                    try:
                        gc_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={self.api_key}"
                        gc_payload = {
                            "contents": [{"parts": [{"text": compiled_prompt}]}],
                            "generationConfig": {"responseModalities": ["image", "text"]},
                        }
                        gc_resp = client.post(gc_url, json=gc_payload, timeout=30.0)
                        if gc_resp.status_code == 200:
                            gc_data = gc_resp.json()
                            for cand in gc_data.get("candidates", []):
                                for part in cand.get("content", {}).get("parts", []):
                                    if "inlineData" in part and "data" in part["inlineData"]:
                                        raw_bytes = base64.b64decode(part["inlineData"]["data"])
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
                                        return StoryboardImageResult(
                                            panel_id=panel.panel_id or panel.id,
                                            version=version,
                                            image_url=asset_url,
                                            provider="google_gemini_image",
                                            mode="ai_image",
                                            compiled_prompt=compiled_prompt,
                                            negative_prompt=negative_prompt,
                                            status=StoryboardImageStatus.READY,
                                            fallback_reason=None,
                                            provider_status=ProviderState.AVAILABLE.value,
                                            continuity_mode="TEXTUAL CONTINUITY ONLY",
                                            mime_type=mime_type,
                                            render_metadata={
                                                "model": "gemini-3.1-flash-image",
                                                "label": "AI IMAGE",
                                                "mime_type": mime_type,
                                                "bytes_size": len(raw_bytes),
                                            },
                                        )
                        status_code = gc_resp.status_code
                    except Exception:
                        pass

                    if status_code == 429:
                        fallback_reason = FallbackReason.QUOTA_EXCEEDED
                        self._last_state = ProviderState.QUOTA_ERROR
                    elif status_code in (400, 401, 403):
                        fallback_reason = FallbackReason.AUTHENTICATION_FAILED
                        self._last_state = ProviderState.AUTH_ERROR
                    elif status_code == 404:
                        fallback_reason = FallbackReason.UNSUPPORTED_MODEL
                        self._last_state = ProviderState.CONFIG_ERROR
                    else:
                        fallback_reason = FallbackReason.REQUEST_FAILED
                        self._last_state = ProviderState.UNAVAILABLE
                elif status_code == 429:
                    fallback_reason = FallbackReason.QUOTA_EXCEEDED
                    self._last_state = ProviderState.QUOTA_ERROR
                else:
                    fallback_reason = FallbackReason.REQUEST_FAILED
                    self._last_state = ProviderState.UNAVAILABLE

            self._last_fallback_reason = fallback_reason
            logger.warning(f"Imagen API request failed with status {status_code}: falling back with reason {fallback_reason.value}")
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.fallback_reason = fallback_reason.value
            fallback_res.provider_status = self._last_state.value
            fallback_res.render_metadata["fallback_reason"] = fallback_reason.value
            fallback_res.render_metadata["provider_status"] = self._last_state.value
            fallback_res.render_metadata["model"] = self.model_name
            fallback_res.render_metadata["http_status"] = status_code
            return fallback_res

        except Exception as err:
            logger.warning(f"Cloud image generation encountered error, falling back to procedural comic engine: {err}")
            self._last_state = ProviderState.UNAVAILABLE
            self._last_fallback_reason = FallbackReason.REQUEST_FAILED
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.fallback_reason = FallbackReason.REQUEST_FAILED.value
            fallback_res.provider_status = ProviderState.UNAVAILABLE.value
            fallback_res.render_metadata["fallback_reason"] = FallbackReason.REQUEST_FAILED.value
            fallback_res.render_metadata["exception"] = str(err)
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
