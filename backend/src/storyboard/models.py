"""Data models for Storyboard Generation, Comic Compositing, and Continuity pipeline."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
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
    INSERT = "insert"
    REACTION = "reaction"


class CameraAngle(str, Enum):
    """Cinematic camera elevation / angles."""
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH_ANGLE = "dutch_angle"
    BIRD_EYE = "bird_eye"


class ShotPurpose(str, Enum):
    """Narrative storytelling function of the storyboard shot."""
    ESTABLISH = "establish"
    INTRODUCE_CHARACTER = "introduce_character"
    ACTION = "action"
    DIALOGUE = "dialogue"
    REACTION = "reaction"
    REVELATION = "revelation"
    REVEAL = "reveal"
    DISCOVERY = "discovery"
    CLUE = "clue"
    THREAT = "threat"
    POWER_SHIFT = "power_shift"
    TRANSITION = "transition"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class StoryboardImageStatus(str, Enum):
    """Status of image generation for an individual panel."""
    PLANNED = "planned"
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    FALLBACK = "fallback"


class PageLayoutTemplate(str, Enum):
    """Comic/graphic novel page layout templates."""
    TEMPLATE_A = "template_a"  # Hero top strip, two middle square panels, hero bottom strip
    TEMPLATE_B = "template_b"  # 3 cinematic panoramic horizontal strips
    TEMPLATE_C = "template_c"  # Tall hero panel left, two stacked horizontal panels right
    TEMPLATE_D = "template_d"  # 6-frame sequence (2x3 grid)
    TEMPLATE_E = "template_e"  # Large climax splash hero page with insets


class StoryboardImageVersion(BaseModel):
    """A specific generated version of a panel's visual artwork."""
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    image_url: str = ""
    prompt_used: str = ""
    prompt_hash: Optional[str] = None
    negative_prompt: str = ""
    provider: str = ""
    model: Optional[str] = None
    seed: Optional[int] = None
    mode: str = "open_model_storyboard"  # "open_model_storyboard" | "ai_image" | "previs_guide"
    fallback_reason: Optional[str] = None
    mime_type: Optional[str] = None
    continuity_mode: str = "Open-Model Continuity Pack"
    previs_available: bool = True
    control_bundle: Optional[Dict[str, Any]] = None
    generation_time_ms: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_selected: bool = False
    render_metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryboardPanel(BaseModel):
    """An individual visual storyboard panel representing a shot in the narrative."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"pnl_{uuid.uuid4().hex[:8]}")
    panel_id: str = ""
    project_id: str = ""
    scene_id: str = ""
    scene_number: int = Field(default=1, ge=1)
    panel_number: int = Field(default=1, ge=1)
    shot_number: int = Field(default=1, ge=1)
    page_number: int = Field(default=1, ge=1)
    shot_type: ShotType = ShotType.MEDIUM
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    narrative_purpose: ShotPurpose = ShotPurpose.ACTION
    lens_feel: str = "35mm cinematic standard, sharp depth of field"
    composition: str = "Rule of thirds, strong diagonal shadows, leading lines"
    psychological_rationale: Optional[str] = None
    subject_focus: str = ""
    layout_slot: str = "default"

    location_id: str = ""
    location_name: str = ""
    characters_present: List[str] = Field(default_factory=list)
    character_names: List[str] = Field(default_factory=list)
    objects_in_frame: List[str] = Field(default_factory=list)
    action: str = ""
    action_description: str = ""
    visual_description: str = ""
    lighting: str = "Low-key lighting, dramatic shadows"
    mood: str = "Tense, suspenseful"
    style_profile_id: str = "noir_graphic_novel"

    prompt: str = ""
    image_prompt: str = ""
    visual_prompt: str = Field(default="", description="Optimized prompt for visual generation")
    compiled_prompt: str = Field(default="", description="Fully compiled multi-layer prompt")
    negative_prompt: str = (
        "text, watermark, speech bubbles rendered in image, blurry, low quality, "
        "distorted anatomy, cartoonish, 3d render, plastic smooth skin"
    )
    style_tags: List[str] = Field(
        default_factory=lambda: [
            "cinematic graphic novel",
            "noir comic ink",
            "high contrast chiaroscuro",
            "heavy black brushwork",
        ]
    )

    character_references: Dict[str, str] = Field(default_factory=dict)
    object_references: Dict[str, str] = Field(default_factory=dict)
    location_reference: str = ""
    caption: str = ""
    dialogue_excerpt: Optional[str] = None
    dialogue_bubble_type: Optional[str] = None  # "speech" | "whisper" | "shout" | "thought" | "caption"
    sfx_label: Optional[str] = None
    continuity_notes: str = ""
    camera_movement: str = "STATIC"  # "STATIC" | "PUSH IN" | "DOLLY OUT" | "TRACK ->" | "PAN ->" | "DUTCH TILT" | "HANDHELD" | "RACK FOCUS"
    focal_depth_plane: str = "focal_plane"  # "foreground" | "focal_plane" | "background"
    lighting_profile_id: str = "NOIR_HARD"
    transition_type: Optional[str] = None  # "MATCH_CUT" | "GRAPHIC_MATCH" | "ACTION_MATCH" | "EYELINE_CUT" | "TRACKING_CONTINUATION" | "WHIP_PAN" | "RACK_FOCUS" | "INSERT_TO_REACTION" | "REVEAL"
    transition_source_shot: Optional[int] = None
    transition_target_shot: Optional[int] = None
    visual_link: Optional[str] = None

    image_asset_id: Optional[str] = None
    image_url: Optional[str] = None
    rendered_image_url: Optional[str] = None
    rendered_svg: Optional[str] = None
    previs_svg: Optional[str] = None
    control_bundle: Optional[Dict[str, Any]] = None
    character_continuity: Optional[Dict[str, Any]] = None
    location_continuity: Optional[Dict[str, Any]] = None
    prop_continuity: Optional[Dict[str, Any]] = None
    is_keyframe: bool = False
    keyframe_reason: Optional[str] = None
    image_status: StoryboardImageStatus = StoryboardImageStatus.PLANNED
    provider: str = ""
    fallback_reason: Optional[str] = None
    status_message: Optional[str] = None
    continuity_mode: str = "TEXTUAL CONTINUITY ONLY"
    generation_version: int = 1
    selected_version: int = 1
    versions: List[StoryboardImageVersion] = Field(default_factory=list)

    aspect_ratio: str = "16:9"
    camera_axis_side: Optional[str] = "LEFT"
    axis_crossing_flag: bool = False
    screen_direction: Optional[str] = None
    source_event_ids: List[str] = Field(default_factory=list)
    source_screenplay_block_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Ensure synchronized fallbacks for IDs, prompts, and URLs."""
        if not self.panel_id:
            self.panel_id = self.id
        if not self.image_prompt:
            self.image_prompt = self.compiled_prompt or self.visual_prompt or self.prompt
        if not self.prompt:
            self.prompt = self.image_prompt
        if not self.visual_prompt:
            self.visual_prompt = self.image_prompt
        if not self.compiled_prompt:
            self.compiled_prompt = self.image_prompt
        if not self.caption:
            cap = self.dialogue_excerpt or self.action or self.action_description
            self.caption = cap[:120] if cap else ""
        if self.image_url and not self.rendered_image_url:
            self.rendered_image_url = self.image_url
        elif self.rendered_image_url and not self.image_url:
            self.image_url = self.rendered_image_url


class StoryboardPage(BaseModel):
    """A collection of storyboard panels formatted as a comic/graphic novel page."""
    model_config = ConfigDict(extra="ignore")

    page_number: int
    total_pages: int
    title: str = ""
    layout_template: PageLayoutTemplate = PageLayoutTemplate.TEMPLATE_A
    panels: List[StoryboardPanel] = Field(default_factory=list)


class ShotPlan(BaseModel):
    """A complete sequence of storyboard panels for a screenplay, organized into pages."""
    model_config = ConfigDict(extra="ignore")

    project_title: str
    total_panels: int
    total_pages: int = 1
    panels_per_page: int = 4
    panels: List[StoryboardPanel] = Field(default_factory=list)
    aspect_ratio: str = "16:9"
    pages: List[StoryboardPage] = Field(default_factory=list)
    density_mode: str = "standard"  # "quick" | "standard" | "detailed"
    render_mode: str = "KEYFRAMES"  # "KEYFRAMES" | "FULL_BOARD"
    keyframe_panel_indices: List[int] = Field(default_factory=list)
    runtime_status: Dict[str, Any] = Field(default_factory=dict)
    storyboard_coverage: Dict[str, Any] = Field(default_factory=dict)
