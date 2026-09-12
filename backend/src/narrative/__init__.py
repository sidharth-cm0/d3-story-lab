"""Narrative intelligence, observation, and Fountain screenplay generation."""

from .observer import NarrativeBeat, NarrativeBeatType, NarrativeEventSelection, Observer
from .fountain import (
    ScreenplayBlock,
    ScreenplayBlockType,
    ScreenplayScene,
    ScreenplayDocument,
)
from .scribe import Scribe
from .completion import StoryCompletionEngine, StoryOutline, StoryInputType, ActBeat
from .synopsis import SynopsisGenerator, StorySynopsis

__all__ = [
    "NarrativeBeat",
    "NarrativeBeatType",
    "NarrativeEventSelection",
    "Observer",
    "ScreenplayBlock",
    "ScreenplayBlockType",
    "ScreenplayScene",
    "ScreenplayDocument",
    "Scribe",
    "StoryCompletionEngine",
    "StoryOutline",
    "StoryInputType",
    "ActBeat",
    "SynopsisGenerator",
    "StorySynopsis",
]
