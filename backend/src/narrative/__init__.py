"""Narrative intelligence, observation, and Fountain screenplay generation."""

from .observer import NarrativeBeat, NarrativeBeatType, NarrativeEventSelection, Observer, EventSalience
from .scene_builder import SceneBuilder, SufficiencyGateExecutionError
from .causal_analyzer import CausalContinuityAnalyzer
from .provenance import ProvenanceService
from .fountain import (
    ScreenplayBlock,
    ScreenplayBlockType,
    ScreenplayScene,
    ScreenplayDocument,
)
from .scribe import Scribe
from .completion import StoryCompletionEngine, StoryOutline, StoryInputType, ActBeat
from .synopsis import SynopsisGenerator, StorySynopsis
from .arc_tracker import CharacterArcTracker
from .subtext import SubtextAnalyzer, DeceptionClassification, SubtextAnalysis
from .performance_cues import (
    PerformanceCueGenerator,
    PerformanceCueType,
    PerformanceCue,
    InternalStateVerbGuard,
)
from .scene_projection import (
    INTERNAL_VOCABULARY_BLOCKLIST,
    ObservableBeat,
    ObservableObjective,
    ObservableDialogueLine,
    ObservableSceneProjection,
    ObservableSceneProjector,
    scan_for_internal_vocabulary,
)

__all__ = [
    "NarrativeBeat",
    "NarrativeBeatType",
    "NarrativeEventSelection",
    "Observer",
    "EventSalience",
    "SceneBuilder",
    "SufficiencyGateExecutionError",
    "CausalContinuityAnalyzer",
    "ProvenanceService",
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
    "CharacterArcTracker",
    "SubtextAnalyzer",
    "DeceptionClassification",
    "SubtextAnalysis",
    "PerformanceCueGenerator",
    "PerformanceCueType",
    "PerformanceCue",
    "InternalStateVerbGuard",
    "INTERNAL_VOCABULARY_BLOCKLIST",
    "ObservableBeat",
    "ObservableObjective",
    "ObservableDialogueLine",
    "ObservableSceneProjection",
    "ObservableSceneProjector",
    "scan_for_internal_vocabulary",
]
