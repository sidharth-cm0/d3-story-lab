"""Storyboard rendering provider abstraction for generating panel visuals."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.storyboard.models import StoryboardPanel


class StoryboardProvider(ABC):
    """Abstract interface for rendering storyboard panel visual representations."""

    @abstractmethod
    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        """Produce visual asset metadata (image URL, data URI, or rendered sketch)."""
        pass


class MockStoryboardProvider(StoryboardProvider):
    """Deterministic mock provider that generates SVG sketch placeholders without external APIs."""

    def render_panel(self, panel: StoryboardPanel) -> Dict[str, Any]:
        # Generate clean SVG graphic placeholder representing framing
        shot = panel.shot_type.value.upper()
        angle = panel.camera_angle.value.upper()
        heading = f"Scene {panel.scene_number} / Shot {panel.panel_number}"
        summary = (panel.dialogue_excerpt or panel.action_description)[:60]

        svg_content = (
            f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 360' width='100%' height='100%'>"
            f"<rect width='640' height='360' fill='#0f172a' stroke='#334155' stroke-width='4'/>"
            f"<circle cx='320' cy='180' r='90' fill='none' stroke='#38bdf8' stroke-width='2' stroke-dasharray='4,4'/>"
            f"<text x='30' y='45' fill='#94a3b8' font-family='monospace' font-size='16'>{heading}</text>"
            f"<text x='30' y='75' fill='#f59e0b' font-family='sans-serif' font-size='14' font-weight='bold'>{shot} | {angle}</text>"
            f"<text x='30' y='320' fill='#e2e8f0' font-family='sans-serif' font-size='13'>{summary}</text>"
            f"</svg>"
        )

        return {
            "panel_id": panel.id,
            "panel_number": panel.panel_number,
            "render_type": "svg_placeholder",
            "svg_data": svg_content,
            "prompt_used": panel.visual_prompt,
            "is_mock": True,
        }
