"""Data models for Storyboard Preparation phase."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ShotType(str, Enum):
    """Cinematic camera framing types."""
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_SHOULDER = "over_shoulder"


class CameraAngle(str, Enum):
    """Cinematic camera elevation / angles."""
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH_ANGLE = "dutch_angle"
    BIRD_EYE = "bird_eye"


class StoryboardPanel(BaseModel):
    """An individual visual storyboard panel representing a shot."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"pnl_{uuid.uuid4().hex[:8]}")
    scene_number: int = Field(default=1, ge=1)
    panel_number: int = Field(default=1, ge=1)
    shot_number: int = Field(default=1, ge=1)
    shot_type: ShotType = ShotType.MEDIUM
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    location_id: str = ""
    location_name: str = ""
    characters_present: List[str] = Field(default_factory=list)
    character_names: List[str] = Field(default_factory=list)
    action: str = ""
    action_description: str = ""
    visual_description: str = ""
    lighting: str = "Low-key lighting, dramatic shadows"
    mood: str = "Tense, suspenseful"
    prompt: str = ""
    dialogue_excerpt: Optional[str] = None
    visual_prompt: str = Field(default="", description="Optimized prompt for static visual panel generation")
    aspect_ratio: str = "16:9"
    source_event_ids: List[str] = Field(default_factory=list)
    source_screenplay_block_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShotPlan(BaseModel):
    """A complete sequence of storyboard panels for a screenplay."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_title: str
    total_panels: int
    panels: List[StoryboardPanel] = Field(default_factory=list)
    aspect_ratio: str = "16:9"
