"""Hand-drawn storyboard sketch engine package."""

from src.storyboard.sketch.stroke import (
    SketchStroke,
    SketchPolyline,
    SketchPolygon,
    SketchEllipse,
    CrossHatch,
    ScribbleShadow,
    PerspectiveGrid,
    MotionArrow,
    SpeedLines,
    get_rng,
    get_seed_hash,
)
from src.storyboard.sketch.pose import (
    PoseType,
    PoseDefinition,
    POSE_DEFINITIONS,
    map_action_to_pose,
)
from src.storyboard.sketch.expression import (
    ExpressionType,
    FacialFeatures,
    EXPRESSION_PROFILES,
    ExpressionRenderer,
    map_emotion_to_expression,
)
from src.storyboard.sketch.character import (
    CharacterSketchIdentity,
    CharacterSketchRenderer,
)
from src.storyboard.sketch.props import (
    PropType,
    ObjectSketchIdentity,
    PropSketchRenderer,
)
from src.storyboard.sketch.environment import (
    EnvironmentType,
    LocationSketchIdentity,
    EnvironmentSketchRenderer,
)
from src.storyboard.sketch.staging import (
    SceneStager,
    StagedScene,
    StagedActor,
    StagedProp,
)
from src.storyboard.sketch.lighting import (
    SketchStyle,
    StylePalette,
    STYLE_PALETTES,
    LightingSketchRenderer,
)
from src.storyboard.sketch.motion import MotionSketchRenderer
from src.storyboard.sketch.renderer import HandDrawnStoryboardProvider

__all__ = [
    "SketchStroke",
    "SketchPolyline",
    "SketchPolygon",
    "SketchEllipse",
    "CrossHatch",
    "ScribbleShadow",
    "PerspectiveGrid",
    "MotionArrow",
    "SpeedLines",
    "get_rng",
    "get_seed_hash",
    "PoseType",
    "PoseDefinition",
    "POSE_DEFINITIONS",
    "map_action_to_pose",
    "ExpressionType",
    "FacialFeatures",
    "EXPRESSION_PROFILES",
    "ExpressionRenderer",
    "map_emotion_to_expression",
    "CharacterSketchIdentity",
    "CharacterSketchRenderer",
    "PropType",
    "ObjectSketchIdentity",
    "PropSketchRenderer",
    "EnvironmentType",
    "LocationSketchIdentity",
    "EnvironmentSketchRenderer",
    "SceneStager",
    "StagedScene",
    "StagedActor",
    "StagedProp",
    "SketchStyle",
    "StylePalette",
    "STYLE_PALETTES",
    "LightingSketchRenderer",
    "MotionSketchRenderer",
    "HandDrawnStoryboardProvider",
]
