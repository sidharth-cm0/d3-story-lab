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
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, StoryboardImageStatus, StoryboardImageVersion
from src.storyboard.visual_bible import VisualBible
from src.storyboard.compiler import StoryboardPromptCompiler
from src.storyboard.asset_store import StoryboardAssetStore
from src.storyboard.provider import ComicGraphicStoryboardProvider

logger = logging.getLogger(__name__)


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

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        # Render rich SVG from our procedural comic engine
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
            render_metadata={
                "engine": "ComicGraphicStoryboardProvider",
                "is_fallback": True,
                "label": "FALLBACK COMIC",
            },
        )


class CloudImagenStoryboardProvider(StoryboardImageProvider):
    """Cloud AI image generator using Google Gemini / Imagen API with transparent fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        asset_store: Optional[StoryboardAssetStore] = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.asset_store = asset_store or StoryboardAssetStore()
        self.compiler = StoryboardPromptCompiler()
        self.fallback = FallbackComicSvgProvider(asset_store=self.asset_store)

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        if not self.api_key:
            # Transparent fallback when API key is not present
            res = self.fallback.generate_panel(panel, bible, version)
            res.render_metadata["fallback_reason"] = "GEMINI_API_KEY not configured"
            return res

        try:
            # Attempt Imagen API generation via google-genai or requests
            import httpx

            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={self.api_key}"
            payload = {
                "instances": [
                    {"prompt": compiled_prompt}
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "negativePrompt": negative_prompt,
                }
            }

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    predictions = data.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        import base64
                        raw_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                        filename = f"{panel.panel_id or panel.id}_v{version}.png"
                        project_id = panel.project_id or "default"
                        asset_url = self.asset_store.save_asset(
                            project_id=project_id,
                            category="panels",
                            filename=filename,
                            content=raw_bytes,
                        )
                        return StoryboardImageResult(
                            panel_id=panel.panel_id or panel.id,
                            version=version,
                            image_url=asset_url,
                            provider="google_imagen",
                            mode="ai_image",
                            compiled_prompt=compiled_prompt,
                            negative_prompt=negative_prompt,
                            status=StoryboardImageStatus.READY,
                            render_metadata={
                                "model": "imagen-3.0-generate-002",
                                "label": "AI IMAGE",
                            },
                        )

            # If request failed or returned unexpected format, fall back safely
            logger.warning(f"Imagen API request returned status {resp.status_code if 'resp' in locals() else 'unknown'}")
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.render_metadata["fallback_reason"] = f"API returned non-200 or invalid payload"
            return fallback_res

        except Exception as err:
            logger.warning(f"Cloud image generation encountered error, falling back to procedural comic engine: {err}")
            fallback_res = self.fallback.generate_panel(panel, bible, version)
            fallback_res.render_metadata["fallback_reason"] = f"Exception: {str(err)}"
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

    def generate_panel(
        self,
        panel: StoryboardPanel,
        bible: Optional[VisualBible] = None,
        version: int = 1,
    ) -> StoryboardImageResult:
        compiled_prompt = self.compiler.compile_panel_prompt(panel, bible)
        negative_prompt = self.compiler.compile_negative_prompt(panel, bible)

        # Generate procedural SVG
        res = self.fallback.generate_panel(panel, bible, version)

        mode = "ai_image" if self.simulate_ai_mode else "fallback_comic"
        provider_name = "mock_ai_provider" if self.simulate_ai_mode else "mock_comic_renderer"

        return StoryboardImageResult(
            panel_id=panel.panel_id or panel.id,
            version=version,
            image_url=res.image_url,
            svg_content=res.svg_content,
            provider=provider_name,
            mode=mode,
            compiled_prompt=compiled_prompt,
            negative_prompt=negative_prompt,
            status=StoryboardImageStatus.READY,
            render_metadata={
                "is_mock": True,
                "label": "AI IMAGE" if mode == "ai_image" else "FALLBACK COMIC",
            },
        )
