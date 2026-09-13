"""Base Interfaces and Capability Definitions for Storyboard Render Providers.

Defines the contract for open-model image rendering engines:
- Model Capability Discovery
- Health Checks without exposing confidential runtime credentials
- Reference Image & Identity Conditioning
- ControlNet / Guidance Maps
- Deterministic Asset Persistence and Versioning
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from src.storyboard.models import StoryboardPanel, StoryboardImageStatus
from src.storyboard.continuity import (
    CharacterContinuityPack,
    LocationContinuityPack,
    PropContinuityPack,
    StoryboardSequenceContext,
)
from src.storyboard.control import StoryboardControlBundle
from src.storyboard.visual_bible import VisualBible


class RenderMode(str, Enum):
    """Storyboard rendering execution modes."""
    KEYFRAMES = "KEYFRAMES"      # Render only major narrative beats (default)
    FULL_BOARD = "FULL_BOARD"    # Render every shot panel in sequence


class ProviderCapabilityReport(BaseModel):
    """Normalized capabilities reported by a render runtime."""
    model_config = ConfigDict(extra="ignore")

    provider: str
    model: str
    available: bool = False
    status: str = "UNCONFIGURED"
    status_message: str = "Runtime not configured"
    provider_status: str = "NOT_CONFIGURED"
    model_status: str = "UNCHECKED"
    supports_reference_images: bool = False
    supports_ip_adapter: bool = False
    supports_identity_conditioning: bool = False
    pose_control: bool = False
    depth_control: bool = False
    edge_control: bool = False
    seed_support: bool = True
    max_resolution: str = "1280x720"
    render_modes_supported: List[str] = Field(default_factory=lambda: ["KEYFRAMES", "FULL_BOARD"])
    pricing_disclaimer: str = (
        "Open-model generation runtime. Connects to configured local or remote inference worker."
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class PanelArtworkAssetRecord(BaseModel):
    """Persistent metadata record stored with every generated raster panel."""
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    version: int = 1
    provider: str
    model: str
    seed: int = 42
    prompt_hash: str
    reference_ids: List[str] = Field(default_factory=list)
    control_ids: List[str] = Field(default_factory=list)
    width: int = 960
    height: int = 540
    mime_type: str = "image/png"
    file_path: str = ""
    image_url: str = ""
    generation_time_ms: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    structured_prompt: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryboardRenderResult(BaseModel):
    """Result returned by a StoryboardRenderProvider."""
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    version: int = 1
    status: StoryboardImageStatus = StoryboardImageStatus.READY
    image_url: Optional[str] = None
    mime_type: str = "image/png"
    provider: str = ""
    model: str = ""
    seed: int = 42
    prompt_hash: str = ""
    compiled_prompt: str = ""
    negative_prompt: str = ""
    previs_guide_available: bool = True
    control_bundle: Optional[StoryboardControlBundle] = None
    asset_record: Optional[PanelArtworkAssetRecord] = None
    fallback_reason: Optional[str] = None
    status_message: Optional[str] = None
    render_metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryboardRenderProvider(ABC):
    """Abstract interface for all open-model and generative storyboard providers."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilityReport:
        """Report runtime capabilities, controlnet support, and availability."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform non-destructive connectivity check against configured runtime."""
        pass

    @abstractmethod
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
        """Generate final raster artwork for an individual storyboard panel."""
        pass
